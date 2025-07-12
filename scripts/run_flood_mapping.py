# run_flood_mapping.py
"""
This script serves as the entry point for running the flood mapping process.
It orchestrates the authentication, data ingestion, preprocessing, flood detection,
and visualization steps using the flood_mapper package.
"""

import ee
import geemap
import argparse
import datetime
from flood_mapper import authentication, data_ingestion, preprocessing, flood_detection, visualization, utils, forecast


def main(event_date_str, aoi_geojson_path=None, sar_search_days=12, s2_search_days=20, export_results=False, output_folder="FloodMappingResults"):
    """
    Main function to run the flood mapping process.

    Args:
        event_date_str (str): The date of the flood event in 'YYYY-MM-DD' format.
        aoi_geojson_path (str, optional): Path to a GeoJSON file defining the Area of Interest.
                                          If None, a default AOI (Lomé) will be used.
        sar_search_days (int): Number of days before/after event_date to search for SAR images.
        s2_search_days (int): Number of days before/after event_date to search for Sentinel-2 images.
        export_results (bool): If True, exports flood extent and duration to Google Drive.
        output_folder (str): Google Drive folder name for exports.
    """
    authentication.initialize_ee()

    event_date = ee.Date(event_date_str)
    
    # Define AOI
    if aoi_geojson_path:
        try:
            AOI = utils.load_aoi_from_geojson(aoi_geojson_path)
            print(f"AOI loaded from {aoi_geojson_path}")
        except ValueError as e:
            print(f"Error loading AOI from GeoJSON: {e}. Using default AOI.")
            AOI = ee.Geometry.Polygon(
                [[[0.889893, 6.110515],
                  [0.889893, 6.342597],
                  [1.853943, 6.342597],
                  [1.853943, 6.110515],
                  [0.889893, 6.110515]]]
            )
            print("Using default AOI (Lomé, Togo).")
    else:
        AOI = ee.Geometry.Polygon(
            [[[0.889893, 6.110515],
              [0.889893, 6.342597],
              [1.853943, 6.342597],
              [1.853943, 6.110515],
              [0.889893, 6.110515]]]
        )
        print("No AOI GeoJSON path provided. Using default AOI (Lomé, Togo).")

    print(f"\nProcessing flood event for {event_date_str} in AOI: {AOI.getInfo()['coordinates']}")

    # --- Sentinel-1 Processing ---
    print("\n--- Sentinel-1 Data Processing ---")
    s1_start_date = event_date.advance(-sar_search_days, 'day')
    s1_end_date = event_date.advance(sar_search_days, 'day')
    try:
        s1_collection = data_ingestion.get_sentinel1_collection(AOI, s1_start_date, s1_end_date)
        sar_pre_event, sar_post_event = preprocessing.get_pre_and_post_sar_images(
            s1_collection, AOI, event_date, sar_search_days
        )
        print("Sentinel-1 data prepared.")
    except ValueError as e:
        print(f"Sentinel-1 processing skipped due to: {e}")
        sar_pre_event, sar_post_event = None, None

    # --- Sentinel-2 Processing ---
    print("\n--- Sentinel-2 Data Processing ---")
    s2_start_date = event_date.advance(-s2_search_days, 'day')
    s2_end_date = event_date.advance(s2_search_days, 'day')
    
    # Initialize NDWI masks and S2 flood extent to None, and areas to 0.0
    ndwi_pre_event_mask, ndwi_post_event_mask = None, None
    s2_flood_extent_image = None
    water_area_pre_event_mask, water_area_post_event_mask = 0.0, 0.0 
    s2_flood_area_sqkm = 0.0

    try:
        s2_collection = data_ingestion.get_sentinel2_collection(AOI, s2_start_date, s2_end_date)
        s2_pre_event, s2_post_event = preprocessing.get_pre_and_post_s2_images(
            s2_collection, AOI, event_date, s2_search_days
        )
        ndwi_pre_event_mask = preprocessing.calculate_ndwi(s2_pre_event).gt(0).rename("ndwi_water_pre")
        ndwi_post_event_mask = preprocessing.calculate_ndwi(s2_post_event).gt(0).rename("ndwi_water_post")
        print("Sentinel-2 data prepared and NDWI calculated.")

        # Calculate water areas from NDWI masks
        water_area_pre_event_mask = utils.calculate_area(ndwi_pre_event_mask, scale=10)
        water_area_post_event_mask = utils.calculate_area(ndwi_post_event_mask, scale=10)

        # Detect flood extent using NDWI
        s2_flood_extent_image = flood_detection.detect_flood_extent_s2_ndwi(ndwi_pre_event_mask, ndwi_post_event_mask)
        s2_flood_area_sqkm = utils.calculate_area(s2_flood_extent_image, scale=10)
        print(f"Calculated Sentinel-2 NDWI-based flood extent area: {s2_flood_area_sqkm:.2f} km²")

    except ValueError as e:
        print(f"Sentinel-2 processing skipped due to: {e}")
        s2_pre_event, s2_post_event = None, None
        ndwi_pre_event_mask, ndwi_post_event_mask = None, None

    # --- Flood Detection (SAR-based) ---
    flood_extent_image = None
    flooded_area_effective = None # Initialize effective flooded area
    flood_area_sqkm = 0.0 # Initialize SAR flood area
    effective_flood_area_sqkm = 0.0 # Initialize effective SAR flood area

    if sar_pre_event and sar_post_event:
        print("\n--- Flood Extent Detection (SAR-based) ---")
        try:
            flood_extent_image = flood_detection.detect_flood_extent(sar_pre_event, sar_post_event, AOI)
            
            # Refine flood extent with connected pixels and topography
            flooded_area_effective = flood_detection.refine_flood_extent_with_topology(
                flood_extent_image, AOI
            )
            
            # Calculate areas
            flood_area_sqkm = utils.calculate_area(flood_extent_image, scale=10)
            effective_flood_area_sqkm = utils.calculate_area(flooded_area_effective, scale=10)
            
            print(f"Calculated initial SAR-based flood extent area: {flood_area_sqkm:.2f} km²")
            print(f"Calculated effective SAR-based flooded area (after refinement): {effective_flood_area_sqkm:.2f} km²")

        except Exception as e:
            print(f"Error during SAR flood extent detection or refinement: {e}")
    else:
        print("\nSkipping SAR-based flood extent detection as SAR images are not available.")

    # --- Print Water Area Estimates ---
    print("\nWater Area Estimates (in km²):")
    print(f"Pre-event Water Area (NDWI)   : {water_area_pre_event_mask:.2f} km²")
    print(f"Post-event Water Area (NDWI)  : {water_area_post_event_mask:.2f} km²")
    print(f"Flood Extent (Sentinel-2 NDWI): {s2_flood_area_sqkm:.2f} km²")
    if flooded_area_effective:
        print(f"Initial Flood Extent (SAR)    : {flood_area_sqkm:.2f} km²")
        print(f"Effective Flooded Area (SAR)  : {effective_flood_area_sqkm:.2f} km²")
    else:
        print("SAR-based Flood Areas         : N/A (SAR processing skipped or failed)")


    # --- Flood Duration (Conceptual - requires more data or logic) ---
    # For a robust flood duration, you'd need a time-series of flood extent maps.
    # The current notebook calculates change for a single pre/post pair.
    # To implement duration, you would need to process multiple SAR pairs or S2 images
    # over a longer period and sum up the 'flooded' days for each pixel.
    # For now, let's just make a placeholder.
    flood_duration_image = None
    if flood_extent_image: # Using SAR-based for duration as it's typically more robust
         # Placeholder for flood duration: assuming the flood extent is valid for a single day.
         # For real duration, you'd iterate through a series of flood extent images.
        flood_duration_image = flood_extent_image.multiply(1).rename('flood_duration_days') # Assigns 1 day of duration where flooded

    # --- Precipitation Forecast ---
    print("\n--- Precipitation Forecast ---")
    forecast_start = event_date
    forecast_end = event_date.advance(7, 'day') # Forecast for next 7 days
    try:
        cpc_forecast = forecast.get_cpc_forecast_precipitation(AOI, forecast_start, forecast_end)
        if cpc_forecast:
            forecast_stats = forecast.get_mean_precipitation_stats(cpc_forecast, AOI)
            if forecast_stats["mean_precipitation"] is not None:
                print(f"Mean forecast precipitation over AOI for next 7 days: {forecast_stats['mean_precipitation']:.2f} mm")
            else:
                print("Could not calculate mean precipitation statistics.")
        else:
            print("No precipitation forecast image available.")
    except Exception as e:
        print(f"Error fetching precipitation forecast: {e}")

    # --- Visualization ---
    print("\n--- Generating Visualization ---")
    map_center = AOI.centroid().coordinates().getInfo()[::-1] # [lon, lat] -> [lat, lon]
    m = visualization.create_map(map_center)

    if sar_pre_event and sar_post_event:
        visualization.add_sar_layers(m, sar_pre_event, sar_post_event)
    if ndwi_pre_event_mask and ndwi_post_event_mask:
        visualization.add_ndwi_layers(m, ndwi_pre_event_mask, ndwi_post_event_mask)
    
    # Add SAR-based flood extent layers
    if flood_extent_image:
        visualization.add_flood_extent_layer(m, flood_extent_image, zoom_to_layer=False) 
    if flooded_area_effective:
        visualization.add_effective_flood_extent_layer(m, flooded_area_effective, zoom_to_layer=False) # Don't zoom here, let S2 or final zoom handle it

    # Add S2-based flood extent layer
    if s2_flood_extent_image:
        visualization.add_s2_flood_extent_layer(m, s2_flood_extent_image, zoom_to_layer=True) # Zoom to S2 flood extent

    if flood_duration_image:
        visualization.add_flood_duration_layer(m, flood_duration_image)
    if cpc_forecast:
        visualization.add_cpc_forecast_layer(m, cpc_forecast)
    
    print("\nMap ready for display (if in a Jupyter environment) or for export.")

    # --- Export Results ---
    if export_results:
        print(f"\n--- Exporting Results to Google Drive (Folder: {output_folder}) ---")
        current_date_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if flooded_area_effective: # Export effective SAR flood area
            export_description_effective_extent = f"Effective_Flood_Extent_SAR_{event_date_str.replace('-', '')}_{current_date_time}"
            utils.export_image_to_drive(flooded_area_effective, export_description_effective_extent, output_folder, AOI)
        else:
            print("No effective SAR flood extent to export.")

        if s2_flood_extent_image: # Export S2 NDWI flood area
            export_description_s2_extent = f"Flood_Extent_S2_NDWI_{event_date_str.replace('-', '')}_{current_date_time}"
            utils.export_image_to_drive(s2_flood_extent_image, export_description_s2_extent, output_folder, AOI)
        else:
            print("No Sentinel-2 NDWI flood extent to export.")

        if flood_duration_image: # Export flood duration (if calculated)
            export_description_duration = f"Flood_Duration_{event_date_str.replace('-', '')}_{current_date_time}"
            utils.export_image_to_drive(flood_duration_image, export_description_duration, output_folder, AOI)
        else:
            print("No flood duration image to export.")
            
    else:
        print("\nSkipping export of results as 'export_results' is False.")

    print("\nFlood mapping process completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated flood mapping using Google Earth Engine.")
    parser.add_argument("--event_date", type=str, required=True,
                        help="Date of the flood event (YYYY-MM-DD).")
    parser.add_argument("--aoi_path", type=str,
                        help="Path to a GeoJSON file defining the Area of Interest. Optional.")
    parser.add_argument("--sar_search_days", type=int, default=12,
                        help="Number of days before/after event date to search for Sentinel-1 images.")
    parser.add_argument("--s2_search_days", type=int, default=20,
                        help="Number of days before/after event date to search for Sentinel-2 images.")
    parser.add_argument("--export", action="store_true",
                        help="Export results (flood extent, duration) to Google Drive.")
    parser.add_argument("--output_folder", type=str, default="FloodMappingResults",
                        help="Google Drive folder name for exported results.")

    args = parser.parse_args()

    main(
        event_date_str=args.event_date,
        aoi_geojson_path=args.aoi_path,
        sar_search_days=args.sar_search_days,
        s2_search_days=args.s2_search_days,
        export_results=args.export,
        output_folder=args.output_folder
    )
