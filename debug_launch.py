#!/usr/bin/env python3
"""
Debug launcher for MCPM CLI - optimized for Zed debugging
This script ensures proper environment setup and provides comprehensive debugging capabilities
"""

import os
import sys
import subprocess
import logging
import argparse
import pdb
from pathlib import Path
from typing import Optional


def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.absolute()


def ensure_uv_environment():
    """Ensure the uv virtual environment is set up and activated."""
    project_root = get_project_root()
    venv_path = project_root / ".venv"

    if not venv_path.exists():
        print("Setting up uv environment...")
        subprocess.run(["uv", "sync"], cwd=project_root, check=True)

    # Add the virtual environment to the Python path
    # Find the correct Python version directory
    lib_path = venv_path / "lib"
    if lib_path.exists():
        python_dirs = list(lib_path.glob("python3.*"))
        if python_dirs:
            site_packages = python_dirs[0] / "site-packages"
            if site_packages.exists() and str(site_packages) not in sys.path:
                sys.path.insert(0, str(site_packages))

    # Add src directory to Python path
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Setup logging configuration for debugging."""
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Setup file handler for debug logs
    project_root = get_project_root()
    log_file = project_root / "debug.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    if debug:
        print(f"Debug logging enabled - logs saved to: {log_file}")


def print_environment_info(verbose: bool = False) -> None:
    """Print comprehensive environment information."""
    print("MCPM Debug Launcher")
    print("==================")
    print(f"Project root: {get_project_root()}")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Platform: {sys.platform}")

    if verbose:
        print(f"Python path: {':'.join(sys.path)}")
        print(f"Environment variables:")
        for key, value in sorted(os.environ.items()):
            if any(env_key in key.upper() for env_key in ['PATH', 'PYTHON', 'UV', 'VIRTUAL', 'CONDA']):
                print(f"  {key}={value}")
    print()


def parse_debug_args() -> argparse.Namespace:
    """Parse command line arguments for debug launcher."""
    parser = argparse.ArgumentParser(
        description="MCPM Debug Launcher",
        add_help=False  # We'll handle help ourselves
    )
    parser.add_argument(
        "--debug-verbose", "-dv",
        action="store_true",
        help="Enable verbose debug output"
    )
    parser.add_argument(
        "--debug-pdb", "-dp",
        action="store_true",
        help="Drop into PDB debugger before running CLI"
    )
    parser.add_argument(
        "--debug-profile", "-dpr",
        action="store_true",
        help="Profile the CLI execution"
    )
    parser.add_argument(
        "--debug-log", "-dl",
        action="store_true",
        help="Enable debug logging to file"
    )

    # Parse known args, leave the rest for the CLI
    args, remaining = parser.parse_known_args()

    # Put remaining args back into sys.argv for the CLI
    sys.argv = [sys.argv[0]] + remaining

    return args


def profile_execution(func, *args, **kwargs):
    """Profile function execution."""
    import cProfile
    import pstats
    import io

    pr = cProfile.Profile()
    pr.enable()

    try:
        result = func(*args, **kwargs)
    finally:
        pr.disable()

        # Print profiling results
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions

        print("\nProfiling Results:")
        print("=" * 50)
        print(s.getvalue())

        # Save to file
        profile_file = get_project_root() / "debug_profile.prof"
        ps.dump_stats(str(profile_file))
        print(f"Full profile saved to: {profile_file}")

    return result


def main():
    """Main debug launcher with enhanced debugging capabilities."""
    # Parse debug-specific arguments first
    debug_args = parse_debug_args()

    # Setup logging
    setup_logging(
        verbose=debug_args.debug_verbose,
        debug=debug_args.debug_log
    )

    # Print environment info
    print_environment_info(verbose=debug_args.debug_verbose)

    # Ensure environment is set up
    try:
        ensure_uv_environment()
        print("✓ Environment setup complete")
        logging.info("UV environment setup completed successfully")
    except Exception as e:
        print(f"✗ Environment setup failed: {e}")
        logging.error(f"Environment setup failed: {e}")
        return 1

    # Import and run the CLI
    try:
        from mcpm.cli import main as cli_main
        print("✓ MCPM CLI imported successfully")
        logging.info("MCPM CLI imported successfully")

        # Default args if none provided
        if len(sys.argv) == 1:
            print("No arguments provided, showing help...")
            sys.argv.append("--help")

        print(f"Running with args: {sys.argv[1:]}")
        logging.info(f"CLI arguments: {sys.argv[1:]}")

        # Drop into debugger if requested
        if debug_args.debug_pdb:
            print("Dropping into PDB debugger...")
            pdb.set_trace()

        print("-" * 50)

        # Run the CLI with optional profiling
        if debug_args.debug_profile:
            return profile_execution(cli_main)
        else:
            return cli_main()

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("This usually means the virtual environment is not properly set up.")
        logging.error(f"Import error: {e}")

        # Try to provide helpful debugging info
        project_root = get_project_root()
        venv_path = project_root / ".venv"
        src_path = project_root / "src"

        print(f"\nDebugging info:")
        print(f"  .venv exists: {venv_path.exists()}")
        print(f"  src/ exists: {src_path.exists()}")
        print(f"  Current sys.path: {sys.path[:3]}...")  # First 3 entries

        return 1

    except Exception as e:
        print(f"✗ Error running CLI: {e}")
        logging.error(f"CLI execution error: {e}")
        import traceback
        traceback.print_exc()

        # Save full traceback to file for analysis
        error_file = get_project_root() / "debug_error.log"
        with open(error_file, "w") as f:
            f.write(f"Error: {e}\n")
            f.write("=" * 50 + "\n")
            traceback.print_exc(file=f)

        print(f"Full error details saved to: {error_file}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
