
# authentication.py
"""                         
This module provides functions to authenticate and initialize the Google Earth Engine (GEE) library.
It includes error handling to ensure that the authentication and initialization processes are successful.
""" 

import ee

def initialize_ee(project_name=None):
    """
    Authenticates and initializes the Google Earth Engine library.

    Args:
        project_name (str, optional): The Earth Engine project ID to initialize.
                                      If None, uses the default project.
    """
    try:
        ee.Authenticate()
        ee.Initialize(project=project_name)
        print("Google Earth Engine initialized successfully.")
    except Exception as e:
        print(f"Error initializing Google Earth Engine: {e}")
        print("Please ensure you have authenticated and have access to the specified project or Google Earth Engine.")
        raise
