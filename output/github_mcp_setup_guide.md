# GitHub MCP Server Setup Guide

## Step 1: Create GitHub Personal Access Token

1. **Visit GitHub Token Settings**
   - URL: https://github.com/settings/tokens
   - Or: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Click "Generate new token (classic)"**

3. **Configure Token:**
   - **Note**: `Kiro MCP Server`
   - **Expiration**: 90 days or No expiration
   
4. **Select Scopes (Required Permissions):**
   ```
   ✅ repo - Full control of private repositories
   ✅ workflow - Update GitHub Action workflows
   ✅ read:org - Read org and team membership
   ✅ gist - Create gists
   ```

5. **Generate and Copy Token**
   - Click "Generate token"
   - Copy the token (starts with `ghp_`)
   - Store it safely - you won't see it again!

## Step 2: Add Token to MCP Configuration

### Option A: Manual Edit

1. Open: `C:\Users\Cane\.kiro\settings\mcp.json`

2. Find the `github` section and update it:
   ```json
   "github": {
     "command": "npx",
     "args": [
       "-y",
       "@modelcontextprotocol/server-github"
     ],
     "env": {
       "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_YOUR_TOKEN_HERE"
     },
     "disabled": false,
     "autoApprove": []
   }
   ```

3. Replace `ghp_YOUR_TOKEN_HERE` with your actual token

4. Change `"disabled": true` to `"disabled": false"`

5. Save the file

### Option B: PowerShell Command

Run this command in PowerShell (replace YOUR_TOKEN with your actual token):

```powershell
$config = Get-Content "C:\Users\Cane\.kiro\settings\mcp.json" | ConvertFrom-Json
$config.mcpServers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_YOUR_TOKEN_HERE"
$config.mcpServers.github.disabled = $false
$config | ConvertTo-Json -Depth 10 | Out-File "C:\Users\Cane\.kiro\settings\mcp.json" -Encoding utf8
```

## Step 3: Restart Kiro

1. **Restart Kiro** or use Command Palette:
   - Press `Ctrl+Shift+P`
   - Type: `MCP: Reconnect All Servers`
   - Press Enter

2. **Verify Connection**
   - Open MCP Server view in Kiro
   - Check that `github` server shows as connected

## What You Can Do with GitHub MCP

Once enabled, you can:

- 📁 **Browse repositories** - List and explore your repos
- 📝 **Read files** - View file contents from any repo
- 🔍 **Search code** - Search across repositories
- 📊 **View issues** - List and read issues
- 🔀 **Check PRs** - View pull requests
- 📋 **Create issues** - Open new issues
- ✏️ **Create/update files** - Commit changes to repos
- 🌿 **Manage branches** - Create and manage branches

## Security Notes

- ✅ Token is stored locally on your machine
- ✅ Never commit the mcp.json file to a repository
- ✅ Revoke token anytime at: https://github.com/settings/tokens
- ✅ Use minimal required scopes for security

## Troubleshooting

### Server Won't Connect
- Verify token is correct (starts with `ghp_`)
- Check token hasn't expired
- Ensure `disabled` is set to `false`
- Try reconnecting: `MCP: Reconnect All Servers`

### Permission Errors
- Check token scopes include `repo` and `workflow`
- Regenerate token with correct permissions

### Token Expired
- Generate new token with same scopes
- Update mcp.json with new token
- Reconnect servers

## Next Steps

After setup, try these commands in Kiro:
- "List my GitHub repositories"
- "Show me the README from [repo-name]"
- "Create an issue in [repo-name]"
- "Search for [term] in my repositories"
