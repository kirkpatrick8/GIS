import streamlit as st
import pandas as pd
import geopandas as gpd
import ezdxf
from ezdxf import recover
from shapely.geometry import Point, LineString, Polygon
import tempfile
import os
import zipfile
from pyproj import CRS
import io

def log_debug(message):
    st.write(f"Debug: {message}")

def get_crs_options():
    crs_options = {
        'EPSG:4326': 'WGS 84',
        'EPSG:27700': 'OSGB 1936 / British National Grid',
        'EPSG:29901': 'TM65 / Irish Grid',
        'EPSG:29902': 'TM75 / Irish Grid',
        'EPSG:2157': 'IRENET95 / Irish Transverse Mercator',
        'EPSG:7405': 'OSGB36 / British National Grid + ODN height',
        'EPSG:4937': 'ETRS89-GRS80',
        'EPSG:3857': 'WGS 84 / Pseudo-Mercator',
    }
    return crs_options

def process_csv(file, crs):
    try:
        log_debug("Reading CSV file")
        df = pd.read_csv(file)
        log_debug(f"CSV columns: {df.columns.tolist()}")
        
        if 'latitude' in df.columns and 'longitude' in df.columns:
            log_debug("Using latitude and longitude columns")
            geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
        elif 'x' in df.columns and 'y' in df.columns:
            log_debug("Using x and y columns")
            geometry = [Point(xy) for xy in zip(df['x'], df['y'])]
        else:
            st.error("CSV must contain 'latitude' and 'longitude' or 'x' and 'y' columns.")
            log_debug("Required columns not found in CSV")
            return None
        
        log_debug("Creating GeoDataFrame")
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
        log_debug(f"GeoDataFrame created with {len(gdf)} rows")
        return gdf
    except Exception as e:
        st.error(f"Error processing CSV: {str(e)}")
        log_debug(f"Error in process_csv: {str(e)}")
        return None

def process_cad(file, crs, file_type):
    try:
        log_debug(f"Processing {file_type.upper()} file")
        file_content = file.read()
        
        if file_type == 'dwg':
            with tempfile.NamedTemporaryFile(delete=False, suffix='.dwg') as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            doc = recover.readfile(tmp_file_path)
            os.unlink(tmp_file_path)
        else:  # dxf
            doc = ezdxf.read(io.BytesIO(file_content))
        
        msp = doc.modelspace()

        entities = []
        for entity in msp:
            geom = None
            properties = {'dxftype': entity.dxftype()}
            
            if entity.dxftype() == 'POINT':
                geom = Point(entity.dxf.location[:2])
            elif entity.dxftype() == 'LINE':
                geom = LineString([entity.dxf.start[:2], entity.dxf.end[:2]])
            elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                points = entity.get_points()
                if len(points) > 2:
                    geom = Polygon(points)
                elif len(points) == 2:
                    geom = LineString(points)
            
            if geom:
                for attr in entity.dxf.all_existing_dxf_attribs():
                    properties[attr] = str(getattr(entity.dxf, attr))
                entities.append({'geometry': geom, 'properties': properties})

        log_debug(f"Processed {len(entities)} entities")

        if entities:
            gdf = gpd.GeoDataFrame(
                [e['properties'] for e in entities],
                geometry=[e['geometry'] for e in entities],
                crs=crs
            )
            log_debug(f"GeoDataFrame created with {len(gdf)} rows")
            return gdf
        else:
            st.error(f"No valid geometries found in the {file_type.upper()} file.")
            log_debug("No valid geometries found")
            return None
    except Exception as e:
        st.error(f"Error processing {file_type.upper()}: {str(e)}")
        log_debug(f"Error in process_cad: {str(e)}")
        return None

def save_and_zip_shapefile(gdf, output_filename):
    try:
        log_debug("Saving and zipping shapefile")
        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = os.path.join(tmpdir, output_filename)
            log_debug(f"Saving shapefile to {shp_path}")
            gdf.to_file(shp_path)
            
            zip_path = f"{output_filename}.zip"
            log_debug(f"Creating zip file: {zip_path}")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(tmpdir):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)
            
            log_debug("Shapefile saved and zipped successfully")
        return zip_path
    except Exception as e:
        st.error(f"Error saving shapefile: {str(e)}")
        log_debug(f"Error in save_and_zip_shapefile: {str(e)}")
        return None

def main():
    st.title('File to Shapefile Converter')
    st.write("This app converts CSV, DXF, or DWG files to shapefiles.")
    log_debug("App started")

    file = st.file_uploader("Choose a CSV, DXF, or DWG file", type=["csv", "dxf", "dwg"])
    log_debug("File uploader displayed")
    
    crs_options = get_crs_options()
    selected_crs = st.selectbox(
        "Select coordinate system",
        list(crs_options.keys()),
        format_func=lambda x: f"{x} - {crs_options[x]}"
    )
    crs = CRS(selected_crs)
    log_debug(f"Selected CRS: {selected_crs}")

    if file is not None:
        log_debug(f"File uploaded: {file.name}, Size: {file.size} bytes, Type: {file.type}")
        file_extension = os.path.splitext(file.name)[1].lower()
        
        try:
            if file_extension == '.csv':
                log_debug("Processing CSV file")
                gdf = process_csv(file, crs)
            elif file_extension in ['.dxf', '.dwg']:
                log_debug(f"Processing {file_extension[1:].upper()} file")
                gdf = process_cad(file, crs, file_extension[1:])
            else:
                st.error("Unsupported file format. Please use CSV, DXF, or DWG files.")
                log_debug(f"Unsupported file format: {file_extension}")
                return

            if gdf is not None:
                st.write("Data preview:")
                st.write(gdf.head())
                log_debug(f"GeoDataFrame created successfully with {len(gdf)} rows")

                output_filename = st.text_input("Enter output filename (without extension)", "output")
                log_debug(f"Output filename set to: {output_filename}")
                
                if st.button('Convert to Shapefile'):
                    log_debug("Convert button clicked")
                    with st.spinner('Converting to shapefile...'):
                        zip_filename = save_and_zip_shapefile(gdf, output_filename)
                    
                    if zip_filename:
                        log_debug(f"Shapefile created: {zip_filename}")
                        with open(zip_filename, "rb") as fp:
                            st.download_button(
                                label="Download Shapefile",
                                data=fp,
                                file_name=zip_filename,
                                mime="application/zip"
                            )
                        st.success(f"Shapefile created and zipped: {zip_filename}")
                    else:
                        st.error("Failed to create shapefile. Please try again.")
                        log_debug("Failed to create shapefile")
            else:
                st.error("Failed to process the file. Please check the file format and try again.")
                log_debug("Failed to create GeoDataFrame")
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            log_debug(f"Unexpected error in main: {str(e)}")
    else:
        st.write("Please upload a CSV, DXF, or DWG file to begin.")
        log_debug("Waiting for file upload")

if __name__ == "__main__":
    main()
