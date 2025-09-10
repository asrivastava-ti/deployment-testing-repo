# Lambda Drift Detection Fix

## Problem Identified

The previous SHA256 comparison approach was producing false positives, reporting drift in all Lambda functions even when some didn't have actual drift. This was caused by several issues:

### Root Causes of False Positives

1. **ZIP File Reproducibility Issues**
   - ZIP files include metadata (timestamps, file permissions, compression settings)
   - Even identical code could produce different SHA256 hashes due to build-time variations
   - Container builds might have slight differences in file metadata

2. **Build Process Inconsistencies**
   - Multiple `sam build` calls during drift detection
   - Potential timing differences between builds
   - Container environment variations

3. **AWS Lambda Packaging Differences**
   - AWS Lambda's internal packaging method might differ from local ZIP creation
   - Different compression algorithms or file ordering
   - AWS-specific metadata additions

## Solution Implemented

### New Approach: Direct Source Code Comparison

Instead of comparing ZIP file SHA256 hashes, the new approach:

1. **Downloads Current Code from AWS**
   ```bash
   # Get download URL and extract current code
   DOWNLOAD_URL=$(aws lambda get-function --function-name $FUNCTION_NAME --query 'Code.Location' --output text)
   curl -s "$DOWNLOAD_URL" -o "$TEMP_DIR/current-code.zip"
   unzip -q current-code.zip
   ```

2. **Maps Functions to Source Directories**
   ```bash
   # Intelligent mapping based on logical ID patterns
   if [[ "$LOGICAL_ID" == *"testFunction"* || "$LOGICAL_ID" == *"TestFunction"* ]]; then
     SOURCE_FUNCTION_DIR="src/functions/testFunction"
   elif [[ "$LOGICAL_ID" == *"order"* || "$LOGICAL_ID" == *"Order"* ]]; then
     SOURCE_FUNCTION_DIR="src/functions/order-service"
   # ... additional mappings
   ```

3. **Compares Source Files Directly**
   ```bash
   # Calculate checksums of actual source files
   SOURCE_CHECKSUM=$(sha256sum "$SOURCE_FUNCTION_DIR/$MAIN_FILE" | cut -d' ' -f1)
   AWS_CHECKSUM=$(sha256sum "$TEMP_DIR/$MAIN_FILE" | cut -d' ' -f1)
   
   # Direct comparison
   if [ "$SOURCE_CHECKSUM" != "$AWS_CHECKSUM" ]; then
     echo "❌ Lambda function has code drift!"
     LAMBDA_DRIFT_DETECTED=true
   fi
   ```

### Key Improvements

1. **Eliminates Build Reproducibility Issues**
   - No longer depends on local ZIP file creation
   - Compares actual source code content, not packaging artifacts

2. **More Accurate Drift Detection**
   - Directly compares the main Lambda function files
   - Shows actual code differences when drift is detected

3. **Better Error Handling**
   - Graceful handling of missing files or unmappable functions
   - Clear logging of what's being compared

4. **Detailed Drift Information**
   - Shows exact file differences using `diff` command
   - Provides checksums for debugging

## Benefits

### Reliability
- Eliminates false positives caused by ZIP metadata differences
- More accurate detection of actual code changes

### Debugging
- Shows exact code differences when drift is detected
- Provides clear mapping information for troubleshooting

### Performance
- No need for multiple local builds during drift detection
- Faster comparison using direct file checksums

## Example Output

### No Drift Detected
```
📋 Checking function: my-test-function
  Function logical ID: TestFunction
  Downloading current function code from AWS...
  Comparing with source directory: src/functions/testFunction
  Comparing main file: lambda_function.py
  Source checksum: abc123...
  AWS checksum: abc123...
  ✅ Lambda function my-test-function code matches source
```

### Drift Detected
```
📋 Checking function: my-test-function
  Function logical ID: TestFunction
  Downloading current function code from AWS...
  Comparing with source directory: src/functions/testFunction
  Comparing main file: lambda_function.py
  Source checksum: abc123...
  AWS checksum: def456...
  ❌ Lambda function my-test-function has code drift!
  📋 Main file (lambda_function.py) differs between source and AWS
  🔧 Someone manually modified the function code in AWS console
  📋 Code differences detected:
  --- src/functions/testFunction/lambda_function.py
  +++ /tmp/my-test-function-aws-code/lambda_function.py
  @@ -1,3 +1,3 @@
   def lambda_handler(event, context):
       return {
           'statusCode': 200,
  -        'body': 'Hello from source'
  +        'body': 'Hello from AWS console'
       }
```

## Testing

The fix includes a test script (`test-drift-detection.sh`) that validates:
- Function directory mapping logic
- Main file detection
- Checksum comparison accuracy

## Deployment

The improved drift detection is now active in the GitHub Actions workflow and will:
- Accurately detect when Lambda function code has been manually modified in AWS console
- Eliminate false positives that were blocking legitimate deployments
- Provide clear information about what changes were detected
