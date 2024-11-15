import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pathlib import Path

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
@st.cache_data
def load_data():
    station_loc_gdf = gpd.read_file(PROCESSED_DATA_DIR / 'station_loc.gpkg')
    station_buffers_gdf = gpd.read_file(PROCESSED_DATA_DIR / 'station_buffers.gpkg')
    sampled_clusters_gdf = gpd.read_file(PROCESSED_DATA_DIR / 'sampled_clusters.gpkg')
    return station_loc_gdf, station_buffers_gdf, sampled_clusters_gdf

def create_map(station_loc_gdf, station_buffers_gdf, sampled_clusters_gdf):
    # Create base map
    m = folium.Map(
        location=[station_loc_gdf.geometry.y.mean(), station_loc_gdf.geometry.x.mean()],
        zoom_start=10,
        tiles='OpenStreetMap'
    )

    # Create legend
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; height: auto;
                background-color: white;
                border: 2px solid grey;
                z-index: 1000;
                padding: 10px;
                font-size: 14px;
                ">
    <p><strong>Radio Stations</strong></p>
    """

    # Add stations to legend
    for idx, row in station_loc_gdf.iterrows():
        legend_html += f"""
        <p>
            <i class="fa fa-circle" style="color:{row['color']}"></i>
            {row['station_name']}
        </p>
        """

    # Add cluster types to legend
    legend_html += """
    <p><strong>Sampled Clusters</strong></p>
    <p>█ Solid fill - Main clusters</p>
    <p>▒ Dashed outline - Replacement clusters</p>
    """

    legend_html += "<p><strong>Assumed Coverage Ranges</strong></p>"
    legend_html += """
    <p>― 20km (solid line, highest opacity)</p>
    <p>-- 25km (dashed line)</p>
    <p>― ― 40km (long dashes)</p>
    <p>... 60km (dotted line, lowest opacity)</p>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    # Create feature groups
    station_buffer_groups = {}
    cluster_groups = {}
    for station in station_loc_gdf['station_name'].unique():
        station_buffer_groups[station] = folium.FeatureGroup(name=f'Ranges {station}')
        cluster_groups[f'{station}_main'] = folium.FeatureGroup(name=f'Main Clusters - {station}')
        cluster_groups[f'{station}_replacement'] = folium.FeatureGroup(name=f'Replacement Clusters - {station}')

    # Sort and add buffers
    station_buffers_gdf = station_buffers_gdf.sort_values('buffer_km', ascending=False)
    for idx, row in station_buffers_gdf.iterrows():
        station_name = row['station_name']
        
        # Define style based on buffer size
        style = {
            20: {'fillOpacity': 0.4, 'dashArray': None, 'weight': 2},
            25: {'fillOpacity': 0.3, 'dashArray': '5,5', 'weight': 2},
            40: {'fillOpacity': 0.2, 'dashArray': '10,10', 'weight': 2},
            60: {'fillOpacity': 0.1, 'dashArray': '2,8', 'weight': 2}
        }[row['buffer_km']]

        folium.GeoJson(
            row.geometry,
            style_function=lambda x, color=row['original_color'], style=style: {
                'fillColor': color,
                'color': color,
                'fillOpacity': style['fillOpacity'],
                'dashArray': style['dashArray'],
                'weight': style['weight']
            },
            highlight_function=lambda x: {
                'weight': 3,
                'fillOpacity': style['fillOpacity'] + 0.2
            },
            tooltip=f"{station_name} - {row['buffer_km']}km range",
            popup=folium.Popup(
                f"""
                <div style='width: 200px'>
                    <b>{station_name}</b><br>
                    Coverage Range: {row['buffer_km']} km<br>
                </div>
                """,
                max_width=300
            )
        ).add_to(station_buffer_groups[station_name])

    # Add clusters
    sampled_clusters_gdf = sampled_clusters_gdf.to_crs(epsg=4326)
    for station in sampled_clusters_gdf['station_name'].unique():
        station_color = station_loc_gdf[station_loc_gdf['station_name'] == station]['color'].iloc[0]
        station_clusters = sampled_clusters_gdf[sampled_clusters_gdf['station_name'] == station]
        
        # Add main clusters
        main_clusters = station_clusters[station_clusters['cluster_type'] == 'main']
        folium.GeoJson(
            main_clusters,
            style_function=lambda x, color=station_color: {
                'fillColor': color,
                'color': color,
                'weight': 2,
                'fillOpacity': 0.7
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['station_name', 'cluster_type', 'population_count', 'centroid_lon_lat', 'grid_id' ],
                aliases=['Station', 'Type', 'Population', 'location of cluster centroid (Coordinate)', 'cluster identifier (grid_id)'],
                style="background-color: white; color: black; font-family: arial; font-size: 12px; padding: 10px;"
            )
        ).add_to(cluster_groups[f'{station}_main'])
        
        # Add replacement clusters
        replacement_clusters = station_clusters[station_clusters['cluster_type'] == 'replacement']
        folium.GeoJson(
            replacement_clusters,
            style_function=lambda x, color=station_color: {
                'fillColor': color,
                'color': color,
                'weight': 1,
                'fillOpacity': 0.3,
                'dashArray': '5, 5'
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['station_name', 'cluster_type', 'population_count'],
                aliases=['Station', 'Type', 'Population'],
                style="background-color: white; color: black; font-family: arial; font-size: 12px; padding: 10px;"
            )
        ).add_to(cluster_groups[f'{station}_replacement'])

    # Add station markers
    for idx, row in station_loc_gdf.iterrows():
        folium.Marker(
            location=[row.geometry.y, row.geometry.x],
            popup=row['station_name'],
            tooltip=f"Click to see {row['station_name']} location",
            icon=folium.Icon(
                color='white',  # This will be the background color of the pin
                icon='info',    # Using 'info' instead of 'radio'
                icon_color=row['color'],  # This will color the icon itself
                prefix='fa'     # Using Font Awesome icons
            )
        ).add_to(m)


    # Add all groups to map
    for group in station_buffer_groups.values():
        group.add_to(m)
    for group in cluster_groups.values():
        group.add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)
    
    return m

def main():
    st.title("📻 Radio Station Coverage sampling LM (test)")
    
    try:
        # Load data
        station_loc_gdf, station_buffers_gdf, sampled_clusters_gdf = load_data()
        
        # Add description
        st.write("This map shows the assumed coverage areas and sampling clusters for radio stations in the region.")
        st.write("Ranges show assumed coverage areas, for the sampling I've taken the 25km radios around the broadcast location as we're sure that that has good coverage")
                        # Add analysis
        st.header("Sampling")
        st.write("### Key Observations:")
        st.write("- The map shows both main and replacement clusters (dashed outline) clusters for each station")
        st.write("- Dwanwana FM and Dokolo FM broadcasting locations show significant overlap in their coverage areas")
        st.write("- Sampling done by overlaying a fishnet grid (1km by 1km cells) and sampled proportional to population size in each cell (based on overlaying worldpop data/imagery estimates), this means that sampled areas should by relatively densely populated.")
        st.write("- Assuming: 35 clusters per radio station, 12 interviews per cluster.")

        
        # Display station data
        with st.expander("View Station Data"):
            display_df = station_loc_gdf.drop(columns=['geometry'])
            st.dataframe(display_df)
        


        # Create and display map
        m = create_map(station_loc_gdf, station_buffers_gdf, sampled_clusters_gdf)
        st_folium(m, width=1200, height=800)
    
        with st.expander("View data on sampled clusters"):
            display_df_2 = sampled_clusters_gdf.copy().drop(columns=['count', 'sum', 'nodata', 'valid_pixels', 'nodata_pixels', 'total_pixels', 'prop_nodata'])
            display_df_2['geometry'] = display_df_2['geometry'].astype(str)
            st.dataframe(display_df_2)

    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.write("Please ensure all required data files are present in the processed data directory:")
        st.write("- station_loc.gpkg")
        st.write("- station_buffers.gpkg")
        st.write("- sampled_clusters.gpkg")

if __name__ == "__main__":
    main()
