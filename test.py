import streamlit as st
import geopandas as gpd
from osgeo import ogr
import os
import zipfile
import tempfile

def convert_dwg_to_shp(dwg_file):
    # Create a temporary directory to store the output files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Open the DWG file
        driver = ogr.GetDriverByName("DWG")
        data_source = driver.Open(dwg_file, 0)
        
        if data_source is None:
            raise Exception("Could not open the DWG file. Please ensure it's a valid DWG file.")

        # Get the number of layers in the DWG file
        layer_count = data_source.GetLayerCount()

        for i in range(layer_count):
            layer = data_source.GetLayer(i)
            layer_name = layer.GetName()
            
            # Create a new shapefile
            output_file = os.path.join(temp_dir, f"{layer_name}.shp")
            out_driver = ogr.GetDriverByName("ESRI Shapefile")
            out_ds = out_driver.CreateDataSource(output_file)
            out_layer = out_ds.CreateLayer(layer_name, layer.GetSpatialRef(), layer.GetGeomType())

            # Copy the fields from the input layer to the output layer
            layer_defn = layer.GetLayerDefn()
            for i in range(layer_defn.GetFieldCount()):
                field_defn = layer_defn.GetFieldDefn(i)
                out_layer.CreateField(field_defn)

            # Copy the features from the input layer to the output layer
            for feature in layer:
                out_feature = ogr.Feature(out_layer.GetLayerDefn())
                out_feature.SetGeometry(feature.GetGeometryRef().Clone())
                for i in range(feature.GetFieldCount()):
                    out_feature.SetField(i, feature.GetField(i))
                out_layer.CreateFeature(out_feature)
                out_feature = None

            out_ds = None

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
