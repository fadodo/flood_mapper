# data_ingestion.py
"""
This module provides functions to collect and filter Sentinel-1 and Sentinel-2 imagery
from Google Earth Engine (GEE) for a specified region of interest (ROI) and event date.
It includes functionality to handle cloud cover in Sentinel-2 imagery and ensures
that sufficient images are available for analysis.

Author: Fifi ADODO, 
"""
# Library imports
import os
import numpy as np
import ee
from datetime import datetime
from typing import Union


def mask_edge(image):
    """
    Masks out edge pixels in an Earth Engine image where pixel values are less than -30.0.
    
    Parameters:
        image (ee.Image): The input Earth Engine image.

    Returns:
        ee.Image: The input image with an updated mask applied, excluding edge pixels.

        - adding the mask edge to remove invalid pixels
    """
    # Identify edge pixels with values less than -30.0
    edge_mask = image.lt(-30.0)
    # Combine with existing mask, and exclude edge pixels
    combined_mask = image.mask().And(edge_mask.Not())
    # Apply the new mask to the image
    return image.updateMask(combined_mask)


def get_sentinel1_collection(roi, start_date, end_date):
    """
    Collects Sentinel-1 SAR imagery for a specified region and time period.

    Args:
        roi (ee.Geometry.Polygon): Region of interest.
        start_date (ee.Date): Start date for image collection.
        end_date (ee.Date): End date for image collection.

        Before running this function, make sure to run authenticate_and_initialize(project=<project_id>). Otherwise, the function will raise an error.

    Returns:
        ee.ImageCollection: Filtered Sentinel-1 image collection.

    Raises:
        ValueError: If fewer than 2 images are found for the given criteria.

        - removed the filter on the orbiteproperties .filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
    """ 
    
    # Check if start_date and end_date are strings and convert them if necessary to 'YYYY-MM-DD' string format
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    s1_collection = (ee.ImageCollection("COPERNICUS/S1_GRD")
                     .filter(ee.Filter.eq("instrumentMode", "IW"))
                     .filter(ee.Filter.eq("resolution_meters", 10))
                     .filterBounds(roi)
                     .filterDate(start_date, end_date)
                     )

    if s1_collection.size().getInfo() < 2:
        raise ValueError(
            "No Sentinel-1 images found for the event date range and location. "
            "Consider increasing the search interval or adjusting the AOI."
        )
    else:
        print(f"\tTotal Sentinel-1 images available: {s1_collection.size().getInfo()} images")
    return s1_collection


def mask_s2_clouds(image):
  """Masks clouds in a Sentinel-2 image using the QA band.
  Args:
      image (ee.Image): A Sentinel-2 image.
  Returns:
      ee.Image: A cloud-masked Sentinel-2 image.
  """
  qa = image.select('QA60')

  # Bits 10 and 11 are clouds and cirrus, respectively.
  cloud_bit_mask = 1 << 10
  cirrus_bit_mask = 1 << 11
  # Both flags should be set to zero, indicating clear conditions.
  mask = (
      qa.bitwiseAnd(cloud_bit_mask)
      .eq(0)
      .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
  )
  return image.updateMask(mask).divide(10000)


def _check_s2_bands_validity(image, geometry, scale=10):
    """
    Helper function to check if an S2 image has valid (unmasked) pixels
    in the 'B3' and 'B8' bands within a given geometry.
    """
    # Reduce regions to get pixel counts for B3 and B8
    b3_count_property = image.select("B3").reduceRegion(ee.Reducer.count(), geometry, scale).get("B3")
    b8_count_property = image.select("B8").reduceRegion(ee.Reducer.count(), geometry, scale).get("B8")

    # Use ee.Algorithms.If to handle potential null values from .get()
    is_b3_valid = ee.Algorithms.If(
        ee.Algorithms.Is.notNull(b3_count_property),
        ee.Number(b3_count_property).gt(0),
        False # If b3_count_property is null, then it's not valid
    )
    is_b8_valid = ee.Algorithms.If(
        ee.Algorithms.Is.notNull(b8_count_property),
        ee.Number(b8_count_property).gt(0),
        False # If b8_count_property is null, then it's not valid
    )
    
    # Combine the boolean results and set a property on the image
    return image.set('has_required_bands_pixels', ee.Algorithms.And(is_b3_valid, is_b8_valid))


def get_sentinel2_collection(roi, start_date, end_date, cloud_pixel_percentage=30):
    """
    Collects Sentinel-2 imagery for a specified region and time period,
    filtering by cloud cover and ensuring images have valid pixels for NDWI.

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
                     # Pre-filter to get less cloudy granules.
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_pixel_percentage))
                     .filterBounds(roi)
                     .filterDate(start_date, end_date)
                    )
    
    if s2_collection.size().getInfo() < 2:
        raise ValueError(
            "No Sentinel-2 images found for the event date range and location. "
            "Consider increasing the search interval or adjusting the AOI."
        )
    else:
        print(f"\tTotal Sentinel-2 images available: {s2_collection.size().getInfo()} images")
    return s2_collection
