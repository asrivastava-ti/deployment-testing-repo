#!/usr/bin/env python3
"""
AWS Drift Detection Script
Validates that AWS resources match the SAM template configuration.
Fails deployment if any drift is detected.
"""

import os
import sys
import json
import yaml
import boto3
import argparse
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class AWSResourceFetcher:
    """Fetches current AWS resource configurations"""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None):
        self.region = region
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        
        try:
            self.lambda_client = self.session.client('lambda', region_name=region)
            self.iam_client = self.session.client('iam', region_name=region)
            self.sts_client = self.session.client('sts', region_name=region)
            
            # Test credentials
            self.sts_client.get_caller_identity()
            
        except NoCredentialsError:
            print(f"{Colors.RED}❌ AWS credentials not found. Please configure AWS CLI or set environment variables.{Colors.END}")
            sys.exit(1)
        except Exception as e:
            print(f"{Colors.RED}❌ Failed to initialize AWS clients: {e}{Colors.END}")
            sys.exit(1)
    
    def get_lambda_function(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get Lambda function configuration"""
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            config = response['Configuration']
            
            # Get function code info
            code_info = {
                'CodeSha256': config.get('CodeSha256'),
                'CodeSize': config.get('CodeSize'),
                'LastModified': config.get('LastModified')
            }
            
            return {
                'FunctionName': config.get('FunctionName'),
                'Runtime': config.get('Runtime'),
                'Handler': config.get('Handler'),
                'MemorySize': config.get('MemorySize'),
                'Timeout': config.get('Timeout'),
                'Environment': config.get('Environment', {}).get('Variables', {}),
                'Layers': [layer['Arn'] for layer in config.get('Layers', [])],
                'Role': config.get('Role'),
                'CodeInfo': code_info
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            else:
                print(f"{Colors.YELLOW}⚠️  Warning: Could not fetch Lambda function {function_name}: {e}{Colors.END}")
                return None
    
    def get_iam_role(self, role_arn: str) -> Optional[Dict[str, Any]]:
        """Get IAM role configuration"""
        try:
            role_name = role_arn.split('/')[-1]
            response = self.iam_client.get_role(RoleName=role_name)
            role = response['Role']
            
            # Get attached policies
            policies_response = self.iam_client.list_attached_role_policies(RoleName=role_name)
            attached_policies = [policy['PolicyArn'] for policy in policies_response['AttachedPolicies']]
            
            return {
                'RoleName': role['RoleName'],
                'Arn': role['Arn'],
                'AssumeRolePolicyDocument': role['AssumeRolePolicyDocument'],
                'AttachedPolicies': attached_policies
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                return None
            else:
                print(f"{Colors.YELLOW}⚠️  Warning: Could not fetch IAM role {role_arn}: {e}{Colors.END}")
                return None

class TemplateParser:
    """Parses SAM template to extract expected resource configurations"""
    
    def __init__(self, template_path: str = 'template.yaml'):
        self.template_path = template_path
        self.template = self._load_template()
    
    def _load_template(self) -> Dict[str, Any]:
        """Load and parse SAM template"""
        if not os.path.exists(self.template_path):
            print(f"{Colors.RED}❌ Template file not found: {self.template_path}{Colors.END}")
            print(f"{Colors.CYAN}💡 Run 'python scripts/generate_template.py' first{Colors.END}")
            sys.exit(1)
        
        try:
            with open(self.template_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"{Colors.RED}❌ Failed to parse template: {e}{Colors.END}")
            sys.exit(1)
    
    def get_lambda_functions(self) -> Dict[str, Dict[str, Any]]:
        """Extract Lambda function configurations from template"""
        functions = {}
        resources = self.template.get('Resources', {})
        
        for logical_id, resource in resources.items():
            if resource.get('Type') == 'AWS::Serverless::Function':
                props = resource.get('Properties', {})
                
                functions[props.get('FunctionName', logical_id)] = {
                    'Runtime': props.get('Runtime'),
                    'Handler': props.get('Handler'),
                    'MemorySize': props.get('MemorySize', 128),
                    'Timeout': props.get('Timeout', 3),
                    'Environment': props.get('Environment', {}).get('Variables', {}),
                    'Layers': props.get('Layers', []),
                    'Role': props.get('Role'),
                    'Policies': props.get('Policies', [])
                }
        
        return functions

class DiffEngine:
    """Compares template expectations with AWS reality"""
    
    def __init__(self):
        self.differences = []
    
    def compare_lambda_function(self, name: str, expected: Dict[str, Any], actual: Optional[Dict[str, Any]]) -> Tuple[List[str], bool]:
        """Compare Lambda function configurations"""
        diffs = []
        is_new_function = False
        
        if actual is None:
            is_new_function = True
            return diffs, is_new_function
        
        # Compare basic configuration
        comparisons = [
            ('Runtime', 'Runtime'),
            ('Handler', 'Handler'),
            ('MemorySize', 'MemorySize'),
            ('Timeout', 'Timeout')
        ]
        
        for template_key, aws_key in comparisons:
            expected_val = expected.get(template_key)
            actual_val = actual.get(aws_key)
            
            if expected_val != actual_val:
                diffs.append(f"{template_key}: Template={expected_val}, AWS={actual_val}")
        
        # Compare environment variables
        expected_env = expected.get('Environment', {})
        actual_env = actual.get('Environment', {})
        
        env_diffs = self._compare_dicts(expected_env, actual_env, 'Environment')
        diffs.extend(env_diffs)
        
        # Compare layers
        expected_layers = set(expected.get('Layers', []))
        actual_layers = set(actual.get('Layers', []))
        
        if expected_layers != actual_layers:
            missing_layers = expected_layers - actual_layers
            extra_layers = actual_layers - expected_layers
            
            if missing_layers:
                diffs.append(f"Missing layers: {list(missing_layers)}")
            if extra_layers:
                diffs.append(f"Extra layers: {list(extra_layers)}")
        
        return diffs, is_new_function
    
    def _compare_dicts(self, expected: Dict, actual: Dict, context: str) -> List[str]:
        """Compare two dictionaries and return differences"""
        diffs = []
        
        all_keys = set(expected.keys()) | set(actual.keys())
        
        for key in all_keys:
            expected_val = expected.get(key)
            actual_val = actual.get(key)
            
            if expected_val != actual_val:
                if expected_val is None:
                    diffs.append(f"{context}.{key}: Not in template, AWS={actual_val}")
                elif actual_val is None:
                    diffs.append(f"{context}.{key}: Template={expected_val}, missing in AWS")
                else:
                    diffs.append(f"{context}.{key}: Template={expected_val}, AWS={actual_val}")
        
        return diffs

class DriftValidator:
    """Main drift validation orchestrator"""
    
    def __init__(self, region: str = 'us-east-1', profile: Optional[str] = None, interactive: bool = False):
        self.region = region
        self.interactive = interactive
        self.fetcher = AWSResourceFetcher(region, profile)
        self.parser = TemplateParser()
        self.diff_engine = DiffEngine()
        self.has_differences = False
    
    def validate(self) -> bool:
        """Run complete drift validation"""
        print(f"{Colors.CYAN}🔍 Validating AWS resources against template...{Colors.END}")
        print(f"{Colors.BLUE}Region: {self.region}{Colors.END}")
        print()
        
        # Get expected configurations from template
        expected_functions = self.parser.get_lambda_functions()
        
        if not expected_functions:
            print(f"{Colors.YELLOW}⚠️  No Lambda functions found in template{Colors.END}")
            return True
        
        # Validate each function
        for function_name, expected_config in expected_functions.items():
            self._validate_lambda_function(function_name, expected_config)
        
        # Summary
        if self.has_differences:
            print(f"\n{Colors.RED}❌ DEPLOYMENT BLOCKED: AWS Console drift detected!{Colors.END}")
            print(f"{Colors.RED}Fix these differences in AWS Console or update your template, then retry deployment.{Colors.END}")
            
            if self.interactive:
                response = input(f"\n{Colors.YELLOW}Continue anyway? [y/N]: {Colors.END}").strip().lower()
                return response in ['y', 'yes']
            
            return False
        else:
            print(f"{Colors.GREEN}✅ All resources match template configuration{Colors.END}")
            print(f"{Colors.GREEN}🚀 Deployment can proceed{Colors.END}")
            return True
    
    def _validate_lambda_function(self, function_name: str, expected_config: Dict[str, Any]):
        """Validate a single Lambda function"""
        print(f"{Colors.BLUE}Checking {function_name}...{Colors.END}")
        
        # Fetch current AWS configuration
        actual_config = self.fetcher.get_lambda_function(function_name)
        
        # Compare configurations
        diffs, is_new_function = self.diff_engine.compare_lambda_function(function_name, expected_config, actual_config)
        
        if is_new_function:
            print(f"{Colors.CYAN}  📦 New function (will be created){Colors.END}")
        elif diffs:
            self.has_differences = True
            print(f"{Colors.RED}  ❌ Differences detected:{Colors.END}")
            for diff in diffs:
                print(f"{Colors.RED}    • {diff}{Colors.END}")
        else:
            print(f"{Colors.GREEN}  ✅ Configuration matches{Colors.END}")
        
        print()

def main():
    parser = argparse.ArgumentParser(description='Validate AWS resources against SAM template')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode with prompts')
    parser.add_argument('--ci-mode', action='store_true', help='CI/CD mode (fail on drift)')
    
    args = parser.parse_args()
    
    # Determine mode
    interactive = args.interactive and not args.ci_mode
    
    if args.ci_mode:
        print(f"{Colors.BOLD}Running in CI/CD mode - will fail on any drift{Colors.END}")
    elif interactive:
        print(f"{Colors.BOLD}Running in interactive mode{Colors.END}")
    
    print()
    
    # Run validation
    validator = DriftValidator(
        region=args.region,
        profile=args.profile,
        interactive=interactive
    )
    
    success = validator.validate()
    
    if not success:
        sys.exit(1)
    
    print(f"{Colors.GREEN}Validation completed successfully{Colors.END}")

if __name__ == '__main__':
    main()
