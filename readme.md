# Radio Station Coverage Analysis and Sampling

## Project Overview
This project provides tools for analyzing radio station coverage areas and generating sampling frames for audience research. It includes functionality for:
- Creating radio station coverage buffers
- Generating sampling grids
- Population-weighted sampling
- Finding nearest roads and addresses for field teams
- Visualizing coverage areas and sampling points

## Data & maps of gridded areas
See: https://lmselectiontest.streamlit.app/

## Project Structure
```
├── app/               # Streamlit web application
├── data/             # Data directory
│   ├── processed/    # Processed data files
│   ├── raw/         # Original source data
│   └── temp/        # Temporary files
├── notebooks/        # Jupyter notebooks for analysis
└── tests/           # Test directory
```

## Data Processing Pipeline
The analysis is performed through a series of Jupyter notebooks:
1. `1_radio_station_buffers.ipynb`: Generate coverage area buffers for radio stations
2. `2_generate_grids.ipynb`: Create sampling grid cells
3. `3_add_population_data.ipynb`: Add population data to grid cells
4. `4_generate_sampling_frame.ipynb`: Create sampling frame
5. `5_sample_grid_cells.ipynb`: Sample grid cells based on population weights
6. `6_merge_geo_sampled_clusters.ipynb`: Merge geographic data with sampled clusters
7. `7_find_nearest_road.ipynb`: Find nearest road points for field teams
8. `8_generate_enumeration_area_maps.ipynb`: Generate maps for enumeration areas

## Key Data Files
- `station_loc.gpkg`: Radio station locations
- `station_buffers.gpkg`: Coverage area buffers
- `enumeration_area_data.gpkg`: Grid cells and sampling points
- `sampling_clusters_full_data.csv`: Final sampling data with all metadata

## Interactive Visualization
The project includes a Streamlit application (`app/app.py`) for interactive visualization of:
- Radio station locations
- Coverage areas
- Sampling clusters
- Road access points
- Administrative boundaries

## Setup and Installation
1. Clone this repository
2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
3. Install requirements:
```bash
pip install -r requirements.txt
```

## Usage
### Data Processing
Run the notebooks in sequence (1-8) to process the data and generate sampling frames.

### Visualization App
Start the Streamlit app:
```bash
cd app
streamlit run app.py
```

## Environment Variables
Required environment variables (create `.env` file):
```
# Add any required environment variables here
```
