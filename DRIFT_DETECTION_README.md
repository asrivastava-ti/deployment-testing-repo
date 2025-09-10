# CloudFormation Drift Detection Workflow

This document explains the advanced drift detection strategy implemented in the GitHub Actions workflow.

## 🔍 How It Works

The workflow now includes sophisticated drift detection that handles both new stack creation and existing stack updates:

### Workflow Steps:

1. **Initial Drift Check** (Before Build)
   - ✅ **If stack exists**: Runs drift detection immediately
   - ❌ **If drift found**: Fails workflow with detailed drift report
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
   - Runs drift check first (already done in step 1)
   - Updates the existing stack with full deployment

4. **Post-Creation Drift Check** (New Stacks Only)
   - Runs after stack infrastructure creation but before code deployment
   - Detects any manual changes made during the infrastructure creation process
   - Fails deployment if drift is detected, preventing code deployment over modified infrastructure

## 🎯 Benefits

### ✅ Comprehensive Coverage
- Detects drift before deployment (existing stacks)
- Detects drift after creation (new stacks)
- Catches manual changes at any point in the process

### ✅ Smart Handling
- No failures on first deployment
- Graceful handling of non-existent stacks
- Detailed drift reporting with resource-level information

### ✅ Security
- Prevents deployments over manually modified resources
- Ensures infrastructure consistency
- Provides clear error messages for troubleshooting

## 📊 Sample Outputs

### ✅ No Drift Detected
```
✅ Stack exists, checking for drift...
Drift detection started with ID: 12345678-1234-1234-1234-123456789012
Drift status: IN_SYNC
✅ No drift detected, proceeding with deployment
```

### ❌ Drift Detected
```
❌ Stack has drifted! Manual changes detected.
📋 Drift Details:
|  LogicalResourceId  |    ResourceType     | StackResourceDriftStatus |
|---------------------|---------------------|--------------------------|
| MyLambdaFunction    | AWS::Lambda::Function| MODIFIED                |
| MyIAMRole          | AWS::IAM::Role       | MODIFIED                |

Please fix the drift in AWS console before deploying.
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

**1. Drift Detection Timeout**
- Increase wait time in the workflow
- Check AWS CloudFormation console for stuck operations

**2. False Positive Drift**
- Some AWS services auto-modify resources (normal behavior)
- Review drift details to identify actual vs. expected changes

**3. Permission Issues**
- Ensure GitHub Actions role has CloudFormation drift detection permissions:
  - `cloudformation:DetectStackDrift`
  - `cloudformation:DescribeStackDriftDetectionStatus`
  - `cloudformation:DescribeStackResourceDrifts`

## 🔄 Workflow Triggers

The workflow runs on:
- Push to `main` branch
- Changes to function code (`src/functions/**`)
- Changes to template generation script
- Changes to the workflow file itself

This ensures drift detection runs only when necessary and on the main deployment branch.
