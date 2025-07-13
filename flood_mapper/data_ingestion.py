# data_ingestion.py
"""
This module provides functions to collect and filter Sentinel-1 and Sentinel-2 imagery
from Google Earth Engine (GEE) for a specified region of interest (ROI) and event date.
It includes functionality to handle cloud cover in Sentinel-2 imagery and ensures
that sufficient images are available for analysis.
"""

import ee

def get_sentinel1_collection(roi, start_date, end_date):
    """
    Collects Sentinel-1 SAR imagery for a specified region and time period.

    Args:
        roi (ee.Geometry.Polygon): Region of interest.
        start_date (ee.Date): Start date for image collection.
        end_date (ee.Date): End date for image collection.

    Returns:
        ee.ImageCollection: Filtered Sentinel-1 image collection.

    Raises:
        ValueError: If fewer than 2 images are found for the given criteria.
    """
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


def get_sentinel2_collection(roi, start_date, end_date, cloud_pixel_percentage=30):
    """
    Collects Sentinel-2 imagery for a specified region and time period,
    filtering by cloud cover.

    Args:
        roi (ee.Geometry.Polygon): Region of interest.
        start_date (ee.Date): Start date for image collection.
        end_date (ee.Date): End date for image collection.
        cloud_pixel_percentage (int): Maximum allowed cloudy pixel percentage (0-100).

    Returns:
        ee.ImageCollection: Filtered Sentinel-2 image collection.

    Raises:
        ValueError: If fewer than 2 images are found for the given criteria.
    """
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
