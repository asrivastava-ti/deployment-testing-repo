# GitHub Actions Deploy.yml File - Line by Line Explanation

This document provides a comprehensive explanation of the `deploy.yml` GitHub Actions workflow file.

## File Header and Metadata

```yaml
name: Deploy SAM Multi-Lambda
```
**Line 1**: Sets the workflow name that appears in the GitHub Actions UI.

## Workflow Triggers

```yaml
on:
  push:
    branches: [ "main" ]
    paths:
      - "src/functions/**"
      - "scripts/generate_template.py"
      - ".github/workflows/deploy.yml"
```
**Lines 3-8**: Defines when this workflow runs:
- `on: push`: Triggers on git push events
- `branches: [ "main" ]`: Only runs when pushing to the main branch
- `paths:`: Only runs if changes are made to specific files/directories:
  - `src/functions/**`: Any Lambda function code changes
  - `scripts/generate_template.py`: Template generation script changes
  - `.github/workflows/deploy.yml`: Workflow file itself changes

## Permissions

```yaml
permissions:
  id-token: write   # for OIDC
  contents: read
```
**Lines 10-12**: Sets GitHub token permissions:
- `id-token: write`: Allows generating OIDC tokens for AWS authentication
- `contents: read`: Allows reading repository contents

## Environment Variables

```yaml
env:
  AWS_REGION: us-east-1
  ARTIFACT_BUCKET: ayush-lambda-artifacts
  STACK_NAME: my-multi-lambda-stack-actions
```
**Lines 14-17**: Global environment variables used throughout the workflow:
- `AWS_REGION`: AWS region for deployment
- `ARTIFACT_BUCKET`: S3 bucket for storing deployment artifacts
- `STACK_NAME`: CloudFormation stack name

## Job Definition

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production   # set required reviewers on this environment for approvals
```
**Lines 19-23**: Defines the deployment job:
- `deploy`: Job name
- `runs-on: ubuntu-latest`: Uses Ubuntu runner
- `environment: production`: Uses production environment (can require manual approval)

## Workflow Steps

### Step 1: Checkout Code

```yaml
- name: Checkout
  uses: actions/checkout@v4
```
**Lines 26-27**: Downloads the repository code to the runner.

### Step 2: Print OIDC Token Claims (Debug)

```yaml
- name: Print OIDC token claims
  run: |
    echo "${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" | cut -d '.' -f1 | base64 -d -i 2>/dev/null || true
    echo "${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" | cut -d '.' -f2 | base64 -d -i 2>/dev/null || true 
```
**Lines 29-32**: Debug step that decodes and prints OIDC token claims for troubleshooting authentication issues.

### Step 3: Configure AWS Credentials

```yaml
- name: Configure AWS credentials (OIDC)
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::975049970782:role/GithubActionsRole
    aws-region: ${{ env.AWS_REGION }}
```
**Lines 34-38**: Sets up AWS authentication using OIDC (OpenID Connect):
- Uses a pre-configured IAM role instead of access keys
- More secure than storing AWS credentials as secrets
- `${{ env.AWS_REGION }}`: References the environment variable defined earlier

### Step 4: Setup Python

```yaml
- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.13"
```
**Lines 40-43**: Installs Python 3.13 on the runner.

### Step 5: Install Tools

```yaml
- name: Install tooling
  run: |
    pip install --upgrade pip
    pip install aws-sam-cli pyyaml cfn-lint
```
**Lines 45-48**: Installs required tools:
- `aws-sam-cli`: AWS SAM CLI for building and deploying
- `pyyaml`: YAML parsing library
- `cfn-lint`: CloudFormation template linter

### Step 6: Generate Template

```yaml
- name: Generate template.yaml
  run: python scripts/generate_template.py
```
**Lines 50-51**: Runs a Python script to dynamically generate the SAM template.

### Step 7: Validate Templates

```yaml
- name: Validate (SAM + cfn-lint)
  run: |
    sam validate --template template.yaml
    cfn-lint template.yaml
```
**Lines 53-56**: Validates the generated template using:
- `sam validate`: SAM-specific validation
- `cfn-lint`: CloudFormation linting for best practices

## Step 8: Initial Drift Check (Complex Logic)

```yaml
- name: Initial Drift Check
  id: initial-drift
```
**Lines 58-59**: Starts the most complex step with an ID for referencing outputs later.

### Check if Stack Exists

```yaml
if aws cloudformation describe-stacks --stack-name ${{ env.STACK_NAME }} >/dev/null 2>&1; then
```
**Line 61**: Checks if the CloudFormation stack already exists by trying to describe it.

### CloudFormation Drift Detection

```yaml
echo "✅ Stack exists, checking for drift..."

# Start CloudFormation drift detection
DRIFT_ID=$(aws cloudformation detect-stack-drift \
  --stack-name ${{ env.STACK_NAME }} \
  --query 'StackDriftDetectionId' --output text)

echo "CloudFormation drift detection started with ID: $DRIFT_ID"
```
**Lines 62-68**: If stack exists, starts CloudFormation drift detection:
- Initiates drift detection and captures the detection ID
- Drift detection runs asynchronously

### Polling for Drift Detection Completion

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
**Lines 70-85**: Polls the drift detection status every 5 seconds until complete:
- Checks status using the detection ID
- Exits with error if detection fails
- Continues polling if still in progress

### Analyze Drift Results

```yaml
# Get CloudFormation drift status
DRIFT_STATUS=$(aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id $DRIFT_ID \
  --query 'StackDriftStatus' --output text)

echo "CloudFormation drift status: $DRIFT_STATUS"

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
**Lines 87-104**: Analyzes drift detection results:
- Gets the final drift status
- If drifted, shows detailed information about what changed
- Exits with error to block deployment if drift detected
- Continues if no drift found

### Lambda-Specific Drift Detection

```yaml
# Lambda-specific drift detection (CloudFormation can't detect Lambda code changes)
echo "🔍 Checking Lambda function code drift..."

# Get all Lambda functions from the stack
LAMBDA_FUNCTIONS=$(aws cloudformation describe-stack-resources \
  --stack-name ${{ env.STACK_NAME }} \
  --query 'StackResources[?ResourceType==`AWS::Lambda::Function`].PhysicalResourceId' \
  --output text)
```
**Lines 106-112**: Starts Lambda-specific drift detection:
- CloudFormation can't detect Lambda code changes (only S3 references)
- Gets list of all Lambda functions in the stack

### Lambda Function Analysis Loop

```yaml
if [ -n "$LAMBDA_FUNCTIONS" ]; then
  LAMBDA_DRIFT_DETECTED=false
  
  for FUNCTION_NAME in $LAMBDA_FUNCTIONS; do
    echo "📋 Checking function: $FUNCTION_NAME"
    
    # Get current function code SHA256 from AWS
    CURRENT_SHA=$(aws lambda get-function \
      --function-name $FUNCTION_NAME \
      --query 'Configuration.CodeSha256' --output text)
    
    echo "  Current AWS SHA256: $CURRENT_SHA"
```
**Lines 114-125**: For each Lambda function:
- Initializes drift detection flag
- Loops through each function
- Gets the current SHA256 hash of the deployed code

### Build and Compare Code

```yaml
    # Build the function locally to get expected SHA256
    # Note: We'll build after this check, so we need to build temporarily here
    echo "  Building function locally to compare..."
    sam build --use-container --quiet
    
    # Get the built function's SHA256 (this is tricky - we need to zip and hash)
    # For now, we'll use a simpler approach: check if deployment would create changes
    echo "  Checking if deployment would make changes..."
    
    # Create a changeset to see what would change
    CHANGESET_NAME="drift-check-$(date +%s)"
    sam deploy \
      --template-file .aws-sam/build/template.yaml \
      --stack-name ${{ env.STACK_NAME }} \
      --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
      --no-execute-changeset \
      --changeset-name $CHANGESET_NAME \
      --s3-bucket ${{ env.ARTIFACT_BUCKET }} >/dev/null 2>&1
```
**Lines 127-141**: Compares local vs deployed code:
- Builds the function locally
- Creates a changeset (without executing) to see what would change
- Uses unique changeset name with timestamp

### Analyze Changeset for Lambda Changes

```yaml
    # Check if changeset has any Lambda function changes
    LAMBDA_CHANGES=$(aws cloudformation describe-change-set \
      --stack-name ${{ env.STACK_NAME }} \
      --change-set-name $CHANGESET_NAME \
      --query 'Changes[?ResourceChange.ResourceType==`AWS::Lambda::Function`]' \
      --output text 2>/dev/null || echo "")
    
    # Clean up the changeset
    aws cloudformation delete-change-set \
      --stack-name ${{ env.STACK_NAME }} \
      --change-set-name $CHANGESET_NAME >/dev/null 2>&1 || true
```
**Lines 143-152**: Analyzes the changeset:
- Looks specifically for Lambda function changes
- Cleans up the temporary changeset

### Detect Lambda Drift

```yaml
    if [ -n "$LAMBDA_CHANGES" ] && [ "$LAMBDA_CHANGES" != "None" ]; then
      echo "  ❌ Lambda function $FUNCTION_NAME has code drift!"
      echo "  📋 This means the function code in AWS differs from your source code"
      LAMBDA_DRIFT_DETECTED=true
    else
      echo "  ✅ Lambda function $FUNCTION_NAME code matches source"
    fi
  done
```
**Lines 154-161**: Determines if Lambda code has drifted:
- If changeset shows Lambda changes, code has drifted
- Sets flag to track drift detection

### Handle Lambda Drift Results

```yaml
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
else
  echo "ℹ️  No Lambda functions found in stack"
fi
```
**Lines 163-175**: Handles Lambda drift results:
- If drift detected, provides detailed explanation and blocks deployment
- If no drift, continues with deployment
- Handles case where no Lambda functions exist

### Set Output Variables

```yaml
echo "✅ All drift checks passed, proceeding with deployment"
echo "stack_exists=true" >> $GITHUB_OUTPUT
else
echo "📦 Stack doesn't exist yet - this will be a first deployment"
echo "✅ Will create stack and then check for drift"
echo "stack_exists=false" >> $GITHUB_OUTPUT
fi
```
**Lines 177-183**: Sets output variables for later steps:
- `stack_exists=true`: If stack exists and passed drift checks
- `stack_exists=false`: If stack doesn't exist (first deployment)

## Step 9: Build

```yaml
- name: Build (use Lambda-like container for deps)
  run: sam build --use-container
```
**Lines 185-186**: Builds Lambda functions using containers for consistent dependencies.

## Step 10: Package

```yaml
- name: Package
  run: |
    sam package \
         --template-file .aws-sam/build/template.yaml \
         --s3-bucket ${{ env.ARTIFACT_BUCKET }} \
         --output-template-file packaged.yaml
```
**Lines 188-193**: Packages the application:
- Uploads artifacts to S3
- Creates a packaged template with S3 references

## Step 11: Create Stack Infrastructure (Conditional)

```yaml
- name: Create Stack Infrastructure (First Deployment)
  if: steps.initial-drift.outputs.stack_exists == 'false'
```
**Lines 195-196**: Only runs for new stacks (first deployment).

### Create Changeset

```yaml
echo "🚀 Creating new stack infrastructure..."

# Create changeset without executing it
sam deploy \
     --template-file packaged.yaml \
     --stack-name ${{ env.STACK_NAME }} \
     --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
     --no-execute-changeset
```
**Lines 198-204**: Creates infrastructure changeset without executing:
- `--no-execute-changeset`: Creates but doesn't execute the changeset
- `CAPABILITY_IAM CAPABILITY_AUTO_EXPAND`: Allows IAM resource creation

### Execute Changeset

```yaml
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
**Lines 206-218**: Executes the changeset:
- Gets the changeset name
- Executes it to create the stack
- Waits for stack creation to complete

## Step 12: Post-Creation Drift Check (Conditional)

```yaml
- name: Post-Creation Drift Check (New Stacks Only)
  if: steps.initial-drift.outputs.stack_exists == 'false'
```
**Lines 220-221**: Only runs for new stacks after infrastructure creation.

### Wait and Start Drift Detection

```yaml
echo "🔍 Running drift check after stack creation (before deployment)..."

# Wait a moment for stack to stabilize
sleep 10

# Start drift detection
DRIFT_ID=$(aws cloudformation detect-stack-drift \
  --stack-name ${{ env.STACK_NAME }} \
  --query 'StackDriftDetectionId' --output text)

echo "Drift detection started with ID: $DRIFT_ID"
```
**Lines 223-233**: Checks for drift after stack creation:
- Waits 10 seconds for stack stabilization
- Starts drift detection to catch any manual changes made during creation

### Poll for Completion

```yaml
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
```
**Lines 235-250**: Same polling logic as initial drift check.

### Handle Post-Creation Drift

```yaml
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
**Lines 252-270**: Handles drift results after stack creation:
- Blocks deployment if someone manually modified the newly created stack
- Allows code deployment to proceed if no drift detected

## Step 13: Deploy Code (Final Step)

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
**Lines 272-286**: Final deployment step:
- Checks if this is an update to existing stack or deployment to new stack
- Performs the actual SAM deployment
- `--no-fail-on-empty-changeset`: Doesn't fail if no changes are needed

## Key Features Summary

### 🔒 Security Features
1. **OIDC Authentication**: Uses IAM roles instead of stored credentials
2. **Environment Protection**: Production environment can require manual approval
3. **Comprehensive Drift Detection**: Catches both infrastructure and code changes

### 🚀 Deployment Strategy
1. **Conditional Logic**: Different paths for new vs existing stacks
2. **Two-Phase Deployment**: Infrastructure first, then code (for new stacks)
3. **Changeset Strategy**: Preview changes before execution

### 🔍 Drift Detection
1. **CloudFormation Drift**: Detects infrastructure changes (IAM, policies, etc.)
2. **Lambda Code Drift**: Detects manual code changes (CloudFormation limitation)
3. **Multiple Check Points**: Before deployment and after stack creation

### 🛠️ Build Process
1. **Container Builds**: Consistent dependency resolution
2. **Template Generation**: Dynamic template creation
3. **Validation**: Multiple validation layers (SAM + cfn-lint)

### 📊 Monitoring & Feedback
1. **Detailed Logging**: Clear status messages throughout
2. **Error Handling**: Specific error messages for different failure types
3. **Progress Tracking**: Visual indicators for long-running operations

This workflow provides enterprise-grade deployment capabilities with comprehensive drift detection, making it suitable for production environments where infrastructure consistency is critical.
