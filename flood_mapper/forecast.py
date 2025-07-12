# forecasting.py
"""
This module provides functions to fetch and process CPC Global Unified Precipitation Forecast data
from Google Earth Engine (GEE). It includes functionality to retrieve a collection of forecast images
for a specified region and time, and to calculate precipitation statistics over an area of interest.
"""

import ee

def get_cpc_forecast_precipitation(roi, event_date, search_window=2):
    """
    Fetches CPC Global Unified Precipitation Forecast data for a given region and time.

    Args:
        roi (ee.Geometry.Polygon): Region of interest.
        event_date (ee.Date): Date of the event.
        search_window (int): Number of days before and after the event date to include in the search.
                             The total period will be (2 * search_window + 1) days centered on event_date.

    Returns:
        ee.Image: Cumulative precipitation forecast for the period (or the first image if sum is not used).
                  Returns None if no data is found.
    """
    event_date = ee.Date(event_date) # Ensure event_date is an ee.Date object
    start_date = event_date.advance(-search_window, 'day')
    end_date = event_date.advance(search_window, 'day') # This makes the window symmetric around event_date

    # CPC Global Unified Precipitation Forecast (daily)
    # The dataset typically provides daily precipitation.
    cpc_collection = (ee.ImageCollection('NOAA/CPC/GHCN_D')
                      .filterDate(start_date, end_date)
                      .filterBounds(roi))

    if cpc_collection.size().getInfo() < 2: # Keep the check for at least 2 images for robustness
        print("No CPC forecast data found for the specified period and region.")
        return None

    # Select the precipitation band and take the first image in the collection.
    # Note: The original request changed from .sum() to .first().
    # If cumulative precipitation over the window is desired, change .first() back to .sum().
    forecast_precip_cpc = cpc_collection.select('PRCP').first().clip(roi)
    return forecast_precip_cpc

def get_precipitation_stats(forecast_image, roi, scale=1000):
    """
    Calculates the sum of precipitation value over the AOI from a forecast image.
    Note: The function name was changed from get_mean_precipitation_stats to get_precipitation_stats,
    and the reducer was changed from ee.Reducer.mean() to ee.Reducer.sum().
    The returned key is still 'mean_precipitation', which might be misleading for a sum.

    Args:
        forecast_image (ee.Image): The precipitation forecast image.
        roi (ee.Geometry.Polygon): Region of interest.
        scale (float): The nominal scale in meters to perform the reduction.

    Returns:
        dict: A dictionary containing the sum of precipitation (under the key 'mean_precipitation').
    """
    if forecast_image is None:
        return {"mean_precipitation": None} # Keeping the key name as per user's request, but it's a sum.

    forecast_stats = forecast_image.reduceRegion(
        reducer=ee.Reducer.sum(), # Changed from mean() to sum()
        geometry=roi,
        scale=scale,
        bestEffort=True
    ).getInfo()

    # The band name for PRCP is 'PRCP'
    sum_precip = forecast_stats.get('PRCP')
    return {"mean_precipitation": sum_precip} # Keeping the key name as per user's request, but it's a sum.