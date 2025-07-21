# Flood Mapper Package

 [Quick Start Documentation](https://fadodo.github.io/event/flood_mapper_documentation/)

## Overview

The `flood_mapper` package is a Python-based tool designed for rapid and flexible mapping of flooded areas using Google Earth Engine (GEE). It leverages pre- and post-event satellite imagery from Sentinel-1 (Synthetic Aperture Radar - SAR) and Sentinel-2 (optical) to detect flood extents. The package offers users the flexibility to choose their preferred detection method and handles data ingestion, preprocessing, flood detection, and export of results to Google Earth Engine Assets.


## Features

* **Flexible Flood Detection:** Choose to perform flood detection using:

  * **Sentinel-1 SAR data only (`--detection_method sar`):** Ideal for all-weather, day/night conditions, crucial when optical imagery is obscured by clouds.

  * **Sentinel-2 optical data only (`--detection_method s2`):** Utilizes NDWI for water detection, effective in clear-sky conditions.

  * **Both Sentinel-1 and Sentinel-2 data (`--detection_method both` - default):** Provides comprehensive analysis by leveraging the strengths of both data types.

* **Automated Data Ingestion:** Seamlessly fetches Sentinel-1 GRD and Sentinel-2 (Surface Reflectance) imagery from Google Earth Engine.

* **Image Preprocessing:** Includes speckle smoothing for SAR images and NDWI calculation for Sentinel-2.

* **Otsu Thresholding:** Dynamically computes thresholds for water/flood detection. Offers an **optional specific GeoJSON for Otsu threshold computation (`--otsu_aoi_path`)** for improved accuracy in complex terrains or specific water bodies.

* **Topological Refinement:** Refines flood extents based on connected pixels and terrain slope to remove noise and spurious detections.

* **Area Calculation:** Quantifies the extent of detected flooded areas in square kilometers.

* **Export to GEE Assets:** Export processed flood extent maps and other results directly to your Google Earth Engine Assets for persistent storage and further analysis within the GEE platform.

* **Command-Line Interface:** Easy-to-use script for running flood mapping workflows.

## Installation

1. **Clone the repository:**

   ```
   git clone [https://github.com/fadodo/flood_mapper.git](https://github.com/fado/flood_mapper.git)
   cd flood_mapper
   
   ```

 

2. **Set up a virtual environment (recommended):**

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   
   ```

3. **Install dependencies:**

   ```
   pip install -e .
   
   ```

   This will install the package in editable mode and all its dependencies.

4. **Authenticate Google Earth Engine:**
   You need to authenticate your Earth Engine account. Follow the instructions provided by the `earthengine` library:

   ```
   earthengine authenticate
   
   ```

   Ensure you have access to the GEE project specified in the code (default is `ee-fid`).

## Usage

The main script for running flood mapping is `scripts/run_flood_mapping.py` or `scripts/run_flood_mapping.ipynb`

```
python scripts/run_flood_mapping.py --help

```

**Example Usage:**

To run flood detection using both SAR and Sentinel-2 data for a specific event date and AOI, and export the results to your GEE Assets:

```
python scripts/run_flood_mapping.py \
    --event_date 2025-06-02 \
    --aoi_path /path/to/your/aoi.geojson \
    --otsu_aoi /path/to/your/aoi.geojson \
    --export \
    --asset_id_prefix "users/your_username/my_flood_maps/" \
    --detection_method both

```

**Arguments:**

* `--event_date <YYYY-MM-DD>` (required): The date of the flood event.

* `--aoi_path <path/to/aoi.geojson>` (optional): Path to a GeoJSON file defining your Area of Interest. If not provided, a default AOI over Lomé, Togo, will be used.

* `--otsu_aoi_path <path/to/otsu_aoi.geojson>` (optional): Path to a GeoJSON file defining a specific region to compute the Otsu threshold. This can be a small, known water body within your AOI for more accurate thresholding. If not provided, a default small AOI over Lac Togo will be used for Otsu calculation.

* `--sar_search_days <int>` (default: 12): Number of days before and after the event date to search for Sentinel-1 images.

* `--s2_search_days <int>` (default: 20): Number of days before and after the event date to search for Sentinel-2 images.

* `--export` (flag): Include this flag to export results (flood extent) to your GEE Assets.

* `--asset_id_prefix <GEE_ASSET_PATH>` (default: `project/ee-fid/FloodMappingResults/`): The base path in your GEE Assets where the exported images will be stored. **Remember to change `project/ee-fid/` to your actual GEE project or `users/your_username/` path.**

* `--detection_method <sar|s2|both>` (default: `both`): Select the method for flood detection.

  * `sar`: Use only Sentinel-1 SAR data.

  * `s2`: Use only Sentinel-2 optical data.

  * `both`: Use both Sentinel-1 and Sentinel-2 data (default).

## Running Tests

To run the unit tests for the package, navigate to the root directory and execute pytest:

```
pytest

```

Ensure your GEE authentication is set up correctly as tests interact with the GEE API.

## Accuracy Considerations

The accuracy of the flooded area calculation can be influenced by several factors inherent to the satellite data and processing methods:

- **Sentinel-2 (Optical) Data**:
      - **Cloud Cover**: The primary limitation for Sentinel-2 is the presence of clouds. Clouds and cloud shadows can obscure the ground, leading to underestimation of flooded areas or false positives if shadows are misidentified as water. Clear-sky images are crucial for reliable detection.

- **Sentinel-1 (SAR) Data**:
        - **Otsu Threshold Determination**: While SAR can penetrate clouds, the accuracy of flood detection heavily relies on the precise determination of the Otsu threshold. This threshold differentiates water from land based on backscatter values. Factors like vegetation, urban areas, and varying water surface conditions can affect backscatter, making a universally optimal threshold challenging and potentially leading to misclassifications.

## Verification Status
The core flood detection logic, including SAR-based (Otsu thresholding) and Sentinel-2 NDWI-based methods, has been refined to ensure robust calculations even when pre- and post-event image pixel counts differ. This is achieved by performing operations on a common mask of available pixels. The `calculate_flood_extension` function now accurately computes the flooded area using the refined flood extent. The visualization now correctly displays both the main Area of Interest (AOI) and the specific Otsu AOI on the map, aiding in verification and understanding of the analysis extent.


## Contributing

Contributions are welcome! If you have suggestions for improvements, bug reports, or want to add new features, please open an issue or submit a pull request.

## License

This project is open-source and available under the [MIT License](https://www.google.com/search?q=LICENSE).
