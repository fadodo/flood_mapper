# scripts/run_flood_mapping.py
"""
This script serves as the entry point for running the flood mapping process.
It orchestrates the authentication, data ingestion, preprocessing, flood detection,
and visualization steps using the flood_mapper package.
"""

import ee
import geemap
import argparse
import datetime
from flood_mapper import authentication, data_ingestion, preprocessing, flood_detection, visualization, utils


def main(event_date_str, aoi_geojson_path=None, otsu_aoi_path=None, sar_search_days=12, s2_search_days=20, 
         export_results=False, asset_id_prefix="project/ee-fid/FloodMappingResults/", 
         detection_method="both"):
    """
    Main function to run the flood mapping process.

    Args:
        event_date_str (str): The date of the flood event in 'YYYY-MM-DD' format.
        aoi_geojson_path (str, optional): Path to a GeoJSON file defining the main Area of Interest.
                                          If None, a default AOI (Lomé) will be used.
        otsu_aoi_path (str, optional): Path to a GeoJSON file defining a specific
                                                region for Otsu threshold computation.
                                                If None, the default Lac Togo polygon will be used internally
                                                by flood_detection.py.
        sar_search_days (int): Number of days before/after event_date to search for SAR images.
        s2_search_days (int): Number of days before/after event_date to search for Sentinel-2 images.
        export_results (bool): If True, exports flood extent and duration to Google Earth Engine assets.
        asset_id_prefix (str): GEE asset ID prefix (e.g., 'users/your_username/my_folder/').
        detection_method (str): Method for flood detection: 'sar', 's2', or 'both'.
    """
    authentication.initialize_ee()

    event_date = ee.Date(event_date_str)
    
    # Define main AOI
    if aoi_geojson_path:
        try:
            AOI = utils.load_aoi_from_geojson(aoi_geojson_path)
            print(f"Main AOI loaded from {aoi_geojson_path}")
        except ValueError as e:
            print(f"Error loading main AOI from GeoJSON: {e}. Using default AOI.")
            AOI = ee.Geometry.Polygon(
                [[[0.889893, 6.110515],
                  [0.889893, 6.342597],
                  [1.853943, 6.342597],
                  [1.853943, 6.110515],
                  [0.889893, 6.110515]]]
            )
            print("Using default main AOI (Lomé, Togo).")
    else:
        AOI = ee.Geometry.Polygon(
            [[[0.889893, 6.110515],
              [0.889893, 6.342597],
              [1.853943, 6.342597],
              [1.853943, 6.110515],
              [0.889893, 6.110515]]]
        )
        print("No main AOI GeoJSON path provided. Using default main AOI (Lomé, Togo).")

    # Define Otsu AOI (if provided, otherwise pass None to flood_detection for its default)
    otsu_aoi_geometry = None
    if otsu_aoi_path:
        try:
            otsu_aoi_geometry = utils.load_aoi_from_geojson(otsu_aoi_path)
            print(f"Specific Otsu AOI loaded from {otsu_aoi_path}")
        except ValueError as e:
            print(f"WARNING: Error loading specific Otsu AOI from GeoJSON: {e}. Flood detection will use its internal default Otsu AOI.")
            # otsu_aoi_geometry remains None, which will trigger the default in flood_detection.py
    else:
        print("No specific Otsu AOI GeoJSON path provided. Flood detection will use its internal default Otsu AOI (Lac Togo).")


    print(f"\nProcessing flood event for {event_date_str} in main AOI: {AOI.getInfo()['coordinates']}")

    sar_pre_event, sar_post_event = None, None
    s2_pre_event, s2_post_event = None, None
    ndwi_pre_event_mask, ndwi_post_event_mask = None, None

    s1_flood_extent_image = None
    s1_flooded_extend_image = None 
    s1_flooded_area_sqkm = 0.0

    s2_flood_extent_image = None
    s2_flooded_extent_image = None
    s2_flooded_area_sqkm = 0.0

    # --- Conditional Data Processing and Flood Detection ---

    if detection_method in ["sar", "both"]:
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

            # --- Flood Detection (SAR-based) ---
            print("\n--- Flood Extent Detection (SAR-based) ---")
            # Pass otsu_aoi_geometry directly
            s1_flood_extent_image = flood_detection.detect_flood_extent(
                pre_event_sar=sar_pre_event, 
                post_event_sar=sar_post_event, 
                aoi=AOI, # Main AOI for clipping/context
                otsu_aoi=otsu_aoi_geometry # Pass the ee.Geometry directly
            )
            
            if s1_flood_extent_image: # Only refine if initial flood extent was calculated
                s1_flooded_extend_image = flood_detection.refine_flood_extent_with_topology(s1_flood_extent_image, AOI)
                s1_flooded_area_sqkm = flood_detection.calculate_flood_extension(s1_flooded_extend_image, AOI) # Updated call
                print(f"Calculated effective SAR-based flooded area (after refinement): {s1_flooded_area_sqkm:.2f} km²")
            else:
                print("SAR-based flood extent not calculated due to inconsistent pixel counts or other issues.")

        except ValueError as e:
            print(f"Sentinel-1 processing skipped due to: {e}")
            sar_pre_event, sar_post_event = None, None
            s1_flood_extent_image = None
            s1_flooded_extend_image = None
        except Exception as e:
            print(f"Error during SAR flood extent detection or refinement: {e}")
            s1_flood_extent_image = None
            s1_flooded_extend_image = None
    else:
        print("\nSkipping SAR-based processing and flood detection as per user selection.")


    if detection_method in ["s2", "both"]:
        # --- Sentinel-2 Processing ---
        print("\n--- Sentinel-2 Data Processing ---")
        s2_start_date = event_date.advance(-s2_search_days, 'day')
        s2_end_date = event_date.advance(s2_search_days, 'day')
        
        try:
            s2_collection = data_ingestion.get_sentinel2_collection(AOI, s2_start_date, s2_end_date)
            s2_pre_event, s2_post_event = preprocessing.get_pre_and_post_s2_images(
                s2_collection, AOI, event_date, s2_search_days
            )
            ndwi_pre_event_mask = preprocessing.calculate_ndwi(s2_pre_event).gt(0).rename("ndwi_water_pre")
            ndwi_post_event_mask = preprocessing.calculate_ndwi(s2_post_event).gt(0).rename("ndwi_water_post")
            print("Sentinel-2 data prepared and NDWI calculated.")

            # -------------Detect flood extent using NDWI---------------
            s2_flood_extent_image = flood_detection.detect_flood_extent_s2_ndwi(ndwi_pre_event_mask, ndwi_post_event_mask, AOI)
            
            if s2_flood_extent_image: # Only refine if initial flood extent was calculated
                s2_flooded_extent_image = flood_detection.refine_flood_extent_with_topology(s2_flood_extent_image, AOI)
                s2_flooded_area_sqkm = flood_detection.calculate_flood_extension(s2_flooded_extent_image, AOI) # Updated call
                print(f"Calculated Sentinel-2 NDWI-based flooded area: {s2_flooded_area_sqkm:.2f} km²")
            else:
                print("Sentinel-2 NDWI-based flood extent not calculated due to inconsistent pixel counts or other issues.")

        except ValueError as e:
            print(f"Sentinel-2 processing skipped due to: {e}")
            s2_pre_event, s2_post_event = None, None
            ndwi_pre_event_mask, ndwi_post_event_mask = None, None
            s2_flood_extent_image = None
            s2_flooded_extent_image = None
        except Exception as e:
            print(f"Error during S2 flood extent detection or refinement: {e}")
            s2_flood_extent_image = None
            s2_flooded_extent_image = None
    else:
        print("\nSkipping Sentinel-2 processing and flood detection as per user selection.")


    # --- Print Water Area Estimates ---
    print("\nWater Area Estimates (in km²):")
    if detection_method in ["s2", "both"] and s2_flooded_extent_image: # Only print if S2 flood extent was calculated
        print(f"Flood Extent (Sentinel-2 NDWI): {s2_flooded_area_sqkm:.2f} km²")
    else:
        print("Sentinel-2 Flood Areas        : N/A (S2 processing skipped or failed)")

    if detection_method in ["sar", "both"] and s1_flooded_extend_image:
        print(f"Effective Flooded Area (SAR)  : {s1_flooded_area_sqkm:.2f} km²")
    else:
        print("SAR-based Flood Areas         : N/A (SAR processing skipped or failed)")


    # --- Visualization ---
    print("\n--- Generating Visualization ---")
    map_center = AOI.centroid().coordinates().getInfo()[::-1] # [lon, lat] -> [lat, lon]
    m = visualization.create_map(map_center)

    # Add Main AOI to the map
    m.addLayer(AOI, {'color': 'blue', 'fillColor': '00000000'}, 'Main AOI')
    # Add Otsu AOI to the map if it was provided
    if otsu_aoi_geometry:
        m.addLayer(otsu_aoi_geometry, {'color': 'green', 'fillColor': '00000000'}, 'Otsu AOI')

    if detection_method in ["sar", "both"] and sar_pre_event and sar_post_event:
        visualization.add_sar_layers(m, sar_pre_event, sar_post_event)
    
    if detection_method in ["s2", "both"] and ndwi_pre_event_mask and ndwi_post_event_mask:
        visualization.add_ndwi_layers(m, ndwi_pre_event_mask, ndwi_post_event_mask)
    
    # Add SAR-based flood extent layers
    if detection_method in ["sar", "both"] and s1_flooded_extend_image:
        visualization.add_effective_flood_extent_layer(m, s1_flooded_extend_image, zoom_to_layer=False) 

    # Add S2-based flood extent layer
    if detection_method in ["s2", "both"] and s2_flooded_extent_image:
        visualization.add_s2_flood_extent_layer(m, s2_flooded_extent_image, zoom_to_layer=True) # Zoom to S2 flood extent if available

    if flood_duration_image:
        visualization.add_flood_duration_layer(m, flood_duration_image)
    
    print("\nMap ready for display (if in a Jupyter environment) or for export.")


    # --- Export Results ---
    if export_results:
        print(f"\n--- Exporting Results to GEE Asset (Prefix: {asset_id_prefix}) ---")
        current_date_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        if detection_method in ["sar", "both"] and s1_flooded_extend_image: # Export effective SAR flood area
            export_description_effective_extent = f"Effective_Flood_Extent_SAR_{event_date_str.replace('-', '')}_{current_date_time}"
            utils.export_image_to_asset(s1_flooded_extend_image, export_description_effective_extent, asset_id_prefix, AOI)
        else:
            print("No effective SAR flood extent to export based on selection or availability.")

        if detection_method in ["s2", "both"] and s2_flooded_extent_image: # Export S2 NDWI flood area
            export_description_s2_extent = f"Flood_Extent_S2_NDWI_{event_date_str.replace('-', '')}_{current_date_time}"
            utils.export_image_to_asset(s2_flooded_extent_image, export_description_s2_extent, asset_id_prefix, AOI)
        else:
            print("No Sentinel-2 NDWI flood extent to export based on selection or availability.")
            
    else:
        print("\nSkipping export of results as 'export_results' is False.")

    print("\nFlood mapping process completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated flood mapping using Google Earth Engine.")
    parser.add_argument("--event_date", type=str, required=True,
                        help="Date of the flood event (YYYY-MM-DD).")
    parser.add_argument("--aoi_path", type=str,
                        help="Path to a GeoJSON file defining the Area of Interest. Optional.")
    parser.add_argument("--otsu_aoi_path", type=str,
                        help="Path to a GeoJSON file for Otsu threshold calculation. Optional. If not provided, flood_detection.py will use its internal default.")
    parser.add_argument("--sar_search_days", type=int, default=12,
                        help="Number of days before/after event date to search for Sentinel-1 images.")
    parser.add_argument("--s2_search_days", type=int, default=20,
                        help="Number of days before/after event date to search for Sentinel-2 images.")
    parser.add_argument("--export", action="store_true",
                        help="Export results (flood extent) to GEE Assets.")
    parser.add_argument("--asset_id_prefix", type=str, default="project/ee-fid/FloodMappingResults/",
                        help="Google Earth Engine Assets.")
    parser.add_argument("--detection_method", type=str, choices=['sar', 's2', 'both'], default='both',
                        help="Select flood detection method: 'sar' (Sentinel-1 only), 's2' (Sentinel-2 only), or 'both'.")


    args = parser.parse_args()

    main(
        event_date_str=args.event_date,
        aoi_geojson_path=args.aoi_path,
        otsu_aoi_path=args.otsu_aoi_path, # Pass the path, main will handle loading to ee.Geometry
        sar_search_days=args.sar_search_days,
        s2_search_days=args.s2_search_days,
        export_results=args.export,
        asset_id_prefix=args.asset_id_prefix,
        detection_method=args.detection_method
    )