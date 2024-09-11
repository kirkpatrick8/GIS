import streamlit as st
import ezdxf
from ezdxf.addons.geo import GeoProxy
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
import tempfile
import os
import zipfile

def convert_to_shp(input_file):
    # Create a temporary directory to store the output files
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Try to read the input file (DWG or DXF)
            doc = ezdxf.readfile(input_file)
            msp = doc.modelspace()

            # Initialize dictionary to store geometries for each layer
            layers = {}

            # Iterate through entities in the file
            for entity in msp:
                layer = entity.dxf.layer
                if layer not in layers:
                    layers[layer] = []

                # Convert entity to geometry
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
                    gdf.to_file(output_file)

            # Create a zip file containing all the shapefiles
            zip_filename = os.path.join(temp_dir, "output_shapefiles.zip")
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(('.shp', '.shx', '.dbf', '.prj')):
                            zipf.write(os.path.join(root, file), file)

            return zip_filename
        except ezdxf.DXFStructureError:
            st.error("Invalid or unsupported DWG/DXF file. Please ensure the file is not corrupted and is in a supported format.")
            return None

st.title("DWG/DXF to SHP Converter")

st.write("This app converts a DWG or DXF file to multiple SHP files, one for each layer in the input file.")

uploaded_file = st.file_uploader("Choose a DWG or DXF file", type=["dwg", "dxf"])

if uploaded_file is not None:
    st.write("File uploaded successfully!")
    
    if st.button("Convert to SHP"):
        with st.spinner("Converting..."):
            # Save the uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            # Convert the file
            try:
                zip_file = convert_to_shp(tmp_file_path)
                
                if zip_file:
                    # Offer the zip file for download
                    with open(zip_file, "rb") as file:
                        btn = st.download_button(
                            label="Download SHP files",
                            data=file,
                            file_name="output_shapefiles.zip",
                            mime="application/zip"
                        )
                    st.success("Conversion completed successfully!")
                else:
                    st.error("Conversion failed. Please try uploading a DXF file instead of DWG if the problem persists.")
            except Exception as e:
                st.error(f"An error occurred during conversion: {str(e)}")
            finally:
                # Clean up the temporary file
                os.unlink(tmp_file_path)
else:
    st.write("Please upload a DWG or DXF file to begin.")
