
#!/usr/bin/env python3
#visualization.py
"""
This module provides functions to create and manipulate a geemap.Map object for visualizing
flood detection data. It includes functionality to add Sentinel-1 SAR layers, NDWI water
masks, flood extent, and flood duration layers to the map. The map can be centered 
on specific coordinates and zoomed to a specified level.
It is designed to work with the geemap library and Google Earth Engine (GEE).
""" 


import geemap
import ee

def create_map(center_coords, zoom=7):
    """
    Creates and returns a geemap.Map object.

    Args:
        center_coords (list): [latitude, longitude] for map center.
        zoom (int): Initial zoom level.

    Returns:
        geemap.Map: The initialized map object.
    """
    map_obj = geemap.Map(center=center_coords, zoom=zoom)
    map_obj.add_basemap("HYBRID")
    return map_obj

def add_sar_layers(map_obj, pre_event_sar, post_event_sar):
    """
    Adds pre- and post-event SAR images to the map.

    Args:
        map_obj (geemap.Map): The map object.
        pre_event_sar (ee.Image): Pre-event smoothed SAR image.
        post_event_sar (ee.Image): Post-event smoothed SAR image.
    """
    sar_vis_params = {'bands': ['VH'], 'min': -25, 'max': 0}
    map_obj.addLayer(pre_event_sar, sar_vis_params, 'Pre-event SAR (Smoothed)')
    map_obj.addLayer(post_event_sar, sar_vis_params, 'Post-event SAR (Smoothed)')
    print("Added pre- and post-event SAR layers to the map.")

def add_ndwi_layers(map_obj, pre_event_ndwi_mask, post_event_ndwi_mask):
    """
    Adds pre- and post-event NDWI masks to the map.

    Args:
        map_obj (geemap.Map): The map object.
        pre_event_ndwi_mask (ee.Image): Pre-event NDWI water mask.
        post_event_ndwi_mask (ee.Image): Post-event NDWI water mask.
    """
    ndwi_vis_params = {"palette": ["blue"]} # Changed to blue for water
    map_obj.addLayer(pre_event_ndwi_mask.updateMask(pre_event_ndwi_mask), ndwi_vis_params, "Pre-flood Water (NDWI)")
    map_obj.addLayer(post_event_ndwi_mask.updateMask(post_event_ndwi_mask), ndwi_vis_params, "Post-flood Water (NDWI)")
    print("Added pre- and post-event NDWI water masks to the map.")

def add_flood_extent_layer(map_obj, flood_extent_image, zoom_to_layer=True):
    """
    Adds the computed flood extent layer to the map.

    Args:
        map_obj (geemap.Map): The map object.
        flood_extent_image (ee.Image): Binary image representing flood extent.
        zoom_to_layer (bool): If True, centers the map on the flood extent.
    """
    flood_vis_params = {"palette": ["red"]}
    map_obj.addLayer(flood_extent_image.updateMask(flood_extent_image), flood_vis_params, 'Initial Flood Extent (SAR)')
    if zoom_to_layer:
        map_obj.centerObject(flood_extent_image)
    print("Added initial flood extent layer to the map.")

def add_effective_flood_extent_layer(map_obj, effective_flood_extent_image, zoom_to_layer=True):
    """
    Adds the refined (effective) flood extent layer to the map.

    Args:
        map_obj (geemap.Map): The map object.
        effective_flood_extent_image (ee.Image): Refined binary image representing flood extent.
        zoom_to_layer (bool): If True, centers the map on the effective flood extent.
    """
    effective_flood_vis_params = {"palette": ["purple"]} # A different color for effective flood
    map_obj.addLayer(effective_flood_extent_image.updateMask(effective_flood_extent_image), effective_flood_vis_params, 'Effective Flood Extent (SAR Refined)')
    if zoom_to_layer:
        map_obj.centerObject(effective_flood_extent_image)
    print("Added effective flood extent layer to the map.")

def add_s2_flood_extent_layer(map_obj, s2_flood_extent_image, zoom_to_layer=False):
    """
    Adds the Sentinel-2 NDWI-based flood extent layer to the map.

    Args:
        map_obj (geemap.Map): The map object.
        s2_flood_extent_image (ee.Image): Binary image representing flood extent from NDWI.
        zoom_to_layer (bool): If True, centers the map on the S2 flood extent.
    """
    s2_flood_vis_params = {"palette": ["green"]} # A distinct color for S2 flood
    map_obj.addLayer(s2_flood_extent_image.updateMask(s2_flood_extent_image), s2_flood_vis_params, 'Flood Extent (Sentinel-2 NDWI)')
    if zoom_to_layer:
        map_obj.centerObject(s2_flood_extent_image)
    print("Added Sentinel-2 NDWI-based flood extent layer to the map.")


def add_flood_duration_layer(map_obj, flood_duration_image):
    """
    Adds the computed flood duration layer to the map.

    Args:
        map_obj (geemap.Map): The map object.
        flood_duration_image (ee.Image): Image representing flood duration.
    """
    duration_vis_params = {
        'min': 0, 'max': 30, 'palette': ['white', 'blue', 'darkblue'] # Example palette
    }
    map_obj.addLayer(flood_duration_image, duration_vis_params, 'Flood Duration (Days)')
    print("Added flood duration layer to the map.")

def add_cpc_forecast_layer(map_obj, forecast_image):
    """
    Adds the CPC forecast precipitation layer to the map.

    Args:
        map_obj (geemap.Map): The map object.
        forecast_image (ee.Image): The CPC forecast precipitation image.
    """
    if forecast_image:
        precip_vis_params = {'min': 0, 'max': 50, 'palette': ['blue', 'green', 'yellow', 'orange', 'red']}
        map_obj.addLayer(forecast_image, precip_vis_params, 'CPC Forecast Precipitation')
        print("Added CPC Forecast Precipitation layer to the map.")
    else:
        print("No CPC forecast image to add to map.")

def display_map(map_obj):
    """
    Displays the geemap map.
    """
    return map_obj
