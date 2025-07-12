
# data_ingestion.py
"""
This module provides functions to collect and filter Sentinel-1 and Sentinel-2 imagery
from Google Earth Engine (GEE) for a specified region of interest (ROI) and event date.
It includes functionality to handle cloud cover in Sentinel-2 imagery and ensures
that sufficient images are available for analysis.
"""

import ee

def get_sentinel1_collection(roi, event_date, search_window=12):
    """
    Collects Sentinel-1 SAR imagery for a specified region and time period.

    Args:
        roi (ee.Geometry.Polygon): Region of interest.
        event_date (ee.Date): Event date for image collection.
        search_window (int): Number of days before and after the event date to include.

    Returns:
        ee.ImageCollection: Filtered Sentinel-1 image collection.

    Raises:
        ValueError: If no images are found for the given criteria.
    """
    # Ensure event_date is an ee.Date object. If it's already one, this does nothing.
    # If it's a string, it converts it.
    event_date = ee.Date(event_date) 
    start_date = event_date.advance(-search_window, 'day')  # 12 days before the event date
    end_date = event_date.advance(search_window, 'day')  # 12 days after

    s1_collection = (ee.ImageCollection("COPERNICUS/S1_GRD")
                     .filter(ee.Filter.eq("instrumentMode", "IW"))
                     .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
                     .filter(ee.Filter.eq("resolution_meters", 10))
                     .filterBounds(roi)
                     .filterDate(start_date, end_date))

    if s1_collection.size().getInfo() < 2:
        raise ValueError(
            "No Sentinel-1 images found for the event date range and location. "
            "Consider increasing the search interval or adjusting the AOI."
        )
    else:
        print(f"\tTotal Sentinel-1 images available: {s1_collection.size().getInfo()} images")
    return s1_collection


def get_sentinel2_collection(roi, event_date, search_window=20, cloud_pixel_percentage=30):
    """
    Collects Sentinel-2 imagery for a specified region and time period,
    filtering by cloud cover.

    Args:
        roi (ee.Geometry.Polygon): Region of interest.
        event_date (ee.Date): Event date for image collection.
        search_window (int): Number of days before and after the event date to include.
        cloud_pixel_percentage (int): Maximum allowed cloudy pixel percentage (0-100).

    Returns:
        ee.ImageCollection: Filtered Sentinel-2 image collection.

    Raises:
        ValueError: If no images are found for the given criteria.
    """
    # FIX: The original code had `event_date = ee.Date(start_date)` which is incorrect.
    # It should use the passed `event_date` argument.
    event_date = ee.Date(event_date) # Ensure it's an ee.Date object
    start_date = event_date.advance(-search_window, 'day')  
    end_date = event_date.advance(search_window, 'day')  
    s2_collection = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_pixel_percentage))
                     .filterBounds(roi)
                     .filterDate(start_date, end_date))

    if s2_collection.size().getInfo() < 2:
        raise ValueError(
            "No Sentinel-2 images found for the event date range and location. "
            "Consider increasing the search interval or adjusting the AOI."
        )
    else:
        print(f"\tTotal Sentinel-2 images available: {s2_collection.size().getInfo()} images")
    return s2_collection
