# Claude Desktop Integration Guide

This guide explains how to properly integrate MCPM profiles with Claude Desktop and resolve common JSON parsing errors.

## The Problem

When using MCPM profiles directly in Claude Desktop configuration like this:

```json
{
  "mcpServers": {
    "mcpm_profile_debugging": {
      "command": "mcpm",
      "args": ["profile", "run", "debugging"]
    }
  }
}
```

Claude Desktop may encounter JSON parsing errors because:

1. **Banner Output**: FastMCP displays a startup banner that corrupts the JSON-RPC stream
2. **Log Messages**: MCPM outputs status messages during initialization
3. **Startup Messages**: Various initialization output appears before the MCP protocol begins

## The Solution: --stdio-clean Flag

MCPM provides a `--stdio-clean` flag specifically designed for MCP client integration:

### Correct Configuration

```json
{
  "mcpServers": {
    "mcpm_profile_debugging": {
      "command": "mcpm",
      "args": ["profile", "run", "--stdio-clean", "debugging"]
    }
  }
}
```

### What --stdio-clean Does

- ✅ Suppresses all MCPM logging output
- ✅ Disables status messages and progress indicators
- ✅ Reduces (but may not eliminate) FastMCP banner output
- ✅ Ensures only MCP JSON-RPC protocol messages go to stdout

## Automatic Configuration

MCPM automatically uses the `--stdio-clean` flag when generating client configurations:

### Using MCPM Client Commands

```bash
# Interactive profile selection for Claude Desktop
mcpm client edit claude-desktop

# Fix existing configurations
mcpm client fix-profiles claude-desktop

# Fix all detected clients
mcpm client fix-profiles --all
```

These commands will automatically generate configurations with the `--stdio-clean` flag.

## Manual Fixes

### Fix Existing Profile Configurations

If you have existing MCPM profile configurations in Claude Desktop that are causing JSON errors:

1. **Automatic Fix**:
   ```bash
   mcpm client fix-profiles claude-desktop
   ```

2. **Manual Fix**:
   Edit your `~/Library/Application Support/Claude/claude_desktop_config.json` and add `--stdio-clean` to any MCPM profile commands:
   
   ```json
   {
     "mcpServers": {
       "mcpm_profile_myprofile": {
         "command": "mcpm",
         "args": ["profile", "run", "--stdio-clean", "myprofile"]
       }
     }
   }
   ```

### Restart Claude Desktop

After making configuration changes, restart Claude Desktop for the changes to take effect.

## Testing Your Configuration

### Test Profile Execution

```bash
# Test that your profile works with --stdio-clean
mcpm profile run --stdio-clean your-profile-name

# Should show minimal output and work properly
```

### Validate JSON Configuration

```bash
# Check your Claude Desktop configuration
python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

## Troubleshooting

### Still Getting JSON Errors?

1. **Check the configuration syntax**:
   ```bash
   mcpm client ls -v
   ```

2. **Verify profile exists**:
   ```bash
   mcpm profile ls
   ```

3. **Test profile individually**:
   ```bash
   mcpm profile run --stdio-clean your-profile-name
   ```

4. **Check Claude Desktop logs** (if available)

### Common Issues

#### Issue: "Profile not found"
**Solution**: Ensure the profile name in your configuration matches exactly:
```bash
mcpm profile ls  # List available profiles
```

#### Issue: "Command not found"
**Solution**: Ensure MCPM is installed and in your PATH:
```bash
which mcpm
mcpm --version
```

#### Issue: FastMCP banner still appears
**Solution**: This is a known limitation. The `--stdio-clean` flag reduces output but may not eliminate the FastMCP banner entirely. This typically doesn't cause JSON parsing errors, but if it does:

1. Use individual servers instead of profiles
2. Report the issue at: https://github.com/pathintegral-institute/mcpm.sh/issues

## Best Practices

### For Profile-Based Integration

1. **Use --stdio-clean**: Always include this flag for client integration
2. **Test thoroughly**: Test your profile with the flag before using in clients
3. **Keep profiles focused**: Smaller profiles are easier to debug and more reliable

### For Individual Servers

If profiles continue to cause issues, you can use individual MCPM servers:

```json
{
  "mcpServers": {
    "mcpm_sequential_thinking": {
      "command": "mcpm",
      "args": ["run", "sequential-thinking"]
    },
    "mcpm_brave_search": {
      "command": "mcpm",
      "args": ["run", "brave-search"]
    }
  }
}
```

## Environment Variables

### Debug Mode

Set debug mode to see detailed output (useful for troubleshooting):

```bash
export MCPM_DEBUG=1
mcpm profile run --stdio-clean your-profile-name
```

**Note**: Don't use debug mode in production client configurations as it will cause JSON errors.

### Clean Environment

For maximum compatibility, ensure a clean environment:

```bash
unset MCPM_DEBUG
unset MCPM_LOG_LEVEL
```

## Support

If you continue to experience issues:

1. **Update MCPM**: `pip install --upgrade mcpm`
2. **Check GitHub Issues**: https://github.com/pathintegral-institute/mcpm.sh/issues
3. **Create a Bug Report**: Include your configuration and error messages

## Related Commands

```bash
# Profile management
mcpm profile ls                           # List profiles
mcpm profile create myprofile             # Create profile
mcpm profile edit myprofile               # Edit profile servers

# Client management  
mcpm client ls                            # List clients and their configurations
mcpm client edit claude-desktop           # Configure Claude Desktop
mcpm client fix-profiles --all            # Fix all client profile configurations

# Testing
mcpm profile run --stdio-clean myprofile  # Test profile with clean output
mcpm doctor                               # Check system health
```
