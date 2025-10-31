# run_becr.py
"""
Immutable runner file for BECR application entry point.
This file provides a fixed, unchanging entry point for the main application.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point for BECR application."""
    try:
        from compareblocks.gui.app import main as app_main
        return app_main()
    except ImportError as e:
        print(f"Error importing BECR application: {e}")
        print("Please ensure all dependencies are installed in the virtual environment.")
        return 1
    except Exception as e:
        print(f"Error running BECR application: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())