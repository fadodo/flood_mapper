# flood_mapper/utils.py
"""
This module provides essential utility functions to support the flood mapping process
within the flood_mapper package. It includes functionalities for:
- Calculating the area of Earth Engine images, typically used for flood extent.
- Loading and parsing Geographic Information System (GIS) data, specifically GeoJSON files,
  to define the Area of Interest (AOI) for analysis.
- Performing consistency checks on pixel counts between different Earth Engine images,
  which is crucial for reliable change detection.
- Exporting processed Earth Engine images as assets to your Google Earth Engine account
  for persistent storage and further use.
"""

import ee
import json

def calculate_area(image, scale=10):
    """
    Calculates the total area of unmasked pixels within an Earth Engine image,
    converting the result to square kilometers. This function is particularly
    useful for quantifying the extent of features like flooded areas or water bodies.

    Args:
        image (ee.Image): The Earth Engine image whose unmasked pixels' area is to be calculated.
                          This image is typically a binary mask (e.g., 1 for flood, 0 for no flood)
                          where only the '1' pixels contribute to the area.
        scale (float): The nominal scale (resolution) in meters at which the area calculation
                       will be performed. A smaller scale provides higher precision but requires
                       more computation.

    Returns:
        float: The calculated area in square kilometers (km²).
    """
    # Create an image where each pixel's value represents its area in square meters.
    # This is done using ee.Image.pixelArea().
    # Then, update the mask of this area image using the input 'image'. This ensures
    # that only the areas corresponding to unmasked pixels in the input 'image' are considered.
    area_image = ee.Image.pixelArea().updateMask(image)

    # Perform a reduction operation to sum up all the pixel areas within the image's geometry.
    # The reduceRegion() method aggregates pixel values over a specified region.
    stats = area_image.reduceRegion(
        reducer=ee.Reducer.sum(), # Use the sum reducer to get the total area.
        geometry=image.geometry(), # The reduction is performed over the geometry of the input image.
        scale=scale,               # Use the specified scale for the computation.
        maxPixels=1e9,             # Allow for a large number of pixels to prevent errors on big regions.
        bestEffort=True            # Use best effort to compute if exact scale is not possible.
    ).getInfo() # GetInfo() executes the Earth Engine computation and returns the result to Python.

    # Extract the total area in square meters from the results dictionary.
    # The default band name for ee.Image.pixelArea() is 'area'. We use .get(0) to safely
    # retrieve the name of the first (and usually only) band in the 'area_image'.
    total_area_sq_m = stats.get(area_image.bandNames().get(0).getInfo(), 0) 

    # Convert the total area from square meters to square kilometers.
    # Since total_area_sq_m is a standard Python float/int after getInfo(),
    # a simple Python division is used.
    return total_area_sq_m / 1e6 


def load_aoi_from_geojson(geojson_path):
    """
    Loads an Area of Interest (AOI) from a GeoJSON file, converting it into
    an Earth Engine Geometry object, typically a Polygon. This function is
    essential for defining the spatial extent of subsequent Earth Engine analyses.

    Args:
        geojson_path (str): The file path to the GeoJSON file containing the AOI definition.

    Returns:
        ee.Geometry.Polygon: The loaded AOI represented as an Earth Engine Polygon.

    Raises:
        ValueError: If the specified GeoJSON file is not found, if its content
                    is not valid JSON, or if there's any other error during
                    the loading and conversion process to an Earth Engine Geometry.
    """
    try:
        # Open and load the GeoJSON file content into a Python dictionary.
        with open(geojson_path, 'r') as f:
            geojson_data = json.load(f)
        
        # Convert the loaded GeoJSON data into an Earth Engine FeatureCollection
        # and then extract its geometry. This handles various GeoJSON types
        # (Feature, FeatureCollection, Geometry) and converts them to GEE geometries.
        return ee.FeatureCollection(geojson_data).geometry()
    except FileNotFoundError:
        raise ValueError(f"GeoJSON file not found at: {geojson_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid GeoJSON format in file: {geojson_path}")
    except Exception as e:
        raise ValueError(f"Error loading AOI from GeoJSON: {e}")
    

def check_same_pixel_count(image1, image2, region, scale=10):
    """
    Compares two Earth Engine images to determine if they have an identical number
    of unmasked pixels within a specified region and at a given scale. This check
    is crucial for change detection workflows where consistent image extents and
    valid pixel coverage are assumed.

    Args:
        image1 (ee.Image): The first Earth Engine image to compare.
        image2 (ee.Image): The second Earth Engine image to compare.
        region (ee.Geometry.Polygon): The geographic region within which the pixel
                                      counts will be performed.
        scale (float): The nominal scale in meters at which the pixels will be counted.
                       This influences the resolution of the count.

    Returns:
        bool: True if the number of unmasked pixels in both images within the
              specified region and scale are exactly equal, False otherwise.
    """
    # Reduce each image to get the count of its unmasked pixels within the defined region.
    # ee.Reducer.count() counts all unmasked pixels.
    count1 = image1.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=region,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True
    ).getInfo()

    count2 = image2.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=region,
        scale=scale,
        maxPixels=1e9,
        bestEffort=True
    ).getInfo()

    # Extract the pixel count from the result dictionary for each image.
    # We assume the relevant count is in the first band of the reduced region result.
    pixel_count1 = count1.get(image1.bandNames().get(0).getInfo(), 0)
    pixel_count2 = count2.get(image2.bandNames().get(0).getInfo(), 0)

    print(f"Pixel count for pre_event image: {pixel_count1}")
    print(f"Pixel count for post_event image: {pixel_count2}")

    # Return True if the pixel counts are identical, False otherwise.
    return pixel_count1 == pixel_count2


def export_image_to_asset(image, description, asset_id_prefix, aoi, scale=10):
    """
    Initiates an Earth Engine export task to save a processed image as a new
    asset within your Google Earth Engine account. This allows for persistent
    storage and sharing of results.

    Args:
        image (ee.Image): The Earth Engine image to be exported.
        description (str): A descriptive string for the export task, which will
                           also form part of the final asset ID.
        asset_id_prefix (str): The base path in your GEE assets where the image
                               will be stored (e.g., 'users/your_username/my_folder/').
                               The final asset ID will be constructed as
                               `asset_id_prefix + description`.
        aoi (ee.Geometry.Polygon): The region of interest to which the image
                                   will be clipped before export. This ensures
                                   only the relevant area is exported.
        scale (float): The nominal resolution in meters for the exported image.
                       This dictates the pixel size of the output asset.
    """
    # Construct the full asset ID by combining the prefix and the description.
    full_asset_id = f"{asset_id_prefix}{description}"    

    print(f"Exporting image to GEE Asset: {full_asset_id}")
    # Define and start the export task.
    task = ee.batch.Export.image.toAsset(
        image=image.clip(aoi), # Clip the image to the AOI before exporting.
        description=description, # Assign the task a descriptive name.
        assetId=full_asset_id,   # Specify the full path for the new asset.
        scale=scale,             # Set the output resolution.
        region=aoi.getInfo()['coordinates'], # Define the export region using AOI coordinates.
        maxPixels=1e16           # Allow for a very large number of pixels for comprehensive exports.
    )
    task.start() # Start the export task.
    print(f"Export task '{description}' started. Check your GEE Tasks tab for status.")
