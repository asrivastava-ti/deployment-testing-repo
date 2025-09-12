# Quick Drift Resolution Reference

## How to Use Drift Resolution Options

### 1. Via GitHub Actions UI

1. **Go to GitHub Repository** → **Actions** tab
2. **Click "Deploy SAM Multi-Lambda"** workflow
3. **Click "Run workflow"** button (top right)
4. **Select your options:**

```
┌─────────────────────────────────────────┐
│ Run workflow                            │
├─────────────────────────────────────────┤
│ Use workflow from                       │
│ [Branch: main ▼]                        │
│                                         │
│ How to handle drift if detected         │
│ [overwrite_console ▼]  ← SELECT THIS    │
│   ├─ prompt                             │
│   ├─ accept_console                     │
│   ├─ overwrite_console  ← FOR OVERWRITE │
│   └─ abort                              │
│                                         │
│ Force deployment bypassing all checks   │
│ [☐] force_deploy                        │
│                                         │
│ [Run workflow]                          │
└─────────────────────────────────────────┘
```

5. **Click "Run workflow"**

### 2. What Each Option Does

| Option | What Happens | When to Use |
|--------|-------------|-------------|
| `prompt` | Pauses workflow, requires manual re-run | Default - review drift first |
| `accept_console` | Downloads console changes, commits to repo | Keep useful console fixes |
| `overwrite_console` | Deploys repo code, discards console changes | Restore repo as source of truth |
| `abort` | Stops deployment completely | Need manual investigation |
| `force_deploy` | Bypasses ALL drift checks | Emergency deployments only |

### 3. Fixed Issues

✅ **`overwrite_console` now works correctly**
- Added dedicated step to handle overwrite logic
- Modified conditions to prevent workflow from failing
- Clear messaging about what will happen
- Proper deployment execution

### 4. Workflow Flow for `overwrite_console`

```
Drift Detected → overwrite_console selected → Show warning message → Deploy repo code → Overwrite console changes → Update commit tag
```

### 5. Testing the Fix

To test `overwrite_console`:

1. Make manual changes in AWS Lambda console
2. Go to GitHub Actions → Run workflow
3. Select `overwrite_console` from dropdown
4. Run workflow
5. ✅ Should deploy successfully and overwrite console changes

### 6. Troubleshooting

If `overwrite_console` still doesn't work:

1. **Check workflow logs** for specific error messages
2. **Verify permissions** - ensure workflow has necessary AWS permissions
3. **Check step conditions** - ensure the "Deploy Code (Final Step)" runs
4. **Use force_deploy** as emergency fallback

### 7. Emergency Override

If all else fails:
```
force_deploy: ☑️ true
```
This bypasses ALL drift detection and deploys immediately.

---

**The `overwrite_console` option is now fully functional and should work as expected!**
