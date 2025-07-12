
#!/usr/bin/env python3
# utils.py
"""
This module provides utility functions for handling geographic data in Google Earth Engine (GEE).   
It includes functions to load an Area of Interest (AOI) from a GeoJSON file, calculate the area of a binary image, and export images to Google Drive.
It is designed to work with the Earth Engine Python API and requires the GEE library to be initialized.
"""

import ee
import json

def load_aoi_from_geojson(filepath):
    """
    Loads an Area of Interest (AOI) from a GeoJSON file.

    Args:
        filepath (str): Path to the GeoJSON file.

    Returns:
        ee.Geometry.Polygon: The AOI as an Earth Engine Geometry.

    Args:
        filepath (str): Path to the GeoJSON file.

    Returns:
        ee.Geometry.Polygon: The AOI as an Earth Engine Geometry.
    
    Raises:
        ValueError: If the GeoJSON file is invalid or cannot be read.
    """
    try:
        with open(filepath, 'r') as f:
            geojson_data = json.load(f)
        
        # Ensure the GeoJSON is a FeatureCollection or a single Feature/Geometry
        if geojson_data['type'] == 'FeatureCollection':
            # Take the first feature's geometry
            geometry = geojson_data['features'][0]['geometry']
        elif geojson_data['type'] == 'Feature':
            geometry = geojson_data['geometry']
        elif geojson_data['type'] == 'Polygon' or geojson_data['type'] == 'MultiPolygon':
            geometry = geojson_data
        else:
            raise ValueError("Unsupported GeoJSON type. Must be Polygon, MultiPolygon, Feature, or FeatureCollection.")

        return ee.Geometry(geometry)
    except FileNotFoundError:
        raise ValueError(f"GeoJSON file not found at: {filepath}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid GeoJSON file: {filepath}. Please check its format.")
    except Exception as e:
        raise ValueError(f"Error loading AOI from GeoJSON: {e}")

def calculate_area(image, scale=10):
    """
    Calculates the area of a binary image (e.g., flood extent) in square kilometers.

    Args:
        image (ee.Image): A binary Earth Engine image (e.g., flood extent mask).
        scale (float): The nominal scale in meters to perform the area calculation.

    Returns:
        float: The calculated area in square kilometers.
    """
    # Assuming the image is a binary mask where 1 represents the feature of interest
    area_image = image.multiply(ee.Image.pixelArea())
    stats = area_image.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=image.geometry(), # Use image geometry for calculation
        scale=scale,
        maxPixels=1e8
    ).getInfo()
    
    # The band name should be the default 'sum' if no specific band was selected
    # or the band name of the input image if it's a single band
    band_name = image.bandNames().get(0).getInfo() if image.bandNames().size().getInfo() > 0 else 'sum'
    
    total_area_sq_m = stats.get(band_name) or stats.get('sum') # Fallback to 'sum' if band_name isn't found
    
    if total_area_sq_m is None:
        print(f"Warning: Could not retrieve area for band '{band_name}' or 'sum'. Stats: {stats}")
        return 0.0

    return total_area_sq_m / 1e6 # Convert square meters to square kilometers

def export_image_to_drive(image, description, folder, region, scale=10, crs='EPSG:4326', max_pixels=1e10):
    """
    Exports an Earth Engine image to Google Drive.

    Args:
        image (ee.Image): The Earth Engine image to export.
        description (str): A name for the export task.
        folder (str): The name of the folder in Google Drive.
        region (ee.Geometry): The region to export.
        scale (float): The resolution in meters per pixel.
        crs (str): The coordinate reference system for the export.
        max_pixels (int): The maximum number of pixels to export.
    """
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        region=region.getInfo()['coordinates'], # Ensure region is in export-compatible format
        scale=scale,
        crs=crs,
        maxPixels=max_pixels
    )
    task.start()
    print(f"Export task '{description}' started. Check your Google Drive '{folder}' folder.")
