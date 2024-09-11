import streamlit as st
import ezdxf
from ezdxf.addons.geo import GeoProxy
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import tempfile
import os
import zipfile
import io

def convert_dwg_to_gdf(dwg_file):
    doc = ezdxf.readfile(dwg_file)
    msp = doc.modelspace()
    
    points = []
    lines = []
    polygons = []
    
    for entity in msp:
        if entity.dxftype() == 'POINT':
            points.append(Point(entity.dxf.location[:2]))
        elif entity.dxftype() == 'LINE':
            lines.append(LineString([entity.dxf.start[:2], entity.dxf.end[:2]]))
        elif entity.dxftype() == 'LWPOLYLINE':
            with entity.points() as point_gen:
                vertices = list(point_gen)
            if len(vertices) >= 3 and vertices[0] == vertices[-1]:
                polygons.append(Polygon(vertices))
            else:
                lines.append(LineString(vertices))
    
    gdf_points = gpd.GeoDataFrame(geometry=points)
    gdf_lines = gpd.GeoDataFrame(geometry=lines)
    gdf_polygons = gpd.GeoDataFrame(geometry=polygons)
    
    return gdf_points, gdf_lines, gdf_polygons

def create_zip_buffer(gdfs):
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, gdf in enumerate(gdfs):
            if not gdf.empty:
                gdf.to_file(os.path.join(tmpdir, f"layer_{i}.shp"))
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    zipf.write(os.path.join(root, file), file)
    
    zip_buffer.seek(0)
    return zip_buffer

st.title('DWG to Shapefile Converter')

uploaded_file = st.file_uploader("Choose a DWG file", type=['dwg'])

if uploaded_file is not None:
    try:
        gdf_points, gdf_lines, gdf_polygons = convert_dwg_to_gdf(uploaded_file)
        
        zip_buffer = create_zip_buffer([gdf_points, gdf_lines, gdf_polygons])
        
        st.download_button(
            label="Download Shapefiles",
            data=zip_buffer,
            file_name="shapefiles.zip",
            mime="application/zip"
        )
        
        st.success("Conversion successful! Click the button above to download your shapefiles.")
        
        # Display preview of the data
        st.subheader("Data Preview")
        st.write("Points:")
        st.write(gdf_points.head())
        st.write("Lines:")
        st.write(gdf_lines.head())
        st.write("Polygons:")
        st.write(gdf_polygons.head())
        
    except Exception as e:
        st.error(f"An error occurred during conversion: {str(e)}")

st.write("Note: This app supports basic DWG elements (points, lines, and polylines). Complex entities may not be fully supported.")
