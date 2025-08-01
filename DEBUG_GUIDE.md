# MCPM Debugging Guide for Zed

This guide explains how to debug the MCPM CLI application in Zed editor.

## Prerequisites

1. **Install dependencies**: Run `uv sync` in the project root to install all dependencies
2. **Zed with Python debugging support**: Ensure you have the Python extension installed in Zed

## Debug Configurations

The project includes several debug configurations in `.zed/debug.json`:

### Recommended: Debug Launcher

**Target**: `Debug Launcher (Recommended)`

This is the most robust option that:
- Automatically sets up the Python environment
- Provides clear debugging output
- Handles dependency management via `uv`
- Shows help by default if no arguments are provided

### Debug Options Available

1. **Debug Launcher (Recommended)** - Best for general debugging
2. **Debug Launcher with Args** - Pre-configured with example arguments
3. **Debug MCPM CLI Test** - Uses the original test_cli.py script
4. **Debug MCPM CLI Test Interactive** - Interactive debugging session
5. **Debug MCPM CLI Direct** - Direct module execution
6. **Debug MCPM with Custom Args** - Example with search command
7. **Python Active File (with uv)** - Debug any active Python file

## Files for Debugging

### 1. `debug_launch.py` (Recommended)

**Purpose**: Optimized debug launcher with environment setup
**Features**:
- Automatic `uv` environment detection and setup
- Clear status messages
- Proper Python path configuration
- Error handling and diagnostics

**Usage**:
```bash
# Command line testing
uv run python debug_launch.py --help
uv run python debug_launch.py search filesystem
uv run python debug_launch.py --version
```

### 2. `test_cli.py` (Original)

**Purpose**: Direct CLI testing script
**Features**:
- Path validation and diagnostics
- Module import verification
- Detailed error reporting

**Usage**:
```bash
# Command line testing
uv run python test_cli.py --help
uv run python test_cli.py install some-server
```

## Setting Up Debugging in Zed

1. **Open the project** in Zed
2. **Open any Python file** you want to debug (e.g., `src/mcpm/cli.py`)
3. **Set breakpoints** by clicking in the left margin
4. **Open the Command Palette** (Cmd+Shift+P on Mac)
5. **Type "debug"** and select "Debug: Start Debugging"
6. **Choose your debug configuration** from the list

### Recommended Workflow

1. Use `Debug Launcher (Recommended)` for most debugging sessions
2. Set breakpoints in the CLI code (`src/mcpm/cli.py`) or command modules
3. The launcher will show help by default - modify the args in the debug config for specific commands

## Troubleshooting

### "No such file" Error

This usually means:
- Dependencies aren't installed (`uv sync`)
- Python path is incorrect
- Virtual environment isn't activated

**Solution**: Use the `Debug Launcher (Recommended)` option which handles all environment setup.

### Module Import Errors

If you see `ModuleNotFoundError`:
1. Run `uv sync` to install dependencies
2. Use debug configurations that include `uv run`
3. Check that the `.venv` directory exists

### `pydantic_core` Import Error

If you see `ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`:

This indicates a binary compatibility issue between Python versions or corrupted compiled extensions.

**Solution**:
1. **Remove and rebuild the virtual environment**:
   ```bash
   rm -rf .venv
   uv sync --python 3.12
   ```

2. **Ensure consistent Python version**: The project is configured for Python 3.12. Mixing Python versions can cause binary compatibility issues.

3. **Verify the fix**:
   ```bash
   uv run python -c "import pydantic_core; print('Success!')"
   ```

This issue typically occurs when:
- System Python version changed after initial environment setup
- Binary wheels were compiled for a different Python version
- Virtual environment got corrupted

### Debugging Specific Commands

To debug a specific MCPM command:
1. Copy one of the debug configurations in `.zed/debug.json`
2. Modify the `args` array to include your command
3. Example: `["run", "python", "debug_launch.py", "install", "filesystem"]`

## Environment Variables

The debug configurations automatically set:
- `PYTHONPATH` to include the `src` directory
- Working directory to the project root
- Use the `uv` managed virtual environment

## Command Line Testing

Before debugging in Zed, test your configuration from the command line:

```bash
# Test basic functionality
uv run python debug_launch.py --help

# Test specific commands
uv run python debug_launch.py search filesystem
uv run python debug_launch.py install --help

# Test with the original script
uv run python test_cli.py --version
```

## Debug Output

Both debug scripts provide detailed output:
- Environment setup status
- Module import verification
- Python path information
- Clear error messages with stack traces

This makes it easy to identify and fix issues before starting the actual debugging session.

## Tips

1. **Start with command line testing** before using the debugger
2. **Use the Debug Launcher** for most debugging sessions
3. **Set breakpoints early** in the CLI initialization to catch startup issues
4. **Check the integrated terminal** for debug output and error messages
5. **Use `uv run`** for all Python execution to ensure proper environment