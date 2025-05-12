#!/usr/bin/env python3
"""
Wrapper script to run the bootstrap tool without changing into the src directory.
"""
import sys
import pathlib

# Insert the src directory into sys.path so we can import the bootstrap module
current_dir = pathlib.Path(__file__).parent.resolve()
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

# Run the main entry point
try:
    from bootstrap import main
except ImportError:
    sys.exit("Error: Could not import 'bootstrap'. Ensure the 'src' directory contains bootstrap.py.")

if __name__ == '__main__':
    main()
