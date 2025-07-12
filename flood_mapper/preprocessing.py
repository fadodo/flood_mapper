
# preprocessing.py 
"""
This module provides functions for preprocessing Sentinel-1 and Sentinel-2 imagery.
It includes speckle smoothing for SAR images, extraction of pre- and post-event images,
and calculation of NDWI from            Sentinel-2 imagery.
It also handles the clipping of images to a specified region of interest (ROI).
It is designed to work with Google Earth Engine (GEE) and requires the GEE library to be initialized.
It is used in the flood detection pipeline to prepare images for further analysis.
"""

import ee

def speckle_smoothing(image, smoothing_radius=30):
    """
    Applies a focal mean filter to reduce speckle effect in SAR images.

    Args:
        image (ee.Image): The SAR image to smooth.
        smoothing_radius (float): The radius of the square kernel in meters.

    Returns:
        ee.Image: The smoothed SAR image.
    """
    kernel = ee.Kernel.square(smoothing_radius, units='meters')
    return image.focal_mean(kernel=kernel, iterations=1)

def get_pre_and_post_sar_images(s1_collection, roi, event_date, search_window=12, smoothing_radius=30):
    """
    Extracts and smooths pre- and post-event Sentinel-1 SAR images.

    Args:
        s1_collection (ee.ImageCollection): The full Sentinel-1 image collection.
        roi (ee.Geometry.Polygon): Region of interest.
        event_date (ee.Date): The date of the flood event.
        search_window (int): Number of days before/after event_date to search for images.
        smoothing_radius (float): Radius for speckle smoothing.

    Returns:
        tuple: (pre_event_smooth_image, post_event_smooth_image)
    """
    start_date = event_date.advance(-search_window, 'day')
    end_date = event_date.advance(search_window, 'day')

    pre_event_image = s1_collection.filterDate(start_date, event_date).sort('system:time_start', False).first()
    post_event_image = s1_collection.filterDate(event_date, end_date).first()

    if not pre_event_image or not post_event_image:
        raise ValueError(
            f"Could not find suitable pre or post event SAR images within {search_window} days of {event_date.format('YYYY-MM-dd').getInfo()}. "
            "Images may be unavailable for the post event date."
        )

    print(f"    Total Sentinel-1 images selected for pre-event: {s1_collection.filterDate(start_date, event_date).size().getInfo()} images")
    print(f"    Total Sentinel-1 images selected for post-event: {s1_collection.filterDate(event_date, end_date).size().getInfo()} images")

    pre_event_smooth_image = speckle_smoothing(pre_event_image, smoothing_radius).clip(roi)
    post_event_smooth_image = speckle_smoothing(post_event_image, smoothing_radius).clip(roi)

    return pre_event_smooth_image, post_event_smooth_image

def get_pre_and_post_s2_images(s2_collection, roi, event_date, search_window=20):
    """
    Extracts median pre- and post-event Sentinel-2 images.

    Args:
        s2_collection (ee.ImageCollection): The full Sentinel-2 image collection.
        roi (ee.Geometry.Polygon): Region of interest.
        event_date (ee.Date): The date of the flood event.
        search_window (int): Number of days before/after event_date to search for images.

    Returns:
        tuple: (s2_pre_event_median, s2_post_event_median)
    """
    start_date_s2 = event_date.advance(-search_window, 'day')
    end_date_s2 = event_date.advance(search_window, 'day')

    s2_pre_event_median = s2_collection.filterDate(start_date_s2, event_date).median().clip(roi)
    s2_post_event_median = s2_collection.filterDate(event_date, end_date_s2).median().clip(roi)

    if not s2_pre_event_median or not s2_post_event_median:
         raise ValueError(
            f"Could not find suitable pre or post event Sentinel-2 images within {search_window} days of {event_date.format('YYYY-MM-dd').getInfo()}. "
            "Images may be yet unavailable for the post event date."
        )

    return s2_pre_event_median, s2_post_event_median


def calculate_ndwi(image):
    """
    Calculates the Normalized Difference Water Index (NDWI) from a Sentinel-2 image.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: The NDWI image.
    """
    green = image.select('B3')
    nir = image.select('B8')
    ndwi = green.subtract(nir).divide(green.add(nir)).rename("NDWI")
    return ndwi
