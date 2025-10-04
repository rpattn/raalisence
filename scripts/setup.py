#!/usr/bin/env python3
"""Setup script for Python raalisence."""

import subprocess
import sys
import os


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 9):
        print("Error: Python 3.9 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} found ✓")


def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("Dependencies installed successfully ✓")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        print("Try running: pip install --upgrade pip")
        sys.exit(1)


def main():
    """Main setup function."""
    print("Setting up Python raalisence...")
    print()
    
    check_python_version()
    install_dependencies()
    
    print()
    print("Setup completed successfully!")
    print()
    print("Next steps:")
    print("1. Generate signing keys: python scripts/gen_keys.py")
    print("2. Create config file: cp config.example.yaml config.yaml")
    print("3. Edit config.yaml with your keys")
    print("4. Run the server: python -m python_raalisence.server")


if __name__ == "__main__":
    main()
