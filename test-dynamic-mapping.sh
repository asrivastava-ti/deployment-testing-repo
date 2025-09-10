#!/bin/bash

# Test script to validate the improved dynamic mapping logic
# This simulates the mapping process locally

echo "🧪 Testing Dynamic Function Mapping Logic..."
echo ""

# Test function to simulate the mapping logic
test_mapping() {
    local LOGICAL_ID="$1"
    local EXPECTED_DIR="$2"
    
    echo "🔍 Testing mapping for logical ID: '$LOGICAL_ID'"
    echo "   Expected directory: $EXPECTED_DIR"
    
    # Convert logical ID to lowercase for case-insensitive matching
    LOGICAL_ID_LOWER=$(echo "$LOGICAL_ID" | tr '[:upper:]' '[:lower:]')
    
    SOURCE_FUNCTION_DIR=""
    
    # Dynamic mapping strategy with multiple approaches
    for func_dir in src/functions/*/; do
        if [ -d "$func_dir" ]; then
            func_name=$(basename "$func_dir")
            func_name_lower=$(echo "$func_name" | tr '[:upper:]' '[:lower:]')
            
            echo "     Checking directory: $func_name"
            
            # Strategy 1: Exact match (case-insensitive)
            if [ "$LOGICAL_ID_LOWER" = "$func_name_lower" ]; then
                echo "     ✅ Exact match found: $func_name"
                SOURCE_FUNCTION_DIR="$func_dir"
                break
            fi
            
            # Strategy 2: Logical ID contains directory name
            if [[ "$LOGICAL_ID_LOWER" == *"$func_name_lower"* ]]; then
                echo "     ✅ Substring match found: $func_name (in $LOGICAL_ID)"
                SOURCE_FUNCTION_DIR="$func_dir"
                break
            fi
            
            # Strategy 3: Directory name contains logical ID
            if [[ "$func_name_lower" == *"$LOGICAL_ID_LOWER"* ]]; then
                echo "     ✅ Reverse substring match found: $LOGICAL_ID (in $func_name)"
                SOURCE_FUNCTION_DIR="$func_dir"
                break
            fi
            
            # Strategy 4: Handle kebab-case to camelCase conversion
            # Convert kebab-case to camelcase for comparison
            func_name_camel=$(echo "$func_name" | sed 's/-\([a-z]\)/\U\1/g')
            func_name_camel_lower=$(echo "$func_name_camel" | tr '[:upper:]' '[:lower:]')
            
            if [[ "$LOGICAL_ID_LOWER" == *"$func_name_camel_lower"* ]]; then
                echo "     ✅ Kebab-to-camel match found: $func_name -> $func_name_camel"
                SOURCE_FUNCTION_DIR="$func_dir"
                break
            fi
            
            # Strategy 5: Handle camelCase to kebab-case conversion
            # Convert camelCase logical ID to kebab-case for comparison
            logical_id_kebab=$(echo "$LOGICAL_ID" | sed 's/\([A-Z]\)/-\L\1/g' | sed 's/^-//')
            logical_id_kebab_lower=$(echo "$logical_id_kebab" | tr '[:upper:]' '[:lower:]')
            
            if [[ "$logical_id_kebab_lower" == *"$func_name_lower"* ]]; then
                echo "     ✅ Camel-to-kebab match found: $LOGICAL_ID -> $logical_id_kebab"
                SOURCE_FUNCTION_DIR="$func_dir"
                break
            fi
            
            echo "     ❌ No match for: $func_name"
        fi
    done
    
    # Check result
    if [ -n "$SOURCE_FUNCTION_DIR" ]; then
        MAPPED_DIR=$(basename "$SOURCE_FUNCTION_DIR")
        echo "   🎯 Result: Successfully mapped to '$SOURCE_FUNCTION_DIR'"
        
        if [ "$MAPPED_DIR" = "$EXPECTED_DIR" ]; then
            echo "   ✅ SUCCESS: Mapping is correct!"
        else
            echo "   ❌ FAILURE: Expected '$EXPECTED_DIR', got '$MAPPED_DIR'"
        fi
    else
        echo "   ❌ FAILURE: Could not map to any directory"
        if [ "$EXPECTED_DIR" = "none" ]; then
            echo "   ✅ SUCCESS: Correctly failed to map (as expected)"
        fi
    fi
    
    echo ""
}

# Show available directories
echo "📁 Available function directories:"
for func_dir in src/functions/*/; do
    if [ -d "$func_dir" ]; then
        func_name=$(basename "$func_dir")
        echo "   - $func_name"
    fi
done
echo ""

# Test cases based on your current functions
echo "🚀 Running test cases..."
echo ""

# Test case 1: Exact matches
test_mapping "testFunction" "testFunction"
test_mapping "order-service" "order-service"
test_mapping "user-service" "user-service"
test_mapping "final-testing" "final-testing"

# Test case 2: Case variations (what AWS might return)
test_mapping "TestFunction" "testFunction"
test_mapping "Testfunction" "testFunction"
test_mapping "TESTFUNCTION" "testFunction"

# Test case 3: CamelCase to kebab-case
test_mapping "OrderService" "order-service"
test_mapping "UserService" "user-service"
test_mapping "FinalTesting" "final-testing"

# Test case 4: Partial matches
test_mapping "TestFunctionHandler" "testFunction"
test_mapping "OrderServiceLambda" "order-service"
test_mapping "UserServiceFunction" "user-service"

# Test case 5: Should fail
test_mapping "NonExistentFunction" "none"
test_mapping "RandomName" "none"

echo "✅ Dynamic mapping tests completed!"
echo ""
echo "📋 Summary:"
echo "   - Removed hardcoded function mappings"
echo "   - Implemented 5 different mapping strategies"
echo "   - Added detailed logging for debugging"
echo "   - System now automatically handles new functions"
echo ""
echo "🎯 Benefits:"
echo "   - No more workflow updates needed for new functions"
echo "   - Handles various naming conventions automatically"
echo "   - Better error reporting and debugging"
echo "   - More maintainable and scalable"
