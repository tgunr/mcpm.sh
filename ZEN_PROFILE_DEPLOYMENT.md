# 🧘 Zen Profile Deployment

## Overview

The Zen Profile Deployment approach represents a fundamental shift in how MCPM manages profiles and client configurations. Instead of running a proxy server that aggregates multiple MCP servers, this approach directly updates client configuration files with individual servers from a profile.

## Philosophy: Simplicity Through Directness

### The Zen Way
- **Direct**: No proxy layer - clients connect directly to MCP servers
- **Transparent**: You can see exactly which servers are configured in each client
- **Reliable**: Fewer moving parts, no single point of failure
- **Simple**: One command deploys servers to all clients using a profile

### Before (Proxy Approach)
```
Profile "web-dev" → FastMCP Proxy → Client connects to proxy
                         ↓
                    [server1, server2, server3]
```

### After (Zen Approach)
```
Profile "web-dev" → Direct deployment → Client config updated with:
                                      ├─ server1
                                      ├─ server2
                                      └─ server3
```

## Key Benefits

### 🚀 Performance
- **Direct connections**: No proxy overhead
- **Parallel execution**: All servers run independently
- **Better resource usage**: No centralized bottleneck

### 🔧 Reliability
- **No single point of failure**: If one server fails, others continue
- **No proxy process**: Nothing to crash or restart
- **Persistent configuration**: Survives client restarts automatically

### 👁️ Transparency
- **Visible in client configs**: See exactly what's running
- **Standard debugging**: Use client-native debugging tools
- **Clear separation**: Each server runs in its own process

### 🎯 Simplicity
- **One command deployment**: `mcpm profile run --deploy profile-name`
- **Automatic discovery**: Finds all clients using a profile
- **Intelligent updates**: Only updates what needs to change

## Usage

### Basic Deployment

Deploy a profile directly to all clients that use it:

```bash
mcpm profile deploy web-dev
```

This command:
1. Finds all clients currently using the "web-dev" profile
2. Expands the profile to individual server configurations
3. Updates each client's config file with the individual servers
4. Reports success/failure for each client

### Check Profile Status

See which clients are using a profile:

```bash
mcpm profile status web-dev
```

Output example:
```
📋 Profile Status
┌─────────────────────────────────────────┐
│ Profile: web-dev                        │
│ Description: Web development tools      │
│ Servers: 5                             │
│ Clients using profile: 2               │
│ Status: Active (deployed to clients)   │
└─────────────────────────────────────────┘

Servers in profile:
┌─────────────────┬──────┬─────────────────────────┐
│ Name            │ Type │ Command/URL             │
├─────────────────┼──────┼─────────────────────────┤
│ filesystem      │ STDIO│ uvx mcp-server-filesystem│
│ github          │ STDIO│ npx @modelcontextprotocol/server-github│
│ playwright      │ STDIO│ npx @playwright/mcp@latest│
└─────────────────┴──────┴─────────────────────────┘

Clients using this profile:
┌─────────────────┬─────────────┬─────────────────────────────────┐
│ Client          │ Status      │ Config Path                     │
├─────────────────┼─────────────┼─────────────────────────────────┤
│ claude-desktop  │ ✓ Installed │ ~/Library/Application Support/... │
│ cursor          │ ✓ Installed │ ~/.cursor/config.json          │
└─────────────────┴─────────────┴─────────────────────────────────┘

Available actions:
  • mcpm profile run --deploy web-dev - Deploy servers directly to client configs
  • mcpm profile run web-dev - Run as proxy server (legacy mode)
  • mcpm profile edit web-dev - Modify profile servers
```

### Legacy Proxy Mode

The original proxy approach is still available:

```bash
# Run as FastMCP proxy over stdio (default)
mcpm profile run web-dev

# Run as FastMCP proxy over HTTP
mcpm profile run --http web-dev

# Run as FastMCP proxy over SSE
mcpm profile run --sse web-dev
```

## Migration Guide

### From Proxy to Direct Deployment

1. **Check current setup**:
   ```bash
   mcpm profile status my-profile
   ```

2. **Deploy directly**:
   ```bash
   mcpm profile deploy my-profile
   ```

3. **Verify deployment**:
   ```bash
   mcpm client list my-client
   ```

4. **Restart clients** for changes to take effect

### Setting Up a New Profile for Direct Deployment

1. **Create profile**:
   ```bash
   mcpm profile create web-dev
   ```

2. **Add servers to profile**:
   ```bash
   mcpm profile edit web-dev
   ```

3. **Assign profile to clients**:
   ```bash
   mcpm client edit claude-desktop
   # Choose option to use profile
   ```

4. **Deploy to clients**:
   ```bash
   mcpm profile deploy web-dev
   ```

## How It Works

### Client Discovery Process

The system automatically discovers which clients are using a profile by:

1. **Scanning client configs**: Looks for servers with pattern:
   ```json
   {
     "name": "mcpm_profile_*",
     "command": "mcpm",
     "args": ["profile", "run", "--stdio-clean", "profile-name"]
   }
   ```

2. **Profile matching**: Extracts profile names from command arguments

3. **Installation verification**: Checks if clients are actually installed

### Deployment Process

When you run `mcpm profile run --deploy profile-name`:

1. **Profile validation**: Ensures profile exists and has servers
2. **Client discovery**: Finds all clients using the profile
3. **Server expansion**: Converts profile to individual server configs
4. **Config updates**: For each client:
   - Removes the profile server entry
   - Adds individual servers from the profile
   - Saves the updated configuration
5. **Result reporting**: Shows success/failure for each client

### Server Format Conversion

The system intelligently converts servers to client-compatible formats:

- **Remote servers**: Converted to stdio format using MCP proxy
- **STDIO servers**: Used directly
- **Client-specific formats**: Handled by each client manager

## Architecture

### Key Components

1. **ClientRegistry**: Manages all client types and discovery
2. **ProfileConfigManager**: Handles profile expansion and validation  
3. **BaseClientManager**: Provides profile detection and replacement methods
4. **Client Managers**: Handle client-specific configuration formats

### Profile Detection Logic

Each client manager can:
- **Extract profile names** from server configurations
- **Detect profile servers** vs regular servers
- **Replace profiles** with individual servers

### Error Handling

The system gracefully handles:
- **Missing profiles**: Clear error messages with suggestions
- **Client errors**: Per-client error reporting
- **Partial failures**: Continues with successful clients
- **Configuration issues**: Detailed error messages

## Examples

### Example 1: Web Development Profile

```bash
# Create and configure profile
mcpm profile create web-dev
mcpm install filesystem github playwright
mcpm profile edit web-dev  # Add the servers

# Assign to clients
mcpm client edit claude-desktop  # Select web-dev profile
mcpm client edit cursor          # Select web-dev profile

# Deploy directly
mcpm profile deploy web-dev
```

Result: Both Claude Desktop and Cursor will have filesystem, github, and playwright servers configured directly.

### Example 2: Data Analysis Profile

```bash
# Create profile for data work
mcpm profile create data-analysis
mcpm install sqlite pandas-mcp python-mcp
mcpm profile edit data-analysis

# Deploy to specific client
mcpm client edit claude-desktop  # Assign data-analysis profile
mcpm profile deploy data-analysis
```

### Example 3: Mixed Environment

```bash
# Some clients use FastMCP proxy, others use direct deployment
mcpm profile run data-analysis          # FastMCP proxy approach
mcpm profile deploy web-dev             # Direct deployment approach
```

## Troubleshooting

### No Clients Found

If `mcpm profile deploy profile-name` reports no clients:

1. **Check profile assignment**:
   ```bash
   mcpm profile status profile-name
   ```

2. **Assign profile to client**:
   ```bash
   mcpm client edit client-name
   ```

3. **Verify client installation**:
   ```bash
   mcpm client list
   ```

### Deployment Failures

If deployment fails for a client:

1. **Check client config path**: Ensure it's accessible
2. **Verify permissions**: Config file must be writable
3. **Check server compatibility**: Some servers may not work with all clients
4. **Review logs**: Use `MCPM_DEBUG=1` for verbose output

### Client Not Responding

After deployment, if client doesn't see new servers:

1. **Restart the client**: Required for config changes
2. **Check config file**: Verify servers were added correctly
3. **Test individual servers**: Run servers manually to verify they work

## Best Practices

### Profile Design

- **Keep profiles focused**: Group related servers together
- **Use descriptive names**: `web-dev`, `data-analysis`, not `profile1`
- **Document profiles**: Add descriptions explaining their purpose

### Deployment Strategy

- **Test first**: Use `mcpm profile status` before deploying
- **Deploy gradually**: Start with one client, then expand
- **Monitor results**: Check that all clients updated successfully

### Maintenance

- **Regular updates**: Use deployment to push profile changes
- **Profile cleanup**: Remove unused profiles and servers
- **Client hygiene**: Regularly review client configurations

## Migration Timeline

### Immediate (Available Now)
- ✅ Zen deployment functionality (`mcpm profile deploy` command)
- ✅ Profile status checking
- ✅ Automatic client discovery
- ✅ FastMCP proxy mode compatibility

### Recommended Migration Path

1. **Week 1-2**: Test zen deployment with non-critical profiles
2. **Week 3-4**: Migrate development environments
3. **Week 5+**: Migrate production setups

### Future Enhancements

- **Automatic profile sync**: Deploy when profile changes
- **Client restart integration**: Automatic client restart after deployment
- **Profile versioning**: Track deployment history
- **Rollback functionality**: Revert to previous configurations

## Conclusion

The Zen Profile Deployment approach represents a more mature, reliable, and transparent way to manage MCP server configurations. By eliminating the proxy layer and working directly with client configurations, we achieve better performance, reliability, and user experience while maintaining the powerful profile-based organization that makes MCPM so useful.

The beauty of this approach lies in its simplicity: one command deploys your entire development environment directly to your clients, with full transparency into what's running where.

**Start your zen journey**: `mcpm profile deploy your-profile-name` 🧘