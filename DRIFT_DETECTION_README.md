# Enhanced Drift Detection Workflow

This document explains the comprehensive drift detection strategy implemented in the GitHub Actions workflow, including both CloudFormation and Lambda-specific drift detection.

## 🔍 How It Works

The workflow now includes sophisticated drift detection that handles both infrastructure and code changes:

### Workflow Steps:

1. **Initial Drift Check** (Before Build)
   - ✅ **CloudFormation Drift Detection**: Checks for infrastructure changes (IAM roles, etc.)
   - ✅ **Lambda Code Drift Detection**: Checks for manual Lambda code changes
   - ❌ **If any drift found**: Fails workflow with detailed drift report
   - 📦 **If stack doesn't exist**: Skips drift check and marks for creation

2. **Build & Package** (Standard SAM steps)
   - Builds Lambda functions
   - Packages artifacts to S3

3. **Conditional Deployment**:
   
   **For New Stacks:**
   - Creates stack infrastructure only (using changesets)
   - Runs drift check immediately after stack creation
   - Proceeds with code deployment only if no drift detected
   
   **For Existing Stacks:**
   - Runs comprehensive drift check first (already done in step 1)
   - Updates the existing stack with full deployment

4. **Post-Creation Drift Check** (New Stacks Only)
   - Runs after stack infrastructure creation but before code deployment
   - Detects any manual changes made during the infrastructure creation process
   - Fails deployment if drift is detected, preventing code deployment over modified infrastructure

## 🎯 Benefits

### ✅ Comprehensive Coverage
- **CloudFormation Drift**: Detects infrastructure changes (IAM roles, policies, etc.)
- **Lambda Code Drift**: Detects manual Lambda function code changes
- **Timing**: Catches manual changes at any point in the process

### ✅ Smart Handling
- No failures on first deployment
- Graceful handling of non-existent stacks
- Detailed drift reporting with resource-level information
- Separate detection for infrastructure vs. code changes

### ✅ Security
- Prevents deployments over manually modified resources
- Ensures both infrastructure and code consistency
- Provides clear error messages for troubleshooting
- Blocks deployment if someone manually edited Lambda code in AWS console

## 🔧 Lambda Code Drift Detection

### Why It's Needed
CloudFormation drift detection **cannot detect Lambda code changes** because:
- Lambda code is stored as ZIP files in S3
- CloudFormation only tracks the S3 object reference (like `s3://bucket/key.zip`)
- When you manually change code in the AWS console, the S3 reference stays the same
- CloudFormation sees the same S3 path and considers the resource "in sync"

### How It Works
The workflow implements Lambda-specific drift detection by:
1. **Building code locally** to get the expected state
2. **Creating a changeset** to compare local vs. deployed code
3. **Analyzing changes** to detect if Lambda functions would be modified
4. **Failing deployment** if code drift is detected

## 📊 Sample Outputs

### ✅ No Drift Detected
```
✅ Stack exists, checking for drift...
CloudFormation drift detection started with ID: 12345678-1234-1234-1234-123456789012
✅ CloudFormation drift detection completed
CloudFormation drift status: IN_SYNC
✅ No CloudFormation drift detected
🔍 Checking Lambda function code drift...
📋 Checking function: my-function-name
  Current AWS SHA256: abc123def456...
  Building function locally to compare...
  Checking if deployment would make changes...
  ✅ Lambda function my-function-name code matches source
✅ No Lambda code drift detected
✅ All drift checks passed, proceeding with deployment
```

### ❌ CloudFormation Drift Detected
```
❌ CloudFormation stack has drifted! Manual changes detected.
📋 CloudFormation Drift Details:
|  LogicalResourceId  |    ResourceType     | StackResourceDriftStatus |
|---------------------|---------------------|--------------------------|
| MyIAMRole          | AWS::IAM::Role       | MODIFIED                |

Please fix the CloudFormation drift in AWS console before deploying.
```

### ❌ Lambda Code Drift Detected
```
✅ No CloudFormation drift detected
🔍 Checking Lambda function code drift...
📋 Checking function: my-function-name
  Current AWS SHA256: abc123def456...
  Building function locally to compare...
  Checking if deployment would make changes...
  ❌ Lambda function my-function-name has code drift!
  📋 This means the function code in AWS differs from your source code

❌ Lambda code drift detected!
🔧 Someone manually modified Lambda function code in the AWS console
💡 This type of drift cannot be detected by CloudFormation drift detection
🚫 Deployment blocked - please revert manual changes or update your source code
```

### 📦 First Deployment
```
📦 Stack doesn't exist yet - this will be a first deployment
✅ Will create stack infrastructure and then check for drift
🚀 Creating stack infrastructure (changeset creation)...
🚀 Executing changeset to create stack...
✅ Stack infrastructure created successfully
⏳ Waiting for stack to stabilize before drift check...
🔍 Running drift check after stack creation but before code deployment...
✅ No drift detected, proceeding with final code deployment
🚀 Deploying Lambda function code...
✅ Deployment completed successfully
```

## 🔧 Configuration

The workflow uses these environment variables:
- `STACK_NAME`: CloudFormation stack name
- `AWS_REGION`: AWS region for deployment
- `ARTIFACT_BUCKET`: S3 bucket for SAM artifacts

## 🚨 Troubleshooting

### Common Issues:

**1. Lambda Code Drift False Positives**
- Sometimes the changeset comparison may show differences due to packaging variations
- Review the specific function mentioned in the error
- Check if someone actually modified the code in AWS console

**2. CloudFormation Drift Detection Timeout**
- Increase wait time in the workflow
- Check AWS CloudFormation console for stuck operations

**3. False Positive Drift**
- Some AWS services auto-modify resources (normal behavior)
- Review drift details to identify actual vs. expected changes

**4. Permission Issues**
- Ensure GitHub Actions role has CloudFormation drift detection permissions:
  - `cloudformation:DetectStackDrift`
  - `cloudformation:DescribeStackDriftDetectionStatus`
  - `cloudformation:DescribeStackResourceDrifts`
  - `cloudformation:DescribeStackResources`
  - `lambda:GetFunction`

## 🔄 Workflow Triggers

The workflow runs on:
- Push to `main` branch
- Changes to function code (`src/functions/**`)
- Changes to template generation script
- Changes to the workflow file itself

This ensures drift detection runs only when necessary and on the main deployment branch.

## 💡 Key Improvements

This enhanced workflow now provides:
1. **Complete drift coverage** - both infrastructure and code
2. **Lambda-specific detection** - catches manual code changes that CloudFormation misses
3. **Clear error messages** - distinguishes between infrastructure and code drift
4. **Robust validation** - prevents deployment over any type of manual changes
