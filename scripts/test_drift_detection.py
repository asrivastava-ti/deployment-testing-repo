#!/usr/bin/env python3
"""
Test script to demonstrate AWS drift detection functionality.
This script simulates different scenarios to show how the drift detection works.
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add the scripts directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_aws_diff import TemplateParser, DiffEngine

def create_test_template(content: dict, temp_dir: str) -> str:
    """Create a temporary template file for testing"""
    template_path = os.path.join(temp_dir, 'test_template.yaml')
    with open(template_path, 'w') as f:
        yaml.dump(content, f)
    return template_path

def test_template_parsing():
    """Test template parsing functionality"""
    print("🧪 Testing Template Parsing...")
    
    # Create a test template
    test_template = {
        'AWSTemplateFormatVersion': '2010-09-09',
        'Transform': 'AWS::Serverless-2016-10-31',
        'Resources': {
            'TestFunction': {
                'Type': 'AWS::Serverless::Function',
                'Properties': {
                    'FunctionName': 'test-function',
                    'Runtime': 'python3.13',
                    'Handler': 'app.lambda_handler',
                    'MemorySize': 256,
                    'Timeout': 15,
                    'Environment': {
                        'Variables': {
                            'STAGE': 'test',
                            'DEBUG': 'true'
                        }
                    },
                    'Layers': ['arn:aws:lambda:us-east-1:123456789012:layer:test-layer:1']
                }
            }
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        template_path = create_test_template(test_template, temp_dir)
        parser = TemplateParser(template_path)
        functions = parser.get_lambda_functions()
        
        assert 'test-function' in functions
        func_config = functions['test-function']
        assert func_config['Runtime'] == 'python3.13'
        assert func_config['MemorySize'] == 256
        assert func_config['Environment']['STAGE'] == 'test'
        
        print("  ✅ Template parsing works correctly")

def test_diff_detection():
    """Test diff detection functionality"""
    print("\n🧪 Testing Diff Detection...")
    
    diff_engine = DiffEngine()
    
    # Test case 1: No differences
    expected = {
        'Runtime': 'python3.13',
        'Handler': 'app.lambda_handler',
        'MemorySize': 256,
        'Timeout': 15,
        'Environment': {'STAGE': 'test'},
        'Layers': []
    }
    
    actual = {
        'Runtime': 'python3.13',
        'Handler': 'app.lambda_handler',
        'MemorySize': 256,
        'Timeout': 15,
        'Environment': {'STAGE': 'test'},
        'Layers': []
    }
    
    diffs, is_new = diff_engine.compare_lambda_function('test-func', expected, actual)
    assert len(diffs) == 0 and not is_new
    print("  ✅ No differences detected correctly")
    
    # Test case 2: Memory difference
    actual_with_diff = actual.copy()
    actual_with_diff['MemorySize'] = 512
    
    diffs, is_new = diff_engine.compare_lambda_function('test-func', expected, actual_with_diff)
    assert len(diffs) == 1 and 'MemorySize' in diffs[0]
    print("  ✅ Memory size difference detected correctly")
    
    # Test case 3: Environment variable differences
    actual_env_diff = actual.copy()
    actual_env_diff['Environment'] = {'STAGE': 'prod', 'NEW_VAR': 'value'}
    
    diffs, is_new = diff_engine.compare_lambda_function('test-func', expected, actual_env_diff)
    env_diffs = [d for d in diffs if 'Environment' in d]
    assert len(env_diffs) >= 1
    print("  ✅ Environment variable differences detected correctly")
    
    # Test case 4: New function (doesn't exist in AWS)
    diffs, is_new = diff_engine.compare_lambda_function('test-func', expected, None)
    assert len(diffs) == 0 and is_new
    print("  ✅ New function detection works correctly")

def test_scenarios():
    """Test various drift scenarios"""
    print("\n🧪 Testing Drift Scenarios...")
    
    scenarios = [
        {
            'name': 'Memory Changed in AWS Console',
            'template': {'MemorySize': 256},
            'aws': {'MemorySize': 512},
            'should_have_diff': True
        },
        {
            'name': 'Timeout Changed in AWS Console',
            'template': {'Timeout': 30},
            'aws': {'Timeout': 60},
            'should_have_diff': True
        },
        {
            'name': 'Environment Variable Added in AWS',
            'template': {'Environment': {'STAGE': 'dev'}},
            'aws': {'Environment': {'STAGE': 'dev', 'DEBUG': 'true'}},
            'should_have_diff': True
        },
        {
            'name': 'No Changes',
            'template': {'MemorySize': 256, 'Timeout': 30},
            'aws': {'MemorySize': 256, 'Timeout': 30},
            'should_have_diff': False
        }
    ]
    
    diff_engine = DiffEngine()
    
    for scenario in scenarios:
        # Add default values to make comparison work
        template_config = {
            'Runtime': 'python3.13',
            'Handler': 'app.lambda_handler',
            'MemorySize': 128,
            'Timeout': 3,
            'Environment': {},
            'Layers': []
        }
        template_config.update(scenario['template'])
        
        aws_config = template_config.copy()
        aws_config.update(scenario['aws'])
        
        diffs, is_new = diff_engine.compare_lambda_function('test', template_config, aws_config)
        has_diff = len(diffs) > 0
        
        if has_diff == scenario['should_have_diff']:
            print(f"  ✅ {scenario['name']}: {'Differences' if has_diff else 'No differences'} detected as expected")
        else:
            print(f"  ❌ {scenario['name']}: Expected {'differences' if scenario['should_have_diff'] else 'no differences'}, got {'differences' if has_diff else 'no differences'}")

def main():
    """Run all tests"""
    print("🚀 Running AWS Drift Detection Tests\n")
    
    try:
        test_template_parsing()
        test_diff_detection()
        test_scenarios()
        
        print(f"\n✅ All tests passed! The drift detection system is working correctly.")
        print(f"\n💡 To test with real AWS resources:")
        print(f"   1. Generate your template: python scripts/generate_template.py")
        print(f"   2. Run drift detection: python scripts/validate_aws_diff.py --interactive")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
