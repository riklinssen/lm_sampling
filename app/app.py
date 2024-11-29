import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pathlib import Path
import pandas as pd

# Page config
st.set_page_config(
    page_title="Radio Station Coverage Sampling (test)",
    page_icon="📻",
    layout="wide")
st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    """, unsafe_allow_html=True)


# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'

# Load data
def load_data():
    """Load all required geodata files"""
    try:
        # Load station-related data
        station_loc_gdf = gpd.read_file(PROCESSED_DATA_DIR / 'station_loc.gpkg')
        station_buffers_gdf = gpd.read_file(PROCESSED_DATA_DIR / 'station_buffers.gpkg')
        
        # Load enumeration area layers
        enum_layers = {
            'grid_cells': gpd.read_file(PROCESSED_DATA_DIR / 'enumeration_area_data.gpkg', layer='grid_cells'),
            'centroids': gpd.read_file(PROCESSED_DATA_DIR / 'enumeration_area_data.gpkg', layer='centroids'),
            'road_points': gpd.read_file(PROCESSED_DATA_DIR / 'enumeration_area_data.gpkg', layer='road_points'),
            'village_points': gpd.read_file(PROCESSED_DATA_DIR / 'enumeration_area_data.gpkg', layer='village_points')
        }
        
        # Filter buffers for 25km only
        station_buffers_gdf = station_buffers_gdf[station_buffers_gdf['buffer_km'] == 25]
        
        # Join grid_cells data to centroids
        enum_layers['centroids'] = enum_layers['centroids'].merge(
            enum_layers['grid_cells'][['station_name', 'grid_id', 'nearest_road_maps_link']], 
            on=['station_name', 'grid_id'], 
            how='left'
        )
        
        return station_loc_gdf, station_buffers_gdf, enum_layers
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None, None


def create_station_map(station_names: list, 
                      station_loc_gdf: gpd.GeoDataFrame,
                      enum_layers: dict,
                      zoom_start: int = 10):
    # Filter data for specified stations
    station_locs = station_loc_gdf[station_loc_gdf['station_name'].isin(station_names)]
    
    # Create base map
    m = folium.Map(
        location=[station_locs.geometry.y.mean(), station_locs.geometry.x.mean()],
        zoom_start=zoom_start,
        tiles=None  # Start with no base map
    )
    
    # Add different tile layers
    folium.TileLayer(
        tiles='openstreetmap',
        name='OpenStreetMap'
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False
    ).add_to(m)

    # Create legend
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; height: auto;
                background-color: white;
                border: 2px solid grey;
                z-index: 1000;
                padding: 10px;
                font-size: 14px;">
    <p><strong>Radio Stations</strong></p>
    """
    
    for idx, row in station_locs.iterrows():
        legend_html += f"""
        <p><i class="fa fa-circle" style="color:{row['color']}"></i> {row['station_name']}</p>
        """
    
    legend_html += """
    <p><strong>Grid Cells</strong></p>
    <p>● Solid - Main<br>● Dashed - Replacement</p>
    """
    
    if not enum_layers['village_points'].empty and not enum_layers['village_points'].geometry.isna().all():
        legend_html += "<p>● Purple - Nearest Village</p>"
    
    legend_html += """
    </div>
    """
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Create feature groups for each station
    station_groups = {}
    for station in station_names:
        station_groups[station] = folium.FeatureGroup(name=f'{station}')
        
        # Get station color
        station_color = station_locs[station_locs['station_name'] == station]['color'].iloc[0]
        
        # Add grid cells (use different styles for main and replacement)
        station_grids = enum_layers['grid_cells'][enum_layers['grid_cells']['station_name'] == station]
        grid_layer = folium.GeoJson(
            station_grids,
            name=f"{station}_grids",
            style_function=lambda feature: {
                'fillColor': None,
                'color': station_color,
                'weight': 2,
                'fillOpacity': 0,
                'dashArray': '5,5' if feature['properties']['cluster_type'] == 'replacement' else None
            }
        )
        grid_layer.add_to(station_groups[station])
        
        # Add centroid markers
        station_centroids = enum_layers['centroids'][enum_layers['centroids']['station_name'] == station]
        for idx, row in station_centroids.iterrows():
            if row.geometry is not None:
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=4,
                    color=station_color,
                    fill=True,
                    weight=2,
                    tooltip=folium.Tooltip(f"""
                        Grid ID: {row.grid_id}
                        Station: {row.station_name}
                        Cluster Type: {row['cluster_type']}
                        Nearest Road: <a href='{row.nearest_road_maps_link}' target='_blank'>Link</a>
                        Centroid: <a href='{row.centroid_maps_link}' target='_blank'>Link</a>
                    """),
                    popup=folium.Popup(
                        f"""<div style='width: 300px'>
                        <b style="color:{station_color}">Grid ID:</b> {row.grid_id}<br>
                        <b style="color:{station_color}">Station:</b> {row.station_name}<br>
                        <b style="color:{station_color}">Cluster Type:</b> {row['cluster_type']}<br>
                        <a href='{row.nearest_road_maps_link}' target='_blank'>Nearest Road</a><br>
                        <a href='{row.centroid_maps_link}' target='_blank'>Centroid</a>
                        </div>""",
                        max_width=300
                    )
                ).add_to(station_groups[station])
        
        # Add village point markers
        station_villages = enum_layers['village_points'][enum_layers['village_points']['station_name'] == station]
        for idx, row in station_villages.iterrows():
            if row.geometry is not None and not pd.isna(row.geometry):
                try:
                    folium.CircleMarker(
                        location=[row.geometry.y, row.geometry.x],
                        radius=4,
                        color='purple',
                        fill=True,
                        weight=2,
                        tooltip=folium.Tooltip(f"""
                            Nearest address found in grid cell:
                            {row.nearest_address_full}
                            Village: {row.village}
                            District: {row.district}
                            Region: {row.region}
                        """),
                        popup=folium.Popup(
                            f"""<div style='width: 300px'>
                            <b>Grid ID:</b> {row.grid_id}<br>
                            <b>Nearest Address:</b> {row.nearest_address_full}<br>
                            <b>Village:</b> {row.village}<br>
                            <b>District:</b> {row.district}<br>
                            <b>Region:</b> {row.region}
                            </div>""",
                            max_width=300
                        )
                    ).add_to(station_groups[station])
                except:
                    continue
        
        # Add station marker
        station_loc = station_locs[station_locs['station_name'] == station].iloc[0]
        folium.Marker(
            location=[station_loc.geometry.y, station_loc.geometry.x],
            popup=f"<span style='color:{station_color};'>{station_loc['station_name']}</span>",
            tooltip=folium.Tooltip(f"Click to see {station_loc['station_name']} location"),
            icon=folium.Icon(
                color='white',
                icon_color=station_color,
                icon='radio',
                prefix='fa'
            )
        ).add_to(station_groups[station])
    
    # Add all groups to the map
    for group in station_groups.values():
        group.add_to(m)
    
    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Save the map to an HTML file
    m.save('radio_station_map.html')

    return m

def main():
    st.title("📻 Radio Station Coverage sampling LM (test)")
    
    try:
        # Load data
        station_loc_gdf, station_buffers_gdf, enum_layers = load_data()
        
        if station_loc_gdf is not None:
            # Add description
            st.write("This map shows the assumed coverage areas and sampling clusters for radio stations in the region.")
            st.write("Ranges show assumed coverage areas, for the sampling I've taken the 25km radius around the broadcast location as we're sure that that has good coverage")
            
            # Add analysis
            st.header("Sampling")
            st.write("### Key Observations:")
            st.write("- The map shows both main and replacement clusters (dashed outline) clusters for each station")
            st.write("- Dwanwana FM and Dokolo FM broadcasting locations show significant overlap in their coverage areas")
            st.write("- Sampling done by overlaying a fishnet grid (1km by 1km cells) and sampled proportional to population size in each cell")
            st.write("- Assuming: 35 clusters per radio station, 12 interviews per cluster.")
            
            # Display station data
            with st.expander("View Station Data"):
                display_df = station_loc_gdf.drop(columns=['geometry'])
                st.dataframe(display_df)
            
            # Station selection
            available_stations = station_loc_gdf['station_name'].unique().tolist()
            selected_stations = st.multiselect(
                "Select Radio Stations to Display",
                options=available_stations,
                default=['Aisa FM', 'Dwanwana FM', 'Dokolo FM']
            )
            
            if selected_stations:
                # Create and display map
                m = create_station_map(
                    selected_stations,
                    station_loc_gdf,
                    enum_layers
                )
                st_folium(m, width=1200, height=800)
            
            # Display cluster data
            with st.expander("View data on sampled clusters"):
                display_df_2 = enum_layers['grid_cells'].copy()
                # Remove unnecessary columns if needed
                cols_to_drop = ['geometry']  # Add any other columns you want to drop
                display_df_2 = display_df_2.drop(columns=cols_to_drop)
                st.dataframe(display_df_2)
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.write("Please ensure all required data files are present in the processed data directory:")
        st.write("- station_loc.gpkg")
        st.write("- station_buffers.gpkg")
        st.write("- enumeration_area_data.gpkg with all required layers")

if __name__ == "__main__":
    main()
