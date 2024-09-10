import streamlit as st
import pandas as pd
import geopandas as gpd
import ezdxf
from shapely.geometry import Point, LineString, Polygon
import tempfile
import os
import zipfile

def process_csv(file, crs):
    df = pd.read_csv(file)
    if 'latitude' in df.columns and 'longitude' in df.columns:
        geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    elif 'x' in df.columns and 'y' in df.columns:
        geometry = [Point(xy) for xy in zip(df['x'], df['y'])]
    else:
        st.error("CSV must contain 'latitude' and 'longitude' or 'x' and 'y' columns.")
        return None
    
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
    return gdf

def process_dxf(file, crs):
    doc = ezdxf.readfile(file)
    msp = doc.modelspace()

    points = []
    lines = []
    polygons = []

    for entity in msp:
        if entity.dxftype() == 'POINT':
            points.append(Point(entity.dxf.location[:2]))
        elif entity.dxftype() == 'LINE':
            lines.append(LineString([entity.dxf.start[:2], entity.dxf.end[:2]]))
        elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
            polygons.append(Polygon(entity.get_points()))

    gdf_points = gpd.GeoDataFrame(geometry=points, crs=crs) if points else None
    gdf_lines = gpd.GeoDataFrame(geometry=lines, crs=crs) if lines else None
    gdf_polygons = gpd.GeoDataFrame(geometry=polygons, crs=crs) if polygons else None

    gdfs = [gdf for gdf in [gdf_points, gdf_lines, gdf_polygons] if gdf is not None]
    if gdfs:
        return pd.concat(gdfs, ignore_index=True)
    else:
        st.error("No valid geometries found in the DXF file.")
        return None

def save_and_zip_shapefile(gdf, output_filename):
    with tempfile.TemporaryDirectory() as tmpdir:
        gdf.to_file(os.path.join(tmpdir, output_filename))
        zipf = zipfile.ZipFile(f"{output_filename}.zip", 'w', zipfile.ZIP_DEFLATED)
        for root, _, files in os.walk(tmpdir):
            for file in files:
                zipf.write(os.path.join(root, file), file)
        zipf.close()
    return f"{output_filename}.zip"

st.title('File to Shapefile Converter')

file = st.file_uploader("Choose a CSV or DXF file", type=["csv", "dxf"])
crs = st.text_input("Enter the coordinate system (e.g., EPSG:4326)", "EPSG:4326")

if file is not None:
    file_extension = os.path.splitext(file.name)[1].lower()
    
    if file_extension == '.csv':
        gdf = process_csv(file, crs)
    elif file_extension == '.dxf':
        gdf = process_dxf(file, crs)
    else:
        st.error("Unsupported file format. Please use CSV or DXF files.")
        gdf = None

    if gdf is not None:
        st.write("Data preview:")
        st.write(gdf.head())

        output_filename = st.text_input("Enter output filename (without extension)", "output")
        if st.button('Convert to Shapefile'):
            zip_filename = save_and_zip_shapefile(gdf, output_filename)
            
            with open(zip_filename, "rb") as fp:
                btn = st.download_button(
                    label="Download Shapefile",
                    data=fp,
                    file_name=zip_filename,
                    mime="application/zip"
                )
            
            st.success(f"Shapefile created and zipped: {zip_filename}")
else:
    st.write("Please upload a CSV or DXF file to begin.")
