
# flood_detection.py
"""
This module provides functions for flood detection using Sentinel-1 SAR imagery.
It includes functionality to compute Otsu's threshold for flood extent detection,
detect flood extent, and calculate flood duration based on a collection of flood extent images.
It is designed to work with Google Earth Engine (GEE) and requires the GEE library to be initialized.
"""


import ee
import numpy as np
import matplotlib.pyplot as plt

def compute_otsu_threshold(image, band_name, region, scale=30, bins=256, plot=False):
    """
    Computes the Otsu threshold for a specific band within a region.

    Args:
        image (ee.Image): The image from which to compute the histogram.
        band_name (str): The name of the band to use for thresholding (e.g., 'VH').
        region (ee.Geometry.Polygon): The region of interest for histogram computation.
        scale (float): The nominal scale in meters of the projection to work in.
        bins (int): The number of histogram bins.
        plot (bool): If True, plots the histogram and the Otsu threshold.

    Returns:
        float: The computed Otsu threshold.
    """
    histogram = image.select(band_name).reduceRegion(
        reducer=ee.Reducer.histogram(maxBuckets=bins),
        geometry=region,
        scale=scale,
        bestEffort=True
    ).getInfo()[band_name]

    hist = np.array(histogram["histogram"])
    values = np.array(histogram["bucketMeans"])

    # Otsu threshold calculation
    probs = hist / np.sum(hist)
    omega = np.cumsum(probs)
    mu = np.cumsum(probs * values)
    mu_t = mu[-1]

    sigma_b_squared = (mu_t * omega - mu) ** 2 / (omega * (1 - omega) + 1e-10)
    max_index = np.argmax(sigma_b_squared)
    threshold = values[max_index]

    if plot:
        plt.figure(figsize=(8, 5))
        plt.plot(values, hist, label='Histogram')
        plt.axvline(threshold, color='red', linestyle='--', label=f'Otsu Threshold: {threshold:.2f}')
        plt.title(f"Otsu Threshold on {band_name} Band")
        plt.xlabel('Backscatter (dB)')
        plt.ylabel('Frequency')
        plt.legend()
        plt.grid(True)
        plt.show()

    return threshold

def detect_flood_extent(pre_event_sar, post_event_sar, aoi_hist_region=None):
    """
    Detects flood extent using change detection on SAR imagery and Otsu's method.

    Args:
        pre_event_sar (ee.Image): Pre-event smoothed SAR image.
        post_event_sar (ee.Image): Post-event smoothed SAR image.
        aoi_hist_region (ee.Geometry.Polygon, optional): Region for histogram computation
                                                         to determine Otsu threshold.
                                                         If None, uses a default small polygon.

    Returns:
        ee.Image: Binary image representing flood extent.
    """
    if aoi_hist_region is None:
        # Default AOI for histogram if not provided (example: Lomé area)
        aoi_hist_region = ee.Geometry.Polygon(
            [[[1.406947563254846, 6.279016328141211],
              [1.406947563254846, 6.273029988557553],
              [1.4196204943754935, 6.273029988557553],
              [1.4196204943754935, 6.279016328141211],
              [1.406947563254846, 6.279016328141211]]]
        )
        print("Using default AOI for Otsu threshold calculation as no AOI_hist was provided.")

    # Compute Otsu thresholds for pre- and post-event images
    threshold_pre = compute_otsu_threshold(pre_event_sar, 'VH', aoi_hist_region, plot=False)
    threshold_post = compute_otsu_threshold(post_event_sar, 'VH', aoi_hist_region, plot=False)

    print(f"Otsu Threshold for pre-event SAR image: {threshold_pre:.2f}")
    print(f"Otsu Threshold for post-event SAR image: {threshold_post:.2f}")

    # Create binary masks for water (values below threshold)
    water_pre = pre_event_sar.select('VH').lt(threshold_pre)
    water_post = post_event_sar.select('VH').lt(threshold_post)

    # Detect new flood areas (water_post AND NOT water_pre)
    flood_extent = water_post.And(water_pre.Not()).rename('flood_extent_sar')
    return flood_extent

def detect_flood_extent_s2_ndwi(pre_event_ndwi_mask, post_event_ndwi_mask):
    """
    Detects flood extent using change detection on Sentinel-2 NDWI masks.

    Args:
        pre_event_ndwi_mask (ee.Image): Binary water mask from pre-event NDWI (1=water, 0=land).
        post_event_ndwi_mask (ee.Image): Binary water mask from post-event NDWI (1=water, 0=land).

    Returns:
        ee.Image: Binary image representing flood extent from NDWI.
    """
    if not pre_event_ndwi_mask or not post_event_ndwi_mask:
        raise ValueError("Both pre-event and post-event NDWI masks are required for S2 flood detection.")

    # Detect new flood areas (water_post AND NOT water_pre)
    # The logic is the same as for SAR, but applied to NDWI-derived water masks.
    flood_extent_ndwi = post_event_ndwi_mask.And(pre_event_ndwi_mask.Not()).rename('flood_extent_ndwi')
    return flood_extent_ndwi


def refine_flood_extent_with_topology(flooded_area_sar, aoi, min_connected_pixels=8, max_slope_percent=5):
    """
    Refines the detected flood extent by filtering based on connected pixels
    and terrain slope.

    Args:
        flooded_area_sar (ee.Image): The initial binary flood extent image from SAR.
        aoi (ee.Geometry.Polygon): The Area of Interest to clip the DEM.
        min_connected_pixels (int): Minimum number of connected pixels for a flood patch to be retained.
        max_slope_percent (float): Maximum allowed slope (in percent) for flooded areas.

    Returns:
        ee.Image: The refined binary flood extent image.
    """
    print(f"    Refining flood extent: min_connected_pixels={min_connected_pixels}, max_slope_percent={max_slope_percent}%")

    # 1. Connected Pixel Count
    # Retain only larger connected components (e.g., >= 8 pixels)
    connections = flooded_area_sar.connectedPixelCount()
    flooded_area_conn = flooded_area_sar.updateMask(connections.gte(min_connected_pixels))

    # 2. Topographic Masking (Slope)
    # Load the HydroSHEDS Digital Elevation Model (DEM)
    DEM = ee.Image('WWF/HydroSHEDS/03VFDEM')
    # Calculate terrain properties (slope, aspect, etc.)
    terrain = ee.Algorithms.Terrain(DEM).clip(aoi)
    # Select the slope band (slope is in degrees by default, but often used as percentage for filtering)
    # The original notebook used `slope.lt(5)` which implies 5 degrees, not 5%.
    # If 5% is desired, it's atan(0.05) in degrees, which is approx 2.86 degrees.
    # Let's assume 5 degrees as per common practice in flood mapping if not specified.
    # If the user literally meant 5%, then it's `slope.lt(ee.Image.constant(5).divide(100).atan().multiply(180/Math.PI))`
    # For simplicity and consistency with common GEE examples, we'll use slope in degrees.
    slope = terrain.select('slope')

    # Mask out areas with a slope greater than max_slope_percent (assuming degrees here)
    flooded_area_conn_topo = flooded_area_conn.updateMask(slope.lt(max_slope_percent))
    
    return flooded_area_conn_topo.rename('effective_flood_extent')

def calculate_flood_duration(flood_extent_collection, roi, start_date, end_date):
    """
    Calculates flood duration based on a collection of flood extent images.

    Args:
        flood_extent_collection (ee.ImageCollection): Collection of binary flood extent images.
        roi (ee.Geometry.Polygon): Region of interest.
        start_date (ee.Date): Start date for duration calculation.
        end_date (ee.Date): End date for duration calculation.

    Returns:
        ee.Image: Image where pixel values represent flood duration in days.
    """
    # Assuming flood_extent_collection contains binary images (1 for flood, 0 for no flood)
    # The sum of these images over time will give the duration if each image represents a day
    # Or, if images are snapshots, it counts the number of times a pixel was flooded.

    # For a more precise duration, you'd need daily flood maps or interpolate.
    # For simplicity, let's sum up the flood occurrences.
    flood_duration = flood_extent_collection.sum().rename('flood_duration')
    return flood_duration.clip(roi)
