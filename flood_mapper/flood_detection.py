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
from flood_mapper.utils import check_same_pixel_count, load_aoi_from_geojson, calculate_area

def compute_otsu_threshold(image, band_name, otsu_aoi, scale=10, bins=256, plot=False):
    """
    Computes the Otsu threshold for a specific band within a specific region.

    Args:
        image (ee.Image): The image from which to compute the histogram.
        band_name (str): The name of the band to use for thresholding (e.g., 'VH', 'VV_minus_VH').
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

    # Check if histogram is None (e.g., no data in otsu_aoi)
    if histogram is None:
        print(f"WARNING: No histogram data found for band '{band_name}' in the specified Otsu AOI. Returning a default threshold.")
        return -20.0 # Return a sensible default or raise an error

    hist = np.array(histogram["histogram"])
    values = np.array(histogram["bucketMeans"])

    # Otsu threshold calculation
    probs = hist / np.sum(hist)
    omega = np.cumsum(probs)
    mu = np.cumsum(probs * values)
    mu_t = mu[-1]

    sigma_b_squared = (mu_t * omega - mu) ** 2 / (omega * (1 - omega) + 1e-10)

    # Handle cases where sigma_b_squared might contain NaNs or infs due to empty classes
    sigma_b_squared[np.isnan(sigma_b_squared)] = 0
    sigma_b_squared[np.isinf(sigma_b_squared)] = 0

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

def detect_flood_extent(pre_event_sar, post_event_sar, aoi, otsu_aoi=None, sar_threshold_band='VH'):
    """
    Detects flood extent using change detection on SAR imagery and Otsu's method.
    If pixel counts are inconsistent, the detection is performed only on common available pixels.

    Args:
        pre_event_sar (ee.Image): Pre-event smoothed SAR image.
        post_event_sar (ee.Image): Post-event smoothed SAR image.
        aoi (ee.Geometry.Polygon): The main Area of Interest for the analysis.
        otsu_aoi (ee.Geometry.Polygon, optional): The specific region for Otsu threshold computation.
                                        If None, a default small polygon over Lac Togo will be used.
        sar_threshold_band (str): The SAR band to use for Otsu thresholding.
                                  Options: 'VV', 'VH', or 'VV_minus_VH'.

    Returns:
        tuple: A tuple containing:
            - ee.Image: Binary image representing pre-event water.
            - ee.Image: Binary image representing post-event water.
            - ee.Image: Binary image representing flood extent.
    """
    # Determine the region for Otsu threshold calculation
    if otsu_aoi is None:
        # Use the default Lac Togo polygon if no specific Otsu AOI is provided
        aoi_hist_region = ee.Geometry.Polygon(
            [[[1.406947563254846, 6.279016328141211],
              [1.406947563254846, 6.273029988557553],
              [1.4196204943754935, 6.273029988557553],
              [1.4196204943754935, 6.279016328141211],
              [1.4069475632846, 6.279016328141211]]]
        )
        print("No specific Otsu AOI provided. Using default Otsu AOI over Lac Togo.")
    else:
        aoi_hist_region = otsu_aoi
        print(f"Using provided Otsu AOI: {aoi_hist_region.getInfo()['coordinates']}")


    # Initialize images for processing (can be original or masked)
    pre_event_sar_for_processing = pre_event_sar
    post_event_sar_for_processing = post_event_sar

    # Get a common region from one of the images for pixel count comparison
    comparison_region = pre_event_sar.geometry()

    # Check if the pixel counts are the same for SAR images
    if not check_same_pixel_count(pre_event_sar, post_event_sar, comparison_region):
        print("WARNING: Pre-event and post-event SAR images have different pixel counts. Flood detection will be performed only on common mask. Flood detection might be therefore unreliable.")
        # Create a common mask for pixels available in both images
        common_mask = pre_event_sar.mask().And(post_event_sar.mask())
        # Apply the common mask to both images
        pre_event_sar_for_processing = pre_event_sar.updateMask(common_mask)
        post_event_sar_for_processing = post_event_sar.updateMask(common_mask)
    else:
        print("Pre-event and post-event SAR images have consistent pixel counts.")

    # --- Create derived band if requested for Otsu thresholding ---
    if sar_threshold_band == 'VV_minus_VH':
        # Ensure 'VV' and 'VH' bands exist for this calculation
        if 'VV' not in pre_event_sar_for_processing.bandNames().getInfo() or \
           'VH' not in pre_event_sar_for_processing.bandNames().getInfo():
            raise ValueError("Pre-event SAR image must contain 'VV' and 'VH' bands to create 'VV_minus_VH'.")
        if 'VV' not in post_event_sar_for_processing.bandNames().getInfo() or \
           'VH' not in post_event_sar_for_processing.bandNames().getInfo():
            raise ValueError("Post-event SAR image must contain 'VV' and 'VH' bands to create 'VV_minus_VH'.")

        # Calculate VV - VH difference (often effective for water)
        pre_event_sar_for_processing = pre_event_sar_for_processing.addBands(
            pre_event_sar_for_processing.select('VV').subtract(pre_event_sar_for_processing.select('VH')).rename('VV_minus_VH')
        )
        post_event_sar_for_processing = post_event_sar_for_processing.addBands(
            post_event_sar_for_processing.select('VV').subtract(post_event_sar_for_processing.select('VH')).rename('VV_minus_VH')
        )
    elif sar_threshold_band not in pre_event_sar_for_processing.bandNames().getInfo():
        raise ValueError(f"Selected SAR threshold band '{sar_threshold_band}' not found in pre-event SAR image.")
    elif sar_threshold_band not in post_event_sar_for_processing.bandNames().getInfo():
        raise ValueError(f"Selected SAR threshold band '{sar_threshold_band}' not found in post-event SAR image.")
    
    # Use the derived band for Otsu threshold calculation
    threshold_band_name = sar_threshold_band
    threshold_pre = compute_otsu_threshold(pre_event_sar_for_processing, threshold_band_name, aoi_hist_region, plot=True)
    threshold_post = compute_otsu_threshold(post_event_sar_for_processing, threshold_band_name, aoi_hist_region, plot=True)

    print(f"Otsu Threshold for pre-event SAR image (on {threshold_band_name}): {threshold_pre:.2f}")
    print(f"Otsu Threshold for post-event SAR image (on {threshold_band_name}): {threshold_post:.2f}")

    # Create binary masks for water (values below threshold)
    # Apply thresholds to the commonly masked images if inconsistent, otherwise original
    water_pre = pre_event_sar_for_processing.select(threshold_band_name).lt(threshold_pre)
    water_post = post_event_sar_for_processing.select(threshold_band_name).lt(threshold_post)

    # Detect new flood areas (water_post AND NOT water_pre)
    # The result will inherently only contain pixels common to both original images if common_mask was applied
    #flood_extent = water_sar_post.And(water_sar_pre.Not()).rename('flood_extent_sar')
    # selfMask() will mask out pixels where the result is 0 or negative (i.e., no new water)
    flood_extent = water_post.subtract(water_pre).selfMask().rename('flood_extent_sar')

    return water_pre, water_post, flood_extent

def detect_flood_extent_s2_ndwi(pre_event_ndwi_mask, post_event_ndwi_mask, aoi): 
    """
    Detects flood extent using change detection on Sentinel-2 NDWI masks.
    If pixel counts are inconsistent, the detection is performed only on common available pixels.

    Args:
        pre_event_ndwi_mask (ee.Image): Binary water mask from pre-event NDWI (1=water, 0=land).
        post_event_ndwi_mask (ee.Image): Binary water mask from post-event NDWI (1=water, 0=land).
        aoi (ee.Geometry.Polygon): The main Area of Interest for the analysis.

    Returns:
        ee.Image: Binary image representing flood extent from NDWI.
    """
    if not pre_event_ndwi_mask or not post_event_ndwi_mask:
        raise ValueError("Both pre-event and post-event NDWI masks are required for S2 flood detection.")
    
    # Initialize masks for processing (can be original or masked)
    pre_event_ndwi_mask_for_processing = pre_event_ndwi_mask
    post_event_ndwi_mask_for_processing = post_event_ndwi_mask

    # Get a common region from one of the masks for pixel count comparison
    # Assuming both masks cover the same area, we can use the geometry of one.
    comparison_region = pre_event_ndwi_mask.geometry()

    # Check if the pixel counts are the same
    if not check_same_pixel_count(pre_event_ndwi_mask, post_event_ndwi_mask, comparison_region):
        print("WARNING: Pre-event and post-event NDWI masks have different pixel counts. Flood detection will be performed only on common mask. Flood detection might be therefore unreliable.")
        # Create a common mask for pixels available in both NDWI masks
        common_mask = pre_event_ndwi_mask.mask().And(post_event_ndwi_mask.mask())
        # Apply the common mask to both NDWI masks
        pre_event_ndwi_mask_for_processing = pre_event_ndwi_mask.updateMask(common_mask)
        post_event_ndwi_mask_for_processing = post_event_ndwi_mask.updateMask(common_mask)
    else:
        print("Pre-event and post-event NDWI masks have consistent pixel counts.")
        # No masking needed if counts are consistent, use original images for processing
        
    # Detect new flood areas (water_post AND NOT water_pre)
    # The result will inherently only contain pixels common to both original images if common_mask was applied
    #flood_extent_ndwi = post_event_ndwi_mask_for_processing.And(pre_event_ndwi_mask_for_processing.Not()).rename('flood_extent_ndwi') 

    # selfMask() will mask out pixels where the result is 0 or negative (i.e., no new water)
    flood_extent_ndwi = post_event_ndwi_mask_for_processing.subtract(pre_event_ndwi_mask_for_processing).selfMask().rename('flood_extent_ndwi')
    
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


def calculate_flood_extension(effective_flood_extent_image):
    """
    Calculates the area of the refined flood extent.

    Args:
        effective_flood_extent_image (ee.Image): The refined binary flood extent image
                                                  (output from refine_flood_extent_with_topology).
        aoi (ee.Geometry.Polygon): The Area of Interest for the calculation.

    Returns:
        float: The effective flooded area in square kilometers.
    """
    if effective_flood_extent_image is None:
        print("WARNING: Effective flood extent image is None. Cannot calculate flood extension area.")
        return 0.0

    # Calculate the area of the effective_flood_extent_image
    # The utils.calculate_area function already handles the reduction and conversion to km^2
    flooded_area_sqkm = calculate_area(effective_flood_extent_image, scale=10)
    
    print(f"Calculated Effective Flooded Area: {flooded_area_sqkm:.2f} km²")

    return flooded_area_sqkm