# Interactive Drift Resolution Guide

This guide explains how to use the interactive drift resolution system implemented in the GitHub Actions workflow.

## Overview

The workflow now includes sophisticated drift detection that can distinguish between:
- **Legitimate repository updates** (different commits) - ✅ Allowed
- **Manual console changes** (drift) - ⚠️ Requires resolution

## How It Works

### 1. Automatic Drift Detection
- Compares AWS deployed code with the **last deployed commit** (not current commit)
- Only flags as drift when someone manually modified code in AWS console
- Legitimate repo updates are recognized and allowed to proceed

### 2. Interactive Resolution Options
When drift is detected, you have 4 options:

#### Option 1: `prompt` (Default)
- Workflow pauses and shows drift details
- Requires manual approval in GitHub environment
- You must re-run with a specific resolution choice

#### Option 2: `accept_console`
- Downloads console changes and commits them to repository
- Syncs repository with AWS console state
- Continues deployment with updated code

#### Option 3: `overwrite_console`
- Deploys repository code, discarding console changes
- Overwrites manual AWS console modifications
- Restores AWS to match repository state

#### Option 4: `abort`
- Stops deployment for manual investigation
- Provides detailed instructions for resolution
- Requires manual decision before proceeding

### 3. Force Deploy Option
- `force_deploy: true` bypasses all drift checks
- Emergency override for critical deployments
- Use with caution - skips all safety checks

## Usage Examples

### Normal Push Deployment
```bash
# Automatic trigger on push to main branch
git push origin main
```

### Manual Deployment with Drift Resolution
```bash
# Via GitHub UI: Actions → Deploy SAM Multi-Lambda → Run workflow
# Set parameters:
# - drift_resolution: accept_console
# - force_deploy: false
```

### Emergency Force Deployment
```bash
# Via GitHub UI with force_deploy: true
# Bypasses all drift detection and safety checks
```

## Workflow Scenarios

### Scenario 1: No Drift Detected
```
✅ Drift Check → No drift found → Continue deployment
```

### Scenario 2: Drift Detected with Prompt
```
❌ Drift Check → Drift found → Pause for approval → Manual re-run with resolution
```

### Scenario 3: Accept Console Changes
```
❌ Drift Check → accept_console → Download & commit console changes → Deploy
```

### Scenario 4: Overwrite Console Changes
```
❌ Drift Check → overwrite_console → Deploy repo code → Overwrite AWS changes
```

## GitHub Environment Setup

The workflow uses the `production` environment which should be configured with:
- **Required reviewers**: Team members who can approve deployments
- **Protection rules**: Ensure manual approval for sensitive operations
- **Deployment branches**: Restrict to main branch only

## Resolution Decision Matrix

| Situation | Recommended Action | Reason |
|-----------|-------------------|---------|
| Minor console fixes | `accept_console` | Preserve useful manual fixes |
| Experimental console changes | `overwrite_console` | Maintain repository as source of truth |
| Unknown console changes | `abort` | Investigate before proceeding |
| Emergency deployment | `force_deploy` | Skip all checks when critical |

## Best Practices

### 1. Regular Monitoring
- Review drift detection logs regularly
- Investigate unexpected console changes
- Maintain repository as single source of truth

### 2. Team Communication
- Document why console changes were made
- Coordinate with team before accepting console changes
- Use commit messages to explain drift resolution decisions

### 3. Emergency Procedures
- Use `force_deploy` only in emergencies
- Document emergency deployments
- Review and fix drift after emergency deployment

## Troubleshooting

### Common Issues

#### "Could not retrieve file from last deployed commit"
- **Cause**: Git history not available or commit not found
- **Solution**: Ensure `fetch-depth: 0` in checkout action

#### "No previous deployment commit found"
- **Cause**: First deployment or old stack without commit tracking
- **Solution**: Normal behavior, drift detection will work on subsequent deployments

#### "Workflow paused for manual approval"
- **Cause**: Drift detected with `prompt` resolution
- **Solution**: Re-run workflow with specific `drift_resolution` choice

### Debug Information

The workflow provides detailed logging:
- Commit hashes being compared
- File checksums for verification
- Detailed diff output showing exact changes
- Function mapping information

## Security Considerations

### Permissions Required
- `contents: write` - For committing console changes when using `accept_console`
- `id-token: write` - For OIDC authentication with AWS
- `pull-requests: write` - For creating PRs if needed in future enhancements

### Environment Protection
- Production environment requires manual approval
- Reviewers can see drift details before approving
- All actions are logged and auditable

## Migration from Previous Version

If upgrading from a workflow without drift detection:
1. First deployment will skip drift detection (no previous commit tag)
2. Subsequent deployments will include full drift detection
3. No changes needed to existing stacks

## Advanced Usage

### Custom Resolution Logic
The workflow can be extended to:
- Create pull requests for console changes
- Send notifications to Slack/Teams
- Integrate with ticketing systems
- Add custom approval workflows

### Integration with CI/CD
- Combine with automated testing
- Add deployment gates based on test results
- Integrate with monitoring and alerting systems

## Support

For issues or questions:
1. Check workflow logs for detailed error messages
2. Review this guide for common scenarios
3. Contact the DevOps team for complex drift situations
4. Use `force_deploy` only as last resort

---

**Remember**: The goal is to maintain infrastructure consistency while providing flexibility for legitimate operational needs.
