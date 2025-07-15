
# visualization.py
"""
This module provides functions for visualizing satellite imagery and flood maps
using the geemap library, which integrates with Google Earth Engine.
"""

import ee
import geemap

def create_map(center_coords=[0, 0], zoom=8):
    """
    Creates an interactive geemap map centered at specified coordinates with a given zoom level.

    Args:
        center_coords (list): A list of [latitude, longitude] for the map center.
        zoom (int): The initial zoom level for the map.

    Returns:
        geemap.Map: An interactive geemap map object.
    """
    m = geemap.Map(center=center_coords, zoom=zoom)
    m.add_basemap('HYBRID') # Add a satellite basemap
    return m

def add_sar_layers(m, pre_event_sar, post_event_sar, layer_names=None, vis_params=None):
    """
    Adds pre-event and post-event SAR images to the map.

    Args:
        m (geemap.Map): The geemap map object.
        pre_event_sar (ee.Image): The pre-event SAR image (e.g., 'VH' band).
        post_event_sar (ee.Image): The post-event SAR image (e.g., 'VH' band).
        layer_names (list, optional): A list of two strings for layer names [pre_name, post_name].
                                      Defaults to ['Pre-event SAR', 'Post-event SAR'].
        vis_params (dict, optional): A dictionary of visualization parameters for the SAR images.
                                     Defaults to {'min': -25, 'max': 0}.
    """
    if layer_names is None:
        layer_names = ['Pre-event SAR', 'Post-event SAR']
    if vis_params is None:
        vis_params = {'bands':['VH'], 'min': -25, 'max': 0} # Default for SAR backscatter in dB

    if pre_event_sar:
        m.addLayer(pre_event_sar, vis_params, layer_names[0])
    if post_event_sar:
        m.addLayer(post_event_sar, vis_params, layer_names[1])

def add_ndwi_layers(m, pre_event_ndwi_mask, post_event_ndwi_mask):
    """
    Adds pre-event and post-event NDWI masks to the map.

    Args:
        m (geemap.Map): The geemap map object.
        pre_event_ndwi_mask (ee.Image): The binary pre-event NDWI water mask.
        post_event_ndwi_mask (ee.Image): The binary post-event NDWI water mask.
    """
    ndwi_vis_params = {'min': 0, 'max': 1, 'palette': ['white', 'blue']}
    if pre_event_ndwi_mask:
        m.addLayer(pre_event_ndwi_mask.updateMask(pre_event_ndwi_mask), ndwi_vis_params, 'Pre-event NDWI Water')
    if post_event_ndwi_mask:
        m.addLayer(post_event_ndwi_mask.updateMask(post_event_ndwi_mask), ndwi_vis_params, 'Post-event NDWI Water')

def add_effective_flood_extent_layer(m, effective_flood_extent, zoom_to_layer=True):
    """
    Adds the refined SAR flood extent layer to the map.

    Args:
        m (geemap.Map): The geemap map object.
        effective_flood_extent (ee.Image): The refined binary flood extent image.
        zoom_to_layer (bool): If True, zooms the map to the extent of the layer.
    """
    flood_vis_params = {'palette': ['red']}
    if effective_flood_extent:
        m.addLayer(effective_flood_extent.updateMask(effective_flood_extent), flood_vis_params, 'Effective Flood Extent (SAR)')
        if zoom_to_layer:
            m.centerObject(effective_flood_extent)

def add_s2_flood_extent_layer(m, s2_flood_extent_image, zoom_to_layer=True):
    """
    Adds the Sentinel-2 NDWI flood extent layer to the map.

    Args:
        m (geemap.Map): The geemap map object.
        s2_flood_extent_image (ee.Image): The binary S2 NDWI flood extent image.
        zoom_to_layer (bool): If True, zooms the map to the extent of the layer.
    """
    s2_flood_vis_params = {'palette': ['purple']}
    if s2_flood_extent_image:
        m.addLayer(s2_flood_extent_image.updateMask(s2_flood_extent_image), s2_flood_vis_params, 'Flood Extent (S2 NDWI)')
        if zoom_to_layer:
            m.centerObject(s2_flood_extent_image)

def display_map(m):
    """
    Displays the geemap map.
    """
    return m
