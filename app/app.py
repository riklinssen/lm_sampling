import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Radio Station Coverage Analysis",
    page_icon="📻",
    layout="wide"
)

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
                fields=['station_name', 'cluster_type', 'population_count'],
                aliases=['Station', 'Type', 'Population'],
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
                color='white',
                icon_color=row['color'],
                icon='radio',
                prefix='fa'
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
    st.title("📻 Radio Station Coverage Analysis")
    
    try:
        # Load data
        station_loc_gdf, station_buffers_gdf, sampled_clusters_gdf = load_data()
        
        # Add description
        st.write("This map shows the coverage areas and sampling clusters for radio stations in the region.")
        st.write("The colored areas represent different coverage ranges (20km, 25km, 40km, and 60km) and sampling clusters.")
        
        # Display station data
        with st.expander("View Station Data"):
            st.dataframe(station_loc_gdf)
        
        # Create and display map
        m = create_map(station_loc_gdf, station_buffers_gdf, sampled_clusters_gdf)
        st_folium(m, width=1200, height=800)
        
        # Add analysis
        st.header("Coverage Analysis")
        st.write("### Key Observations:")
        st.write("- The map shows both coverage ranges and sampling clusters for each station")
        st.write("- Main clusters (solid fill) represent primary coverage areas")
        st.write("- Replacement clusters (dashed outline) show alternative coverage zones")
        st.write("- Dwanwana FM and Dokolo FM broadcasting locations show significant overlap in their coverage areas")
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.write("Please ensure all required data files are present in the processed data directory:")
        st.write("- station_loc.gpkg")
        st.write("- station_buffers.gpkg")
        st.write("- sampled_clusters.gpkg")

if __name__ == "__main__":
    main()
