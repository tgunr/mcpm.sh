#!/usr/bin/env python3
"""
Test script for MCPM CLI
Run this script directly to test the CLI without installation
"""

import os
import sys
from pathlib import Path

def setup_path():
    """Setup the Python path to include the src directory."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    src_dir = script_dir / "src"

    # Add the src directory to the path so we can import mcpm
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Verify that the mcpm module can be found
    try:
        import mcpm
        print(f"✓ MCPM module found at: {mcpm.__file__}")
    except ImportError as e:
        print(f"✗ Failed to import mcpm: {e}")
        print(f"✗ Looking for mcpm in: {src_dir}")
        print(f"✗ Current sys.path: {sys.path}")
        sys.exit(1)

def main():
    """Main entry point for the test script."""
    print("MCPM CLI Test Script")
    print("===================")
    print(f"Script location: {__file__}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print()

    # Setup the Python path
    setup_path()

    # Import and run the CLI
    try:
        from mcpm.cli import main as cli_main
        print("✓ CLI module imported successfully")
        print("Running MCPM CLI with arguments:", sys.argv[1:])
        print()

        # Run the CLI with any command line arguments passed to this script
        return cli_main()
    except Exception as e:
        print(f"✗ Error running CLI: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
