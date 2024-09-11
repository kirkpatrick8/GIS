import streamlit as st
import geopandas as gpd
import ezdxf
from ezdxf.addons.geo import GeoProxy
from shapely.geometry import Point, LineString, Polygon
import pandas as pd
import os
import zipfile
import tempfile

def convert_dwg_to_shp(dwg_file):
    # Create a temporary directory to store the output files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Read the DWG file
        doc = ezdxf.readfile(dwg_file)
        msp = doc.modelspace()

        # Initialize dictionary to store geometries for each layer
        layers = {}

        # Iterate through entities in the DWG file
        for entity in msp:
            layer = entity.dxf.layer
            if layer not in layers:
                layers[layer] = []

            # Convert DXF entity to geometry
            try:
                geo = GeoProxy.from_dxf_entity(entity)
                if isinstance(geo, (Point, LineString, Polygon)):
                    layers[layer].append(geo)
            except Exception as e:
                st.warning(f"Skipping unsupported entity: {str(e)}")

        # Convert layers to GeoDataFrames and save as shapefiles
        for layer, geometries in layers.items():
            if geometries:
                gdf = gpd.GeoDataFrame(geometry=geometries)
                gdf['Layer'] = layer
                output_file = os.path.join(temp_dir, f"{layer}.shp")
                gdf.to_file(driver='ESRI Shapefile', filename=output_file)

        # Create a zip file containing all the shapefiles
        zip_filename = os.path.join(temp_dir, "output_shapefiles.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != "output_shapefiles.zip":
                        zipf.write(os.path.join(root, file), file)

        return zip_filename

st.title("DWG to SHP Converter")

st.write("This app converts a DWG file to multiple SHP files, one for each layer in the DWG file.")

uploaded_file = st.file_uploader("Choose a DWG file", type="dwg")

if uploaded_file is not None:
    st.write("File uploaded successfully!")
    
    if st.button("Convert to SHP"):
        with st.spinner("Converting..."):
            # Save the uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dwg") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Convert the file
            try:
                zip_file = convert_dwg_to_shp(tmp_file_path)
                
                # Offer the zip file for download
                with open(zip_file, "rb") as file:
                    btn = st.download_button(
                        label="Download SHP files",
                        data=file,
                        file_name="output_shapefiles.zip",
                        mime="application/zip"
                    )
                st.success("Conversion completed successfully!")
            except Exception as e:
                st.error(f"An error occurred during conversion: {str(e)}")
            finally:
                # Clean up the temporary file
                os.unlink(tmp_file_path)
else:
    st.write("Please upload a DWG file to begin.")
