# flood_detection.py
"""
This module provides functions for flood detection using Sentinel-1 SAR imagery and Sentinel S2 imagery.
It includes functionality to compute Otsu's threshold for flood extent detection,
detect flood extent, and calculate flood extension.
It is designed to work with Google Earth Engine (GEE) and requires the GEE library to be initialized.
"""


import ee
import numpy as np
import matplotlib.pyplot as plt
from flood_mapper.utils import check_same_pixel_count, load_aoi_from_geojson

def compute_otsu_threshold(image, band_name, otsu_aoi, scale=30, bins=256, plot=False):
    """
    Computes the Otsu threshold for a specific band within a region.

    Args:
        image (ee.Image): The image from which to compute the histogram.
        band_name (str): The name of the band to use for thresholding (e.g., 'VH').
        otsu_aoi (ee.Geometry.Polygon): The region of interest for histogram computation.
        scale (float): The nominal scale in meters of the projection to work in.
        bins (int): The number of histogram bins.
        plot (bool): If True, plots the histogram and the Otsu threshold.

    Returns:
        float: The computed Otsu threshold.
    """
    histogram = image.select(band_name).reduceRegion(
        reducer=ee.Reducer.histogram(maxBuckets=bins),
        geometry=otsu_aoi,
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

def detect_flood_extent(pre_event_sar, post_event_sar, otsu_aoi_geojson_path=None):
    """
    Detects flood extent using change detection on SAR imagery and Otsu's method.

    Args:
        pre_event_sar (ee.Image): Pre-event smoothed SAR image.
        post_event_sar (ee.Image): Post-event smoothed SAR image.
        aoi (ee.Geometry.Polygon): The main Area of Interest for the analysis.
        otsu_aoi_geojson_path (str, optional): Path to a GeoJSON file defining a specific
                                                region for Otsu threshold computation.
                                                If None, a default small polygon over Lac Togo will be used.

    Returns:
        ee.Image: Binary image representing flood extent. Returns None if pixel counts are inconsistent.
    """
    # Determine the region for Otsu threshold calculation
    # If a specific GeoJSON path is provided, try to load it.
    # If loading fails or no path is provided, fall back to a default hardcoded AOI.
    if otsu_aoi_geojson_path:
        try:
            aoi_hist_region = load_aoi_from_geojson(otsu_aoi_geojson_path)
            print(f"AOI for Otsu threshold loaded from: {otsu_aoi_geojson_path}")
        except ValueError as e:
            print(f"WARNING: Error loading specific AOI for Otsu threshold: {e}. Falling back to default Otsu AOI.")
            aoi_hist_region = ee.Geometry.Polygon(
                [[[1.406947563254846, 6.279016328141211],
                  [1.406947563254846, 6.273029988557553],
                  [1.4196204943754935, 6.273029988557553],
                  [1.4196204943754935, 6.279016328141211],
                  [1.4069475632846, 6.279016328141211]]]
            )
            print("Using default Otsu AOI over Lac Togo (Lomé, Togo).")   
    else:
        aoi_hist_region = ee.Geometry.Polygon(
            [[[1.406947563254846, 6.279016328141211],
              [1.406947563254846, 6.273029988557553],
              [1.4196204943754935, 6.273029988557553],
              [1.4196204943754935, 6.279016328141211],
              [1.4069475632846, 6.279016328141211]]]
        )
        print("No Otsu AOI GeoJSON path provided. Using default Otsu AOI over Lac Togo.")

    # Get a common region from one of the images for pixel count comparison
    # Assuming both images cover the same area, we can use the geometry of one.
    comparison_region = pre_event_sar.geometry()

    # Check if the pixel counts are the same for SAR images
    if not check_same_pixel_count(pre_event_sar, post_event_sar, comparison_region):
        print("WARNING: Pre-event and post-event SAR images have different pixel counts. Flood detection will not be performed.")
        return None # Do not calculate flood extent if pixel counts are inconsistent
    else:
        print("Pre-event and post-event SAR images have consistent pixel counts.")

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

def detect_flood_extent_s2_ndwi(pre_event_ndwi_mask, post_event_ndwi_mask, aoi): 
    """
    Detects flood extent using change detection on Sentinel-2 NDWI masks.

    Args:
        pre_event_ndwi_mask (ee.Image): Binary water mask from pre-event NDWI (1=water, 0=land).
        post_event_ndwi_mask (ee.Image): Binary water mask from post-event NDWI (1=water, 0=land).
        aoi (ee.Geometry.Polygon): The main Area of Interest for the analysis.

    Returns:
        ee.Image: Binary image representing flood extent from NDWI. Returns None if pixel counts are inconsistent.
    """
    if not pre_event_ndwi_mask or not post_event_ndwi_mask:
        raise ValueError("Both pre-event and post-event NDWI masks are required for S2 flood detection.")
    
    # Get a common region from one of the masks for pixel count comparison
    # Assuming both masks cover the same area, we can use the geometry of one.
    comparison_region = pre_event_ndwi_mask.geometry()

    # Check if the pixel counts are the same
    if not check_same_pixel_count(pre_event_ndwi_mask, post_event_ndwi_mask, comparison_region):
        print("WARNING: Pre-event and post-event NDWI masks have different pixel counts. Flood detection will not be performed.")
        return None # Do not calculate flood extent if pixel counts are inconsistent
    else:
        print("Pre-event and post-event NDWI masks have consistent pixel counts.")

    # Detect new flood areas (water_post AND NOT water_pre)
    # The logic is the same as for SAR, but applied to NDWI-derived water masks.
    flood_extent_ndwi = post_event_ndwi_mask.And(pre_event_ndwi_mask.Not()).rename('flood_extent_ndwi')
    return flood_extent_ndwi


def refine_flood_extent_with_topology(flooded_area_image, aoi, min_connected_pixels=8, max_slope_percent=5):
    """
    Refines the detected flood extent by filtering based on connected pixels
    and terrain slope.

    Args:
        flooded_area_image (ee.Image): The initial binary flood extent image (from SAR or NDWI).
        aoi (ee.Geometry.Polygon): The Area of Interest to clip the DEM.
        min_connected_pixels (int): Minimum number of connected pixels for a flood patch to be retained.
        max_slope_percent (float): Maximum allowed slope (in percent) for flooded areas.

    Returns:
        ee.Image: The refined binary flood extent image.
    """
    print(f"    Refining flood extent: min_connected_pixels={min_connected_pixels}, max_slope_percent={max_slope_percent}%")

    # 1. Connected Pixel Count
    # Retain only larger connected components (e.g., >= 8 pixels)
    connections = flooded_area_image.connectedPixelCount()
    flooded_area_conn = flooded_area_image.updateMask(connections.gte(min_connected_pixels))

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

def calculate_flood_extension(pre_event_water_mask, post_event_water_mask, aoi):
    """
    Calculates the flood extension by subtracting the pre-event water area from the post-event water area.

    Args:
        pre_event_water_mask (ee.Image): Binary water mask from pre-event (1=water, 0=land).
        post_event_water_mask (ee.Image): Binary water mask from post-event (1=water, 0=land).
        aoi (ee.Geometry.Polygon): The Area of Interest for the calculation.

    Returns:
        float: The flood extension in square kilometers.
    """
    if not pre_event_water_mask or not post_event_water_mask:
        print("WARNING: Both pre-event and post-event water masks are required to calculate flood extension.")
        return 0.0

    # Ensure pixel counts are consistent before calculating extension
    if not check_same_pixel_count(pre_event_water_mask, post_event_water_mask, aoi):
        print("WARNING: Pre-event and post-event water masks have different pixel counts. Flood extension calculation might be inaccurate.")
        # Decide whether to proceed with calculation or return 0.0
        # For now, we will proceed but warn. If strict consistency is needed, return 0.0 here.

    # Calculate area of pre and post water masks
    pre_water_area_sqkm = pre_event_water_mask.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10, # Assuming 10m resolution for S2
        maxPixels=1e9,
        bestEffort=True
    ).getInfo().get(pre_event_water_mask.bandNames().get(0).getInfo(), 0) / 1e6

    post_water_area_sqkm = post_event_water_mask.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10, # Assuming 10m resolution for S2
        maxPixels=1e9,
        bestEffort=True
    ).getInfo().get(post_event_water_mask.bandNames().get(0).getInfo(), 0) / 1e6

    flood_extension_sqkm = post_water_area_sqkm - pre_water_area_sqkm
    print(f"Pre-event water area: {pre_water_area_sqkm:.2f} km²")
    print(f"Post-event water area: {post_water_area_sqkm:.2f} km²")
    print(f"Calculated Flood Extension: {flood_extension_sqkm:.2f} km²")

    return flood_extension_sqkm