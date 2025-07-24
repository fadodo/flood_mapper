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

    #Check if the given list of dates is in the correct chronological order.
    if end_date <= start_date:
        raise Exception("Verify that your dates are in the correct chronological order")


    s1_collection = (ee.ImageCollection("COPERNICUS/S1_GRD")
                     .filter(ee.Filter.eq("instrumentMode", "IW"))
                     .filter(ee.Filter.eq("resolution_meters", 10))
                     .filterBounds(roi)
                     .filterDate(start_date, end_date)
                     .map(mask_edge)
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
                     # Pre-filter to get less cloudy granules.
                     .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_pixel_percentage))
                     .filterBounds(roi)
                     .filterDate(start_date, end_date)
                     .map(mask_s2_clouds)
                     )

    if s2_collection.size().getInfo() < 2:
        raise ValueError(
            "No Sentinel-2 images found for the event date range and location. "
            "Consider increasing the search interval or adjusting the AOI."
        )
    else:
        print(f"\tTotal Sentinel-2 images available: {s2_collection.size().getInfo()} images")
    return s2_collection
