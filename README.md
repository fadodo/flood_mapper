# Flood Mapper

An automated tool for flood mapping using Google Earth Engine (GEE) with Sentinel-1 SAR and Sentinel-2 optical imagery. This package aims to streamline the process of detecting flood extent and duration, and can integrate precipitation forecasts.

## ✨ Features

-   **Automated Data Ingestion**: Fetches Sentinel-1 SAR and Sentinel-2 optical imagery from GEE.
-   **Advanced Preprocessing**: Includes speckle filtering for SAR imagery and NDWI calculation for Sentinel-2.
-   **Dynamic Flood Detection**: Utilizes Otsu's method for automatic thresholding to detect flood extent.
-   **Flood Duration (Conceptual)**: Placeholder for future time-series based flood duration analysis.
-   **Precipitation Forecasting Integration**: Fetches and analyzes CPC Global Unified Precipitation Forecasts.
-   **Intuitive Visualization**: Generates interactive maps using `geemap` to visualize results.
-   **Export Capabilities**: Exports flood maps (extent, duration) to Google Drive.
-   **Command-Line Interface (CLI)**: Easily run flood mapping tasks from your terminal.
-   **Modular and Extensible**: Designed as a Python package for easy integration and expansion.

## 🚀 Installation

1.  **Clone the repository:**

    ```bash
    git clone [https://github.com/fadodo/flood_mapper.git](https://github.com/fadodo/flood_mapper.git)
    cd flood_mapper
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the package and its dependencies:**

    ```bash
    pip install -e .
    ```
    The `-e .` installs the package in "editable" mode, meaning changes to the source code will be reflected without reinstalling.

4.  **Authenticate Google Earth Engine:**

    Before running, you need to authenticate your Earth Engine account. This is a one-time setup.

    ```bash
    earthengine authenticate
    ```
    Follow the prompts to complete the authentication process. You might also need to set up a GEE project.

## 💡 Usage

You can run the flood mapping process using the provided command-line interface.

### Command Line Interface (CLI)

```bash
run-flood-mapping --event_date YYYY-MM-DD [OPTIONS]