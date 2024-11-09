import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Radio Station Coverage",
    page_icon="📻",
    layout="wide"
)

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'

# Load data
@st.cache_data
def load_data():
    station_loc_gdf = gpd.read_file(PROCESSED_DATA_DIR / 'station_loc.gpkg')  # adjust filename as needed
    station_buffers_gdf = gpd.read_file(PROCESSED_DATA_DIR / 'station_buffers.gpkg')  # if you saved the buffers
    return station_loc_gdf, station_buffers_gdf

# Main app
def main():
    station_loc_gdf, station_buffers_gdf = load_data()

    st.title("📻 LM Radio Station Coverage sample")
    st.write("The map below shows the coverage areas of radio stations in the region. The colored polygons represent the estimated coverage area for each station.")
    st.write("We estimated a buffer of 20km, 25 km, and 40km and 60 km range to get an idea of where the stations broadcast.")


    # Load data
    st.header("Station Locations")
    st.dataframe(station_loc_gdf)

    # Your  folium map code here
    m = folium.Map(location=[station_loc_gdf.geometry.y.mean(), station_loc_gdf.geometry.x.mean()], 
                zoom_start=10, 
                tiles='OpenStreetMap', 
                attr=''
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

    # Add each station to the legend with its color
    for idx, row in station_loc_gdf.iterrows():
        legend_html += f"""
        <p>
            <i class="fa fa-circle" style="color:{row['color']}"></i>
            {row['station_name']}
        </p>
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

    # Create a Feature Group for each radio station's buffers
    station_buffer_groups = {}
    for station in station_loc_gdf['station_name'].unique():
        station_buffer_groups[station] = folium.FeatureGroup(name=f'Ranges {station}')

    # Sort buffers from largest to smallest for proper layering
    station_buffers_gdf = station_buffers_gdf.sort_values('buffer_km', ascending=False)

    # Add buffers with different styles
    for idx, row in station_buffers_gdf.iterrows():
        station_name = row['station_name']
        
        # Define style based on buffer size
        if row['buffer_km'] == 20:
            style = {
                'fillOpacity': 0.4, 
                'dashArray': None, 
                'weight': 2
            }
        elif row['buffer_km'] == 25:
            style = {
                'fillOpacity': 0.3, 
                'dashArray': '5,5', 
                'weight': 2
            }
        elif row['buffer_km'] == 40:
            style = {
                'fillOpacity': 0.2, 
                'dashArray': '10,10', 
                'weight': 2
            }
        else:  # 60km
            style = {
                'fillOpacity': 0.1, 
                'dashArray': '2,8', 
                'weight': 2
            }

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

    # Add station points
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

    # Add all buffer groups to the map
    for group in station_buffer_groups.values():
        group.add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    m  
        
    # Display the map in Streamlit
    st_folium(m, width=1200, height=800)
    
    st.write("### Key Features: ")
    st.write("We see that Dwanwana FM and Dokolo FM broadcasting locations are very close to eachother and they overlap quite a bit")
    st.write("### blabla Features:")


if __name__ == "__main__":
    main()