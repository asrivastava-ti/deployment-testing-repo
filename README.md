# AWS Drift Detection for SAM Deployments

This repository includes an AWS drift detection system that validates your AWS resources against your SAM template configuration before deployment. It prevents deployments when manual changes have been made in the AWS console, ensuring infrastructure consistency.

## 🚀 Features

- **Drift Detection**: Compares AWS Lambda functions against your SAM template
- **Fail-Fast Deployment**: Automatically blocks deployment if differences are detected
- **GitHub Actions Integration**: Built-in CI/CD workflow with drift validation
- **Interactive & CI Modes**: Works both locally and in automated pipelines
- **Comprehensive Reporting**: Detailed diff reports showing exactly what changed

## 📋 Prerequisites

- Python 3.11+
- AWS CLI configured with appropriate credentials
- SAM CLI installed
- Required Python packages: `boto3`, `PyYAML`

## 🛠️ Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials:
```bash
aws configure
# OR set environment variables:
# export AWS_ACCESS_KEY_ID=your_key
# export AWS_SECRET_ACCESS_KEY=your_secret
# export AWS_DEFAULT_REGION=us-east-1
```

## 📖 Usage

### Local Development

1. **Generate SAM Template**:
```bash
python scripts/generate_template.py
```

2. **Validate Against AWS (Interactive Mode)**:
```bash
python scripts/validate_aws_diff.py --interactive
```

3. **Validate Against AWS (CI Mode)**:
```bash
python scripts/validate_aws_diff.py --ci-mode
```

4. **Deploy if validation passes**:
```bash
sam build
sam deploy
```

### Command Line Options

```bash
python scripts/validate_aws_diff.py [OPTIONS]

Options:
  --region TEXT        AWS region (default: us-east-1)
  --profile TEXT       AWS profile to use
  --interactive        Interactive mode with prompts
  --ci-mode           CI/CD mode (fail on drift)
  --help              Show help message
```

### GitHub Actions

The repository includes a complete GitHub Actions workflow that:

1. Generates the SAM template
2. Validates against AWS (fails on drift)
3. Builds and deploys if validation passes

**Required GitHub Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

The workflow runs on:
- Push to `main` or `develop` branches
- Pull requests to `main`
- Manual trigger via `workflow_dispatch`

## 🔍 What Gets Validated

The drift detection system checks:

### Lambda Functions
- ✅ Runtime version
- ✅ Handler configuration
- ✅ Memory allocation
- ✅ Timeout settings
- ✅ Environment variables
- ✅ Layer attachments
- ✅ IAM role assignments

### Future Enhancements
- IAM roles and policies
- S3 bucket configurations
- CloudFormation stack parameters

## 📊 Sample Output

### ✅ No Drift Detected
```
🔍 Validating AWS resources against template...
Region: us-east-1

Checking order-service...
  ✅ Configuration matches

Checking testFunction...
  📦 New function (will be created)

Checking user-service...
  ✅ Configuration matches

✅ All resources match template configuration
🚀 Deployment can proceed
```

### ❌ Drift Detected
```
🔍 Validating AWS resources against template...
Region: us-east-1

Checking order-service...
  ❌ Differences detected:
    • MemorySize: Template=512, AWS=256
    • Environment.STAGE: Template=dev, missing in AWS

Checking testFunction...
  ❌ Differences detected:
    • Timeout: Template=10, AWS=30

❌ DEPLOYMENT BLOCKED: AWS Console drift detected!
Fix these differences in AWS Console or update your template, then retry deployment.
```

## 🔧 Configuration

### Function Configuration Files

Each Lambda function has a `config.json` file that defines its configuration:

```json
{
  "handler": "app.lambda_handler",
  "runtime": "python3.13",
  "memory": 512,
  "timeout": 20,
  "layers": [],
  "env": {
    "STAGE": "dev",
    "DB_TABLE": "users"
  },
  "policies": ["AWSLambdaBasicExecutionRole", "AmazonS3FullAccess"],
  "role": ""
}
```

### Template Generation

The `generate_template.py` script automatically creates a SAM template from your function configurations:

```bash
python scripts/generate_template.py
```

This generates `template.yaml` which is used for both drift detection and deployment.

## 🚨 Troubleshooting

### Common Issues

**1. AWS Credentials Not Found**
```
❌ AWS credentials not found. Please configure AWS CLI or set environment variables.
```
**Solution**: Run `aws configure` or set AWS environment variables.

**2. Template Not Found**
```
❌ Template file not found: template.yaml
💡 Run 'python scripts/generate_template.py' first
```
**Solution**: Generate the template first using the generate script.

**3. Function Not Found in AWS**
```
📦 New function (will be created)
```
**Note**: This is normal for new functions. They will be created during deployment.

**4. Permission Denied**
```
⚠️ Warning: Could not fetch Lambda function: AccessDenied
```
**Solution**: Ensure your AWS credentials have Lambda read permissions.

### Required AWS Permissions

Your AWS credentials need the following permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:GetFunction",
        "lambda:ListFunctions",
        "iam:GetRole",
        "iam:ListAttachedRolePolicies",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🔄 Workflow Integration

### Local Development Workflow
```bash
# 1. Make changes to function code/config
# 2. Generate template
python scripts/generate_template.py

# 3. Validate against AWS
python scripts/validate_aws_diff.py --interactive

# 4. Deploy if validation passes
sam build && sam deploy
```

### CI/CD Workflow
The GitHub Actions workflow automatically:
1. Generates template
2. Validates against AWS (fails on drift)
3. Builds and deploys if validation passes

## 📝 Contributing

1. Make changes to function code or configurations
2. Test locally with drift validation
3. Ensure GitHub Actions workflow passes
4. Submit pull request

## 🔒 Security

- AWS credentials are never stored in the repository
- Use GitHub Secrets for CI/CD credentials
- Follow AWS IAM best practices for minimal permissions

## 📄 License

This project is licensed under the MIT License.
