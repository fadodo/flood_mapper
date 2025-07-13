# conftest.py
import pytest
import ee
import sys
import os

# Add the project root to sys.path to ensure 'flood_mapper' is discoverable
# This assumes conftest.py is in the root of the project.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    print(f"\n--- CONTEST: Added {project_root} to sys.path. ---")

from flood_mapper import authentication # Now flood_mapper should be importable

def pytest_sessionstart(session):
    """
    Called after the Session object has been created and before performing collection and entering the run test loop.
    This is the earliest point to ensure GEE is initialized before any ee.Date or ee.Geometry objects are created
    during test collection.
    """
    try:
        authentication.initialize_ee(project_name='ee-fid')
        print("\n--- CONTEST: GEE initialized during pytest session start. ---")
        # Verify initialization by trying to access a basic GEE property
        _ = ee.Image(1).getInfo() 
        print("--- CONTEST: GEE basic operation successful. ---")
    except Exception as e:
        # If GEE initialization fails here, exit pytest immediately.
        sys.exit(f"ERROR: Failed to initialize Earth Engine in conftest.py: {e}. Please ensure you are authenticated and have access to the project.", 1)

