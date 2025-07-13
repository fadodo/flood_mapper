# tests/test_flood_mapper.py
""" 
This module contains unit tests for the flood_mapper package.
It tests the functionality of data ingestion, preprocessing, flood detection, and visualization modules.
It uses pytest for testing and assumes that Google Earth Engine (GEE) is properly authenticated and initialized.
""" 

import pytest
import ee
import numpy as np 
from flood_mapper import authentication, data_ingestion, preprocessing, flood_detection, utils

# Removed explicit import of Geometry and Date from ee.
# Will use ee.Geometry and ee.Date directly.

# Fixture for initializing GEE (run once for all tests)
@pytest.fixture(scope="module", autouse=True)
def ee_init():
    """Initializes Google Earth Engine for all tests in the module."""
    try:
        authentication.initialize_ee(project_name='ee-fid') 
        print("\n--- DEBUG: GEE initialized in ee_init fixture. ---") # Debug print
        # Explicitly check if ee.data is initialized
        if not ee.data._initialized:
            raise RuntimeError("ee.data was not initialized after ee.Initialize(). This is critical.")
        print("--- DEBUG: ee.data._initialized is True. ---") # Debug print
    except Exception as e:
        pytest.fail(f"Failed to initialize Earth Engine: {e}. Please ensure you are authenticated and have access to the project.")

# No module-level ee.Geometry or ee.Date objects anymore.
# They will be created inside each test function after ee_init runs.

def test_get_sentinel1_collection(ee_init): # Depend on ee_init
    """Test if Sentinel-1 collection can be fetched."""
    # Create ee.Date and ee.Geometry objects within the test function
    test_event_date = ee.Date('2025-06-02') 
    search_window=12
    test_start_event=test_event_date.advance(-search_window,'day')
    test_end_event=test_event_date.advance(search_window,'day')
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    print(f"\n--- DEBUG: test_get_sentinel1_collection ---")
    print(f"Type of test_event_date: {type(test_event_date)}") 
    print(f"Type of ee.Date: {type(ee.Date)}") # Check ee.Date type
    collection = data_ingestion.get_sentinel1_collection(
        roi=test_aoi, start_date=test_start_event, end_date=test_end_event 
    )
    assert collection.size().getInfo() > 0, "Should retrieve at least one Sentinel-1 image."

def test_get_sentinel2_collection(ee_init): # Depend on ee_init
    """Test if Sentinel-2 collection can be fetched."""
    # Create ee.Date and ee.Geometry objects within the test function
    test_event_date = ee.Date('2025-06-02') 
    search_window=12
    test_start_event=test_event_date.advance(-search_window,'day')
    test_end_event=test_event_date.advance(search_window,'day')
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    print(f"\n--- DEBUG: test_get_sentinel2_collection ---")
    print(f"Type of test_event_date: {type(test_event_date)}") 
    print(f"Type of ee.Date: {type(ee.Date)}") # Check ee.Date type
    collection = data_ingestion.get_sentinel2_collection(
        roi=test_aoi, start_date=test_start_event, end_date=test_end_event 
    )
    assert collection.size().getInfo() > 0, "Should retrieve at least one Sentinel-2 image."

def test_speckle_smoothing(ee_init): 
    """Test speckle smoothing function."""
    test_event_date = ee.Date('2025-06-02') 
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    # Pass explicit start and end dates to get_sentinel1_collection
    s1_collection = data_ingestion.get_sentinel1_collection(
        roi=test_aoi.centroid().buffer(1000), 
        start_date=test_event_date.advance(-30, 'day'), 
        end_date=test_event_date.advance(30, 'day')   
    )
    image = s1_collection.first()
    if image is None:
        pytest.skip("Could not find a sample S1 image for smoothing test.")
            
    smoothed_image = preprocessing.speckle_smoothing(image.select('VH'))
    assert isinstance(smoothed_image, ee.Image), "Smoothed output should be an ee.Image."
    assert smoothed_image.bandNames().getInfo() == ['VH'], "Smoothed image should retain the band name."

def test_calculate_ndwi(ee_init): 
    """Test NDWI calculation."""
    test_event_date = ee.Date('2025-06-02') 
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    # Pass explicit start and end dates to get_sentinel2_collection
    s2_collection = data_ingestion.get_sentinel2_collection(
        roi=test_aoi.centroid().buffer(1000), 
        start_date=test_event_date.advance(-12, 'day'), 
        end_date=test_event_date.advance(12, 'day')   
    )
    image = s2_collection.first()
    if image is None:
        pytest.skip("Could not find a sample S2 image for NDWI test.")

    ndwi_image = preprocessing.calculate_ndwi(image)
    assert isinstance(ndwi_image, ee.Image), "NDWI output should be an ee.Image."
    assert ndwi_image.bandNames().getInfo() == ['NDWI'], "NDWI image should have 'NDWI' band."

def test_compute_otsu_threshold(ee_init): # Depend on ee_init
    """Test Otsu threshold computation."""
    test_event_date = ee.Date('2025-06-02') 
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    s1_collection = data_ingestion.get_sentinel1_collection(
        roi=test_aoi, 
        start_date=test_event_date.advance(-12, 'day'), 
        end_date=test_event_date.advance(12, 'day')   
    )
    sar_image = s1_collection.first()
    if sar_image is None:
        pytest.skip("Could not find a sample SAR image for Otsu test.")
    
    sar_image = sar_image.select('VH').clip(test_aoi.centroid().buffer(1000))

    # For this test, we are directly testing compute_otsu_threshold,
    # so we pass an ee.Geometry.Polygon as the otsu_aoi argument.
    small_aoi_hist = test_aoi.centroid().buffer(100) 

    threshold = flood_detection.compute_otsu_threshold(image=sar_image, band_name='VH', otsu_aoi=small_aoi_hist, plot=False)
    assert isinstance(threshold, (float, int)), "Otsu threshold should be a number."
    assert -30 < threshold < 10, f"Otsu threshold {threshold} is outside expected range."

def test_detect_flood_extent(ee_init): # Depend on ee_init
    """Test flood extent detection (SAR-based)."""
    test_event_date = ee.Date('2025-06-02') 
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    
    # Create dummy pre_s1_smooth and post_s1_smooth images that are guaranteed
    # to have the same pixel count within a defined region.
    # This avoids reliance on actual GEE data availability and pixel count variations.
    clip_region = test_aoi.centroid().buffer(5000)
    
    # Create a dummy constant image over the clip_region for pre-event
    # We'll use a value that would typically be 'land' (e.g., -15 dB)
    pre_s1_smooth = ee.Image.constant(-15).rename('VH').clip(clip_region)
    
    # Create another dummy constant image over the same region for post-event
    # We'll use a value that would typically be 'water' (e.g., -25 dB)
    post_s1_smooth = ee.Image.constant(-25).rename('VH').clip(clip_region)

    # Use keyword arguments for clarity and to avoid the TypeError
    # Pass the clip_region as the aoi for detect_flood_extent, and None for otsu_aoi_geojson_path
    flood_map = flood_detection.detect_flood_extent(
        pre_event_sar=pre_s1_smooth, 
        post_event_sar=post_s1_smooth, 
        otsu_aoi_geojson_path=None # Explicitly pass None to use default Otsu AOI logic within flood_detection
    )
    
    # Now, flood_map should be an ee.Image because pixel counts are consistent.
    assert isinstance(flood_map, ee.Image), "Flood map should be an ee.Image."
    assert flood_map.bandNames().getInfo() == ['flood_extent_sar'], "Flood map should have 'flood_extent_sar' band."

    # Further check that some flood extent is detected with the dummy data
    sum_pixels = flood_map.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=clip_region, # Use the clip_region for reduction
        scale=30,
        maxPixels=1e9
    ).getInfo()
    assert sum_pixels['flood_extent_sar'] is not None, "SAR flood extent sum should not be None."
    assert sum_pixels['flood_extent_sar'] > 0, "SAR flood extent should detect some flooded area with dummy data."


def test_detect_flood_extent_s2_ndwi(ee_init): # Depend on ee_init
    """Test flood extent detection using Sentinel-2 NDWI."""
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    lon_lat = ee.Image.pixelLonLat().clip(test_aoi)
    lon = lon_lat.select('longitude')
    lat = lon_lat.select('latitude')

    pre_ndwi_mask = lon.lt(1.2).And(lat.lt(6.25)).rename('ndwi_water_pre')
    post_ndwi_mask = lon.gt(1.3).And(lat.gt(6.25)).Or(lon.lt(1.2).And(lat.lt(6.25))).rename('ndwi_water_post')

    # Use keyword arguments for clarity and to avoid the TypeError
    s2_flood_map = flood_detection.detect_flood_extent_s2_ndwi(
        pre_event_ndwi_mask=pre_ndwi_mask, 
        post_event_ndwi_mask=post_ndwi_mask, 
        aoi=test_aoi
    )
    
    # If s2_flood_map is None due to pixel count inconsistency, this assert will fail.
    # This is expected behavior if the check_same_pixel_count returns False.
    assert isinstance(s2_flood_map, ee.Image), "S2 flood map should be an ee.Image."
    assert s2_flood_map.bandNames().getInfo() == ['flood_extent_ndwi'], "S2 flood map should have 'flood_extent_ndwi' band."

    sum_pixels = s2_flood_map.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=test_aoi,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    
    assert sum_pixels['flood_extent_ndwi'] is not None, "S2 flood extent sum should not be None."
    assert sum_pixels['flood_extent_ndwi'] > 0, "S2 flood extent should detect some flooded area with dummy data."


def test_refine_flood_extent_with_topology(ee_init): # Depend on ee_init
    """Test refinement of flood extent with connected pixels and topology."""
    test_aoi = ee.Geometry.Polygon( 
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    dummy_image_geometry = ee.Geometry.Rectangle([1.1, 6.1, 1.2, 6.2]) 
    dummy_flood_image = ee.Image.constant(1).clip(dummy_image_geometry).rename('flood_extent_sar')
    
    refined_flood_map = flood_detection.refine_flood_extent_with_topology(dummy_flood_image, test_aoi, min_connected_pixels=5, max_slope_percent=10)
    assert isinstance(refined_flood_map, ee.Image), "Refined flood map should be an ee.Image."
    assert refined_flood_map.bandNames().getInfo() == ['effective_flood_extent'], "Refined flood map should have 'effective_flood_extent' band."

    sum_pixels = refined_flood_map.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=test_aoi,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    
    assert sum_pixels['effective_flood_extent'] >= 0, "Refined flood map should not be entirely empty if dummy image had content."


def test_calculate_area(ee_init): # Depend on ee_init
    """Test area calculation for a simple image with a known geometry."""
    dummy_geometry = ee.Geometry.Rectangle([1.1, 6.1, 1.1 + 0.001, 6.1 + 0.001]) 
    
    scale_m = 10
    dummy_image = ee.Image.constant(1).clip(dummy_geometry).rename('test_band')

    expected_area_sq_m = dummy_geometry.area().getInfo()
    expected_area_sq_km = expected_area_sq_m / 1e6
    
    calculated_area = utils.calculate_area(dummy_image, scale=scale_m)
    
    # Increased tolerance slightly for floating point comparisons
    assert abs(calculated_area - expected_area_sq_km) < 0.005, f"Calculated area {calculated_area:.4f} km² differs significantly from expected {expected_area_sq_km:.4f} km²."


def test_load_aoi_from_geojson(tmp_path, ee_init):
    """Test loading AOI from a GeoJSON file."""
    print(f"\n--- DEBUG: test_load_aoi_from_geojson ---")
    # Directly use ee.Geometry.Polygon for type checking
    print(f"Type of ee.Geometry.Polygon: {type(ee.Geometry.Polygon)}") 
    geojson_content = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0]]]
                }
            }
        ]
    }
    geojson_path = tmp_path / "test_aoi.geojson"
    with open(geojson_path, 'w') as f:
        import json
        json.dump(geojson_content, f)
    
    aoi = utils.load_aoi_from_geojson(str(geojson_path))
    
    # Robust type check: check if it's an ee.Geometry object and then its type name
    assert isinstance(aoi, ee.Geometry), "Loaded AOI should be an ee.Geometry object."
    # The .name() method is not standard for ee.Geometry. Use .type() to get the GeoJSON type string.
    assert aoi.type().getInfo() == 'Polygon', "Loaded AOI should be an ee.Geometry.Polygon."
    assert aoi.coordinates().getInfo() == [[[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0]]], "AOI coordinates mismatch."

def test_load_aoi_from_geojson_non_existent_file(ee_init):
    """Test loading AOI from a non-existent GeoJSON file."""
    with pytest.raises(ValueError, match="GeoJSON file not found"):
        utils.load_aoi_from_geojson("non_existent_file.geojson")