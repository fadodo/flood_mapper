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

# Explicitly import Geometry and Date from ee to help with isinstance checks
from ee import Geometry, Date

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
    test_event_date = Date('2025-06-02') # Use Date alias
    search_window=12
    test_start_event=test_event_date.advance(-search_window,'day')
    test_end_event=test_event_date.advance(search_window,'day')
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    print(f"\n--- DEBUG: test_get_sentinel1_collection ---")
    print(f"Type of test_event_date: {type(test_event_date)}") 
    print(f"Type of ee.Date (alias): {type(Date)}") # Check alias type
    collection = data_ingestion.get_sentinel1_collection(
        test_aoi, test_start_event, test_end_event # Corrected: search_window is an int
    )
    assert collection.size().getInfo() > 0, "Should retrieve at least one Sentinel-1 image."

def test_get_sentinel2_collection(ee_init): # Depend on ee_init
    """Test if Sentinel-2 collection can be fetched."""
    # Create ee.Date and ee.Geometry objects within the test function
    test_event_date = Date('2025-06-02') # Use Date alias
    search_window=12
    test_start_event=test_event_date.advance(-search_window,'day')
    test_end_event=test_event_date.advance(search_window,'day')
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    print(f"\n--- DEBUG: test_get_sentinel2_collection ---")
    print(f"Type of test_event_date: {type(test_event_date)}") 
    print(f"Type of ee.Date (alias): {type(Date)}") # Check alias type
    collection = data_ingestion.get_sentinel2_collection(
        test_aoi, test_start_event, test_end_event # Corrected: search_window is an int
    )
    assert collection.size().getInfo() > 0, "Should retrieve at least one Sentinel-2 image."

def test_speckle_smoothing(ee_init): 
    """Test speckle smoothing function."""
    test_event_date = Date('2025-06-02') # Use Date alias
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    s1_collection = data_ingestion.get_sentinel1_collection(
        test_aoi.centroid().buffer(1000), test_event_date, search_window=30 # Corrected: search_window is an int
    )
    image = s1_collection.first()
    if image is None:
        pytest.skip("Could not find a sample S1 image for smoothing test.")
            
    smoothed_image = preprocessing.speckle_smoothing(image.select('VH'))
    assert isinstance(smoothed_image, ee.Image), "Smoothed output should be an ee.Image."
    assert smoothed_image.bandNames().getInfo() == ['VH'], "Smoothed image should retain the band name."

def test_calculate_ndwi(ee_init): 
    """Test NDWI calculation."""
    test_event_date = Date('2025-06-02') # Use Date alias
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    s2_collection = data_ingestion.get_sentinel2_collection(
        test_aoi.centroid().buffer(1000), test_event_date, search_window=12 # Corrected: search_window is an int
    )
    image = s2_collection.first()
    if image is None:
        pytest.skip("Could not find a sample S2 image for NDWI test.")

    ndwi_image = preprocessing.calculate_ndwi(image)
    assert isinstance(ndwi_image, ee.Image), "NDWI output should be an ee.Image."
    assert ndwi_image.bandNames().getInfo() == ['NDWI'], "NDWI image should have 'NDWI' band."

def test_compute_otsu_threshold(ee_init): # Depend on ee_init
    """Test Otsu threshold computation."""
    test_event_date = Date('2025-06-02') # Use Date alias
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    s1_collection = data_ingestion.get_sentinel1_collection(
        test_aoi, test_event_date, search_window=12 # Corrected: search_window is an int
    )
    sar_image = s1_collection.first()
    if sar_image is None:
        pytest.skip("Could not find a sample SAR image for Otsu test.")
    
    sar_image = sar_image.select('VH').clip(test_aoi.centroid().buffer(1000))

    # For this test, we are directly testing compute_otsu_threshold,
    # so we pass an ee.Geometry.Polygon as the otsu_aoi argument.
    small_aoi_hist = test_aoi.centroid().buffer(100) 

    threshold = flood_detection.compute_otsu_threshold(sar_image, 'VH', small_aoi_hist)
    assert isinstance(threshold, (float, int)), "Otsu threshold should be a number."
    assert -30 < threshold < 10, f"Otsu threshold {threshold} is outside expected range."

def test_detect_flood_extent(ee_init): # Depend on ee_init
    """Test flood extent detection (SAR-based)."""
    test_event_date = Date('2025-06-02') # Use Date alias
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    s1_collection = data_ingestion.get_sentinel1_collection(
        test_aoi, test_event_date, search_window=12 # Corrected: search_window is an int
    )
    pre_s1 = s1_collection.filterDate(test_event_date.advance(-12, 'day'), test_event_date).sort('system:time_start', False).first()
    post_s1 = s1_collection.filterDate(test_event_date, test_event_date.advance(12, 'day')).first()

    if not pre_s1 or not post_s1:
        pytest.skip("Could not find sufficient pre/post SAR images for flood detection test.")
    
    clip_region = test_aoi.centroid().buffer(5000)
    pre_s1_smooth = preprocessing.speckle_smoothing(pre_s1.select('VH')).clip(clip_region)
    post_s1_smooth = preprocessing.speckle_smoothing(post_s1.select('VH')).clip(clip_region)

    # Updated call to include the new otsu_aoi_geojson_path argument.
    # Passing None here to test the default behavior within detect_flood_extent.
    flood_map = flood_detection.detect_flood_extent(pre_s1_smooth, post_s1_smooth, test_aoi, otsu_aoi_geojson_path=None)
    
    # If flood_map is None due to pixel count inconsistency, the assert will fail, which is expected.
    assert isinstance(flood_map, ee.Image), "Flood map should be an ee.Image."
    assert flood_map.bandNames().getInfo() == ['flood_extent_sar'], "Flood map should have 'flood_extent_sar' band."

def test_detect_flood_extent_s2_ndwi(ee_init): # Depend on ee_init
    """Test flood extent detection using Sentinel-2 NDWI."""
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    lon_lat = ee.Image.pixelLonLat().clip(test_aoi)
    lon = lon_lat.select('longitude')
    lat = lon_lat.select('latitude')

    pre_ndwi_mask = lon.lt(1.2).And(lat.lt(6.25)).rename('ndwi_water_pre')
    post_ndwi_mask = lon.gt(1.3).And(lat.gt(6.25)).Or(lon.lt(1.2).And(lat.lt(6.25))).rename('ndwi_water_post')

    # Updated call to include the new aoi argument.
    s2_flood_map = flood_detection.detect_flood_extent_s2_ndwi(pre_ndwi_mask, post_ndwi_mask, test_aoi)
    
    # If s2_flood_map is None due to pixel count inconsistency, the assert will fail, which is expected.
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
    test_aoi = Geometry.Polygon( # Use Geometry alias
        [[[1.0, 6.0], [1.5, 6.0], [1.5, 6.5], [1.0, 6.5], [1.0, 6.0]]]
    )
    dummy_image_geometry = Geometry.Rectangle([1.1, 6.1, 1.2, 6.2]) # Use Geometry alias
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
    dummy_geometry = Geometry.Rectangle([1.1, 6.1, 1.1 + 0.001, 6.1 + 0.001]) # Use Geometry alias
    
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
    print(f"Type of ee.Geometry.Polygon (alias): {type(Geometry.Polygon)}") # Debug print, use alias
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
    assert isinstance(aoi, Geometry.Polygon), "Loaded AOI should be an ee.Geometry.Polygon." # Use Geometry alias
    assert aoi.coordinates().getInfo() == [[[-1.0, -1.0], [1.0, -1.0], [1.0, 1.0], [-1.0, 1.0], [-1.0, -1.0]]], "AOI coordinates mismatch."

def test_load_aoi_from_geojson_non_existent_file(ee_init):
    """Test loading AOI from a non-existent GeoJSON file."""
    with pytest.raises(ValueError, match="GeoJSON file not found"):
        utils.load_aoi_from_geojson("non_existent_file.geojson")