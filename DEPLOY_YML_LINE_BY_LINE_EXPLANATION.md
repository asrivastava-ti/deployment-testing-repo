# Deploy.yml Line-by-Line Detailed Explanation

This document provides a comprehensive, line-by-line explanation of the GitHub Actions workflow file `deploy.yml`.

## File Header & Metadata

### Lines 1-2: Workflow Name
```yaml
name: Deploy SAM Multi-Lambda
```
- **Purpose**: Sets the display name for this GitHub Actions workflow
- **What it does**: This name appears in the GitHub Actions UI and logs
- **Why**: Makes it easy to identify this workflow among multiple workflows

### Lines 3-9: Trigger Configuration
```yaml
on:
  push:
    branches: [ "main" ]
    paths:
      - "src/functions/**"
      - "scripts/generate_template.py"
      - ".github/workflows/deploy.yml"
```
- **Line 3**: `on:` - Defines when this workflow should run
- **Line 4**: `push:` - Triggers on git push events
- **Line 5**: `branches: [ "main" ]` - Only runs when pushing to the main branch
- **Lines 6-9**: `paths:` - Only runs if files in these paths are changed:
  - `src/functions/**` - Any Lambda function code changes
  - `scripts/generate_template.py` - Template generation script changes
  - `.github/workflows/deploy.yml` - This workflow file itself changes
- **Why**: Prevents unnecessary runs when unrelated files change (like README updates)

### Lines 10-12: Permissions
```yaml
permissions:
  id-token: write   # for OIDC
  contents: read
```
- **Line 11**: `id-token: write` - Allows workflow to create OIDC tokens for AWS authentication
- **Line 12**: `contents: read` - Allows workflow to read repository contents
- **Why**: Minimal permissions for security; OIDC eliminates need for stored AWS credentials

### Lines 13-17: Environment Variables
```yaml
env:
  AWS_REGION: us-east-1
  ARTIFACT_BUCKET: ayush-lambda-artifacts
  STACK_NAME: my-multi-lambda-stack-actions
```
- **Line 14**: AWS region where resources will be deployed
- **Line 15**: S3 bucket for storing deployment artifacts (Lambda code packages)
- **Line 16**: CloudFormation stack name for this deployment
- **Why**: Centralized configuration that can be easily changed

## Job Definition

### Lines 18-23: Job Setup
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production   # set required reviewers on this environment for approvals
```
- **Line 19**: `deploy:` - Job name
- **Line 20**: `runs-on: ubuntu-latest` - Uses latest Ubuntu runner
- **Lines 21-22**: `environment: production` - Links to GitHub environment for approval gates
- **Why**: Production environment can require manual approvals before deployment

## Workflow Steps

### Step 1: Checkout (Lines 24-26)
```yaml
- name: Checkout
  uses: actions/checkout@v4
```
- **Purpose**: Downloads repository code to the runner
- **What it does**: Makes your source code available for the workflow
- **Why**: Needed to access Lambda function code and scripts

### Step 2: OIDC Token Debug (Lines 27-31)
```yaml
- name: Print OIDC token claims
  run: |
    echo "${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" | cut -d '.' -f1 | base64 -d -i 2>/dev/null || true
    echo "${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" | cut -d '.' -f2 | base64 -d -i 2>/dev/null || true
```
- **Purpose**: Debug step to inspect OIDC token contents
- **Line 29-30**: Decodes JWT token parts (header and payload)
- **Why**: Helps troubleshoot OIDC authentication issues

### Step 3: AWS Authentication (Lines 32-37)
```yaml
- name: Configure AWS credentials (OIDC)
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::975049970782:role/GithubActionsRole
    aws-region: ${{ env.AWS_REGION }}
```
- **Purpose**: Authenticates with AWS using OIDC (no stored credentials)
- **Line 35**: IAM role that GitHub Actions will assume
- **Line 36**: Uses the AWS region from environment variables
- **Why**: Secure authentication without storing AWS keys in GitHub

### Step 4: Python Setup (Lines 38-42)
```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.13"
```
- **Purpose**: Installs Python 3.13 on the runner
- **Why**: Needed for running Python scripts and SAM CLI

### Step 5: Install Tools (Lines 43-47)
```yaml
- name: Install tooling
  run: |
    pip install --upgrade pip
    pip install aws-sam-cli pyyaml cfn-lint
```
- **Line 45**: Updates pip to latest version
- **Line 46**: Installs required tools:
  - `aws-sam-cli`: For building and deploying serverless applications
  - `pyyaml`: For YAML processing in Python scripts
  - `cfn-lint`: For CloudFormation template validation

### Step 6: Generate Template (Lines 48-50)
```yaml
- name: Generate template.yaml
  run: python scripts/generate_template.py
```
- **Purpose**: Runs your custom script to generate CloudFormation template
- **What it does**: Creates `template.yaml` from your function configurations
- **Why**: Dynamically builds template based on your function structure

### Step 7: Validation (Lines 51-55)
```yaml
- name: Validate (SAM + cfn-lint)
  run: |
    sam validate --template template.yaml
    cfn-lint template.yaml
```
- **Line 53**: SAM validates template syntax and structure
- **Line 54**: cfn-lint performs additional CloudFormation best practice checks
- **Why**: Catches template errors before deployment

## Step 8: Initial Drift Check (Lines 56-218)

This is the most complex step. Let me break it down into sections:

### Lines 56-58: Step Header
```yaml
- name: Initial Drift Check
  id: initial-drift
```
- **Line 57**: `id: initial-drift` - Allows other steps to reference outputs from this step

### Lines 59-61: Stack Existence Check
```yaml
run: |
  if aws cloudformation describe-stacks --stack-name ${{ env.STACK_NAME }} >/dev/null 2>&1; then
    echo "✅ Stack exists, checking for drift..."
```
- **Line 60**: Checks if CloudFormation stack already exists
- **`>/dev/null 2>&1`**: Suppresses output (we only care about exit code)
- **Purpose**: Determines if this is a new deployment or update

### Lines 62-67: Start CloudFormation Drift Detection
```yaml
# Start CloudFormation drift detection
DRIFT_ID=$(aws cloudformation detect-stack-drift \
  --stack-name ${{ env.STACK_NAME }} \
  --query 'StackDriftDetectionId' --output text)

echo "CloudFormation drift detection started with ID: $DRIFT_ID"
```
- **Lines 63-65**: Starts drift detection and captures the detection ID
- **`--query 'StackDriftDetectionId'`**: Extracts just the ID from the response
- **Purpose**: Initiates asynchronous drift detection process

### Lines 68-84: Poll for Drift Detection Completion
```yaml
# Poll for drift detection completion
echo "⏳ Waiting for CloudFormation drift detection to complete..."
while true; do
  STATUS=$(aws cloudformation describe-stack-drift-detection-status \
    --stack-drift-detection-id $DRIFT_ID \
    --query 'DetectionStatus' --output text)
  
  if [ "$STATUS" = "DETECTION_COMPLETE" ]; then
    echo "✅ CloudFormation drift detection completed"
    break
  elif [ "$STATUS" = "DETECTION_FAILED" ]; then
    echo "❌ CloudFormation drift detection failed"
    exit 1
  else
    echo "⏳ CloudFormation drift detection in progress (status: $STATUS)..."
    sleep 5
  fi
done
```
- **Line 70**: Infinite loop to poll status
- **Lines 71-73**: Gets current detection status
- **Lines 75-77**: If complete, break out of loop
- **Lines 78-80**: If failed, exit with error
- **Lines 81-84**: If still running, wait 5 seconds and check again
- **Purpose**: Waits for asynchronous drift detection to finish

### Lines 85-90: Get Drift Results
```yaml
# Get CloudFormation drift status
DRIFT_STATUS=$(aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DRIFT_ID \
  --query 'StackDriftStatus' --output text)

echo "CloudFormation drift status: $DRIFT_STATUS"
```
- **Lines 86-88**: Gets the final drift status (IN_SYNC or DRIFTED)
- **Purpose**: Determines if manual changes were made to infrastructure

### Lines 91-105: Handle Drift Detection Results
```yaml
if [ "$DRIFT_STATUS" = "DRIFTED" ]; then
  echo "❌ CloudFormation stack has drifted! Manual changes detected."
  
  # Get detailed drift information
  echo "📋 CloudFormation Drift Details:"
  aws cloudformation describe-stack-resource-drifts \
    --stack-name ${{ env.STACK_NAME }} \
    --query 'StackResourceDrifts[?StackResourceDriftStatus==`MODIFIED`].[LogicalResourceId,ResourceType,StackResourceDriftStatus]' \
    --output table
  
  echo "Please fix the CloudFormation drift in AWS console before deploying."
  exit 1
else
  echo "✅ No CloudFormation drift detected"
fi
```
- **Line 91**: If drift detected, show error and exit
- **Lines 96-99**: Shows detailed information about what resources drifted
- **Line 101**: Exits workflow with error code
- **Lines 102-104**: If no drift, continue
- **Purpose**: Prevents deployment if infrastructure was manually modified

### Lines 106-109: Lambda Drift Detection Setup
```yaml
# Lambda-specific drift detection (CloudFormation can't detect Lambda code changes)
echo "🔍 Checking Lambda function code drift..."

# Get all Lambda functions from the stack
LAMBDA_FUNCTIONS=$(aws cloudformation describe-stack-resources \
  --stack-name ${{ env.STACK_NAME }} \
  --query 'StackResources[?ResourceType==`AWS::Lambda::Function`].PhysicalResourceId' \
  --output text)
```
- **Line 106**: Comment explaining why this is needed
- **Lines 110-113**: Gets list of all Lambda functions in the stack
- **Purpose**: CloudFormation can't detect Lambda code changes, so we check manually

### Lines 114-120: Lambda Function Loop Setup
```yaml
if [ -n "$LAMBDA_FUNCTIONS" ]; then
  LAMBDA_DRIFT_DETECTED=false
  
  for FUNCTION_NAME in $LAMBDA_FUNCTIONS; do
    echo "📋 Checking function: $FUNCTION_NAME"
    
    # Find the function's logical ID from the template
    LOGICAL_ID=$(aws cloudformation describe-stack-resources \
      --stack-name ${{ env.STACK_NAME }} \
      --query "StackResources[?PhysicalResourceId=='$FUNCTION_NAME'].LogicalResourceId" --output text)
```
- **Line 114**: Only proceed if functions exist
- **Line 115**: Flag to track if any drift is detected
- **Line 117**: Loop through each function
- **Lines 120-122**: Get the logical ID for the function
- **Purpose**: Sets up loop to check each Lambda function individually

### Lines 123-133: Download Current Function Code
```yaml
echo "  Function logical ID: $LOGICAL_ID"

# Download current function code from AWS
echo "  Downloading current function code from AWS..."
TEMP_DIR="/tmp/${FUNCTION_NAME}-aws-code"
mkdir -p "$TEMP_DIR"

# Get the function code URL and download it
DOWNLOAD_URL=$(aws lambda get-function \
  --function-name $FUNCTION_NAME \
  --query 'Code.Location' --output text)

if [ "$DOWNLOAD_URL" != "None" ] && [ -n "$DOWNLOAD_URL" ]; then
```
- **Lines 127-128**: Creates temporary directory for downloaded code
- **Lines 130-132**: Gets download URL for function code
- **Line 134**: Checks if URL is valid
- **Purpose**: Downloads currently deployed code for comparison

### Lines 135-140: Extract Downloaded Code
```yaml
# Download and extract the current code
curl -s "$DOWNLOAD_URL" -o "$TEMP_DIR/current-code.zip"
cd "$TEMP_DIR"
unzip -q current-code.zip
rm current-code.zip
cd - >/dev/null
```
- **Line 136**: Downloads the ZIP file silently
- **Line 138**: Extracts the ZIP file quietly
- **Line 139**: Removes the ZIP file
- **Line 140**: Returns to original directory
- **Purpose**: Extracts deployed code for file comparison

### Lines 141-165: Function Directory Mapping
```yaml
# Find the source function directory
SOURCE_FUNCTION_DIR=""
# Convert logical ID to lowercase for case-insensitive matching
LOGICAL_ID_LOWER=$(echo "$LOGICAL_ID" | tr '[:upper:]' '[:lower:]')

if [ -d "src/functions/testFunction" ] && [[ "$LOGICAL_ID_LOWER" == *"testfunction"* ]]; then
  SOURCE_FUNCTION_DIR="src/functions/testFunction"
elif [ -d "src/functions/order-service" ] && [[ "$LOGICAL_ID_LOWER" == *"order"* ]]; then
  SOURCE_FUNCTION_DIR="src/functions/order-service"
elif [ -d "src/functions/user-service" ] && [[ "$LOGICAL_ID_LOWER" == *"user"* ]]; then
  SOURCE_FUNCTION_DIR="src/functions/user-service"
else
  # Try to find by case-insensitive directory name matching
  for func_dir in src/functions/*/; do
    if [ -d "$func_dir" ]; then
      func_name=$(basename "$func_dir")
      func_name_lower=$(echo "$func_name" | tr '[:upper:]' '[:lower:]')
      if [[ "$LOGICAL_ID_LOWER" == *"$func_name_lower"* ]]; then
        SOURCE_FUNCTION_DIR="$func_dir"
        break
      fi
    fi
  done
fi
```
- **Lines 144-145**: Converts logical ID to lowercase for case-insensitive matching
- **Lines 147-151**: Explicit mappings for known functions
- **Lines 152-162**: Dynamic mapping for any other functions
- **Purpose**: Maps AWS function names to source code directories

### Lines 166-175: Main File Detection
```yaml
if [ -n "$SOURCE_FUNCTION_DIR" ] && [ -d "$SOURCE_FUNCTION_DIR" ]; then
  echo "  Comparing with source directory: $SOURCE_FUNCTION_DIR"
  
  # Compare the main Lambda function file
  MAIN_FILE=""
  if [ -f "$SOURCE_FUNCTION_DIR/lambda_function.py" ]; then
    MAIN_FILE="lambda_function.py"
  elif [ -f "$SOURCE_FUNCTION_DIR/app.py" ]; then
    MAIN_FILE="app.py"
  elif [ -f "$SOURCE_FUNCTION_DIR/index.js" ]; then
    MAIN_FILE="index.js"
  fi
```
- **Line 166**: Checks if mapping was successful
- **Lines 170-175**: Looks for common Lambda entry point files
- **Purpose**: Identifies the main function file to compare

### Lines 176-200: File Comparison
```yaml
if [ -n "$MAIN_FILE" ]; then
  echo "  Comparing main file: $MAIN_FILE"
  
  # Calculate checksums of the main files
  SOURCE_CHECKSUM=$(sha256sum "$SOURCE_FUNCTION_DIR/$MAIN_FILE" | cut -d' ' -f1)
  AWS_CHECKSUM=$(sha256sum "$TEMP_DIR/$MAIN_FILE" 2>/dev/null | cut -d' ' -f1 || echo "missing")
  
  echo "  Source checksum: $SOURCE_CHECKSUM"
  echo "  AWS checksum: $AWS_CHECKSUM"
  
  if [ "$SOURCE_CHECKSUM" != "$AWS_CHECKSUM" ]; then
    echo "  ❌ Lambda function $FUNCTION_NAME has code drift!"
    echo "  📋 Main file ($MAIN_FILE) differs between source and AWS"
    echo "  🔧 Someone manually modified the function code in AWS console"
    
    # Show the differences if possible
    if [ "$AWS_CHECKSUM" != "missing" ]; then
      echo "  📋 Code differences detected:"
      diff -u "$SOURCE_FUNCTION_DIR/$MAIN_FILE" "$TEMP_DIR/$MAIN_FILE" || true
    else
      echo "  📋 Main file missing in AWS deployment"
    fi
    
    LAMBDA_DRIFT_DETECTED=true
  else
    echo "  ✅ Lambda function $FUNCTION_NAME code matches source"
  fi
```
- **Lines 179-180**: Calculates SHA256 checksums of source and deployed files
- **Lines 182-183**: Displays checksums for debugging
- **Line 185**: Compares checksums to detect differences
- **Lines 186-188**: If different, reports drift detected
- **Lines 190-196**: Shows actual code differences using `diff` command
- **Line 198**: Sets flag indicating drift was found
- **Lines 199-201**: If same, reports no drift
- **Purpose**: Compares actual file content to detect manual code changes

### Lines 201-207: Error Handling for Missing Files
```yaml
else
  echo "  ⚠️  Could not find main Lambda file in source directory"
  echo "  ℹ️  Skipping drift check for this function"
fi
else
  echo "  ⚠️  Could not map function to source directory"
  echo "  ℹ️  Available directories: $(ls -d src/functions/*/ 2>/dev/null | tr '\n' ' ')"
  echo "  ℹ️  Skipping drift check for this function"
fi
```
- **Lines 202-204**: Handles case where main file isn't found
- **Lines 205-209**: Handles case where function can't be mapped to directory
- **Line 207**: Shows available directories for debugging
- **Purpose**: Graceful error handling with helpful debugging information

### Lines 210-215: Cleanup and Error Handling
```yaml
# Clean up temporary directory
rm -rf "$TEMP_DIR"
else
  echo "  ⚠️  Could not get download URL for function code"
  echo "  ℹ️  Skipping drift check for this function"
fi
```
- **Line 211**: Removes temporary directory to clean up
- **Lines 212-215**: Handles case where function code can't be downloaded
- **Purpose**: Cleanup and error handling

### Lines 216-225: Final Drift Check Results
```yaml
done

if [ "$LAMBDA_DRIFT_DETECTED" = true ]; then
  echo ""
  echo "❌ Lambda code drift detected!"
  echo "🔧 Someone manually modified Lambda function code in the AWS console"
  echo "💡 This type of drift cannot be detected by CloudFormation drift detection"
  echo "🚫 Deployment blocked - please revert manual changes or update your source code"
  exit 1
else
  echo "✅ No Lambda code drift detected"
fi
```
- **Line 216**: End of function loop
- **Line 218**: Check if any drift was detected across all functions
- **Lines 219-223**: If drift found, explain the issue and exit with error
- **Lines 224-226**: If no drift, continue with deployment
- **Purpose**: Final decision on whether to proceed with deployment

### Lines 227-235: Stack Existence Output and New Stack Handling
```yaml
else
  echo "ℹ️  No Lambda functions found in stack"
fi

echo "✅ All drift checks passed, proceeding with deployment"
echo "stack_exists=true" >> $GITHUB_OUTPUT
else
  echo "📦 Stack doesn't exist yet - this will be a first deployment"
  echo "✅ Will create stack and then check for drift"
  echo "stack_exists=false" >> $GITHUB_OUTPUT
fi
```
- **Lines 227-228**: Handles case where no Lambda functions exist
- **Line 230**: Confirms all checks passed
- **Line 231**: Sets output variable for existing stack
- **Lines 232-235**: Handles new stack deployment case
- **Purpose**: Sets up conditional logic for subsequent steps

## Step 9: Build (Lines 236-238)
```yaml
- name: Build (use Lambda-like container for deps)
  run: sam build --use-container
```
- **Purpose**: Builds Lambda functions using containers that match AWS Lambda environment
- **`--use-container`**: Ensures dependencies are compiled for Lambda's Linux environment
- **Why**: Prevents issues with platform-specific dependencies

## Step 10: Package (Lines 239-244)
```yaml
- name: Package
  run: |
    sam package \
         --template-file .aws-sam/build/template.yaml \
         --s3-bucket ${{ env.ARTIFACT_BUCKET }} \
         --output-template-file packaged.yaml
```
- **Purpose**: Uploads Lambda code to S3 and creates deployment-ready template
- **Line 242**: Uses built template from previous step
- **Line 243**: Uploads to specified S3 bucket
- **Line 244**: Creates new template with S3 references
- **Why**: Lambda code must be in S3 for CloudFormation deployment

## Step 11: Create Stack Infrastructure (Lines 245-265)
```yaml
- name: Create Stack Infrastructure (First Deployment)
  if: steps.initial-drift.outputs.stack_exists == 'false'
  run: |
    echo "🚀 Creating new stack infrastructure..."
    
    # Create changeset without executing it
    sam deploy \
         --template-file packaged.yaml \
         --stack-name ${{ env.STACK_NAME }} \
         --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
         --no-execute-changeset
    
    # Execute the changeset to create stack
    CHANGESET_NAME=$(aws cloudformation list-change-sets \
      --stack-name ${{ env.STACK_NAME }} \
      --query 'Summaries[0].ChangeSetName' --output text)
    
    echo "Executing changeset: $CHANGESET_NAME"
    aws cloudformation execute-change-set \
      --change-set-name $CHANGESET_NAME \
      --stack-name ${{ env.STACK_NAME }}
    
    # Wait for stack creation to complete
    echo "⏳ Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete \
      --stack-name ${{ env.STACK_NAME }}
    
    echo "✅ Stack infrastructure created successfully"
```
- **Line 246**: Only runs for new stacks (conditional execution)
- **Lines 250-253**: Creates changeset without executing it
- **Line 252**: Grants necessary IAM permissions
- **Lines 255-257**: Gets the changeset name
- **Lines 259-261**: Executes the changeset to create stack
- **Lines 263-265**: Waits for creation to complete
- **Purpose**: Creates infrastructure first, then checks for drift before deploying code

## Step 12: Post-Creation Drift Check (Lines 266-300)
```yaml
- name: Post-Creation Drift Check (New Stacks Only)
  if: steps.initial-drift.outputs.stack_exists == 'false'
  run: |
    echo "🔍 Running drift check after stack creation (before deployment)..."
    
    # Wait a moment for stack to stabilize
    sleep 10
    
    # Start drift detection
    DRIFT_ID=$(aws cloudformation detect-stack-drift \
      --stack-name ${{ env.STACK_NAME }} \
      --query 'StackDriftDetectionId' --output text)
    
    echo "Drift detection started with ID: $DRIFT_ID"
    
    # Poll for drift detection completion
    echo "⏳ Waiting for drift detection to complete..."
    while true; do
      STATUS=$(aws cloudformation describe-stack-drift-detection-status \
        --stack-drift-detection-id $DRIFT_ID \
        --query 'DetectionStatus' --output text)
      
      if [ "$STATUS" = "DETECTION_COMPLETE" ]; then
        echo "✅ Drift detection completed"
        break
      elif [ "$STATUS" = "DETECTION_FAILED" ]; then
        echo "❌ Drift detection failed"
        exit 1
      else
        echo "⏳ Drift detection in progress (status: $STATUS)..."
        sleep 5
      fi
    done
    
    # Get drift status
    DRIFT_STATUS=$(aws cloudformation describe-stack-drift-detection-status \
      --stack-drift-detection-id $DRIFT_ID \
      --query 'StackDriftStatus' --output text)
    
    echo "Post-creation drift status: $DRIFT_STATUS"
    
    if [ "$DRIFT_STATUS" = "DRIFTED" ]; then
      echo "❌ Stack has drifted after creation! Manual changes detected."
      
      # Get detailed drift information
      echo "📋 Drift Details:"
      aws cloudformation describe-stack-resource-drifts \
        --stack-name ${{ env.STACK_NAME }} \
        --query 'StackResourceDrifts[?StackResourceDriftStatus==`MODIFIED`].[LogicalResourceId,ResourceType,StackResourceDriftStatus]' \
        --output table
      
      echo "⚠️  Someone made manual changes to the stack after creation!"
      echo "❌ Deployment blocked - fix drift before proceeding"
      exit 1
    else
      echo "✅ No drift detected after stack creation"
      echo "✅ Proceeding with code deployment..."
    fi
```
- **Line 267**: Only runs for new stacks
- **Line 271**: Waits for stack to stabilize before checking
- **Lines 273-275**: Starts drift detection
- **Lines 280-296**: Polls for completion (same logic as initial check)
- **Lines 298-312**: Handles drift results
- **Purpose**: Ensures no manual changes were made during stack creation

## Step 13: Deploy Code (Lines 301-315)
```yaml
- name: Deploy Code (Final Step)
  run: |
    if [ "${{ steps.initial-drift.outputs.stack_exists }}" == "true" ]; then
      echo "🔄 Updating existing stack with new code..."
    else
      echo "📦 Deploying code to newly created stack..."
    fi
    
    sam deploy \
         --template-file packaged.yaml \
         --stack-name ${{ env.STACK_NAME }} \
         --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
         --no-fail-on-empty-changeset
    
    echo "✅ Deployment completed successfully"
```
- **Lines 303-307**: Shows different messages for updates vs new deployments
- **Lines 309-312**: Deploys the packaged template
- **Line 312**: `--no-fail-on-empty-changeset` prevents errors when no changes exist
- **Purpose**: Final deployment step that updates Lambda code

## Summary

This workflow implements a comprehensive deployment pipeline with:

1. **Security**: OIDC authentication, minimal permissions
2. **Quality Gates**: Template validation, drift detection
3. **Safety**: Prevents deployment if manual changes detected
4. **Flexibility**: Handles both new and existing stacks
5. **Observability**: Detailed logging and error messages
6. **Reliability**: Proper error handling and cleanup

The key innovation is the Lambda-specific drift detection that downloads and compares actual deployed code with source code, something CloudFormation cannot do natively.
