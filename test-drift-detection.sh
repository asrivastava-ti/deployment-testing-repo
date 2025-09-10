#!/bin/bash

# Test script to validate drift detection logic
# This simulates the drift detection process locally

echo "🧪 Testing Lambda drift detection logic..."

# Simulate function mapping
test_function_mapping() {
    echo "Testing function directory mapping..."
    
    # Test cases
    test_cases=(
        "TestFunction:testFunction"
        "OrderService:order-service"
        "UserService:user-service"
        "SomeOtherFunction:unknown"
    )
    
    for test_case in "${test_cases[@]}"; do
        LOGICAL_ID="${test_case%%:*}"
        EXPECTED="${test_case##*:}"
        
        echo "  Testing LOGICAL_ID: $LOGICAL_ID"
        
        # Simulate the mapping logic from the workflow
        SOURCE_FUNCTION_DIR=""
        if [ -d "src/functions/testFunction" ] && [[ "$LOGICAL_ID" == *"testFunction"* || "$LOGICAL_ID" == *"TestFunction"* ]]; then
            SOURCE_FUNCTION_DIR="src/functions/testFunction"
        elif [ -d "src/functions/order-service" ] && [[ "$LOGICAL_ID" == *"order"* || "$LOGICAL_ID" == *"Order"* ]]; then
            SOURCE_FUNCTION_DIR="src/functions/order-service"
        elif [ -d "src/functions/user-service" ] && [[ "$LOGICAL_ID" == *"user"* || "$LOGICAL_ID" == *"User"* ]]; then
            SOURCE_FUNCTION_DIR="src/functions/user-service"
        else
            # Try to find by exact logical ID match
            for func_dir in src/functions/*/; do
                if [ -d "$func_dir" ]; then
                    func_name=$(basename "$func_dir")
                    if [[ "$LOGICAL_ID" == *"$func_name"* ]]; then
                        SOURCE_FUNCTION_DIR="$func_dir"
                        break
                    fi
                fi
            done
        fi
        
        if [ -n "$SOURCE_FUNCTION_DIR" ]; then
            MAPPED_DIR=$(basename "$SOURCE_FUNCTION_DIR")
            if [ "$MAPPED_DIR" = "$EXPECTED" ]; then
                echo "    ✅ Correctly mapped to: $SOURCE_FUNCTION_DIR"
            else
                echo "    ❌ Incorrectly mapped to: $SOURCE_FUNCTION_DIR (expected: $EXPECTED)"
            fi
        else
            if [ "$EXPECTED" = "unknown" ]; then
                echo "    ✅ Correctly failed to map (as expected)"
            else
                echo "    ❌ Failed to map (expected: $EXPECTED)"
            fi
        fi
    done
}

# Test file detection
test_file_detection() {
    echo "Testing main file detection..."
    
    for func_dir in src/functions/*/; do
        if [ -d "$func_dir" ]; then
            func_name=$(basename "$func_dir")
            echo "  Testing directory: $func_name"
            
            # Simulate main file detection logic
            MAIN_FILE=""
            if [ -f "$func_dir/lambda_function.py" ]; then
                MAIN_FILE="lambda_function.py"
            elif [ -f "$func_dir/app.py" ]; then
                MAIN_FILE="app.py"
            elif [ -f "$func_dir/index.js" ]; then
                MAIN_FILE="index.js"
            fi
            
            if [ -n "$MAIN_FILE" ]; then
                echo "    ✅ Found main file: $MAIN_FILE"
                
                # Test checksum calculation
                if [ -f "$func_dir/$MAIN_FILE" ]; then
                    CHECKSUM=$(sha256sum "$func_dir/$MAIN_FILE" | cut -d' ' -f1)
                    echo "    📋 Checksum: $CHECKSUM"
                fi
            else
                echo "    ❌ No main file found"
            fi
        fi
    done
}

# Test checksum comparison
test_checksum_comparison() {
    echo "Testing checksum comparison..."
    
    # Create a test file
    TEST_FILE="/tmp/test-lambda.py"
    echo 'def lambda_handler(event, context):
    return {"statusCode": 200, "body": "test"}' > "$TEST_FILE"
    
    # Calculate checksum
    CHECKSUM1=$(sha256sum "$TEST_FILE" | cut -d' ' -f1)
    echo "  Original checksum: $CHECKSUM1"
    
    # Create identical file
    TEST_FILE2="/tmp/test-lambda2.py"
    echo 'def lambda_handler(event, context):
    return {"statusCode": 200, "body": "test"}' > "$TEST_FILE2"
    
    CHECKSUM2=$(sha256sum "$TEST_FILE2" | cut -d' ' -f1)
    echo "  Identical checksum: $CHECKSUM2"
    
    if [ "$CHECKSUM1" = "$CHECKSUM2" ]; then
        echo "  ✅ Identical files have same checksum"
    else
        echo "  ❌ Identical files have different checksums"
    fi
    
    # Create modified file
    echo 'def lambda_handler(event, context):
    return {"statusCode": 200, "body": "modified"}' > "$TEST_FILE2"
    
    CHECKSUM3=$(sha256sum "$TEST_FILE2" | cut -d' ' -f1)
    echo "  Modified checksum: $CHECKSUM3"
    
    if [ "$CHECKSUM1" != "$CHECKSUM3" ]; then
        echo "  ✅ Modified files have different checksums"
    else
        echo "  ❌ Modified files have same checksum"
    fi
    
    # Clean up
    rm -f "$TEST_FILE" "$TEST_FILE2"
}

# Run all tests
echo "🚀 Starting drift detection tests..."
echo ""

test_function_mapping
echo ""

test_file_detection
echo ""

test_checksum_comparison
echo ""

echo "✅ Drift detection tests completed!"
