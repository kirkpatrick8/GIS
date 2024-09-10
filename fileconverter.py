import streamlit as st
import pandas as pd
import geopandas as gpd
import ezdxf
from shapely.geometry import Point, LineString, Polygon
import tempfile
import os
import zipfile

def log_debug(message):
    st.write(f"Debug: {message}")

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

def process_dxf(file, crs):
    try:
        log_debug("Reading DXF file")
        doc = ezdxf.readfile(file)
        msp = doc.modelspace()

        points, lines, polygons = [], [], []
        log_debug("Processing DXF entities")

        for entity in msp:
            if entity.dxftype() == 'POINT':
                points.append(Point(entity.dxf.location[:2]))
            elif entity.dxftype() == 'LINE':
                lines.append(LineString([entity.dxf.start[:2], entity.dxf.end[:2]]))
            elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                polygons.append(Polygon(entity.get_points()))

        log_debug(f"Processed {len(points)} points, {len(lines)} lines, {len(polygons)} polygons")

        gdfs = []
        if points:
            gdfs.append(gpd.GeoDataFrame(geometry=points, crs=crs))
        if lines:
            gdfs.append(gpd.GeoDataFrame(geometry=lines, crs=crs))
        if polygons:
            gdfs.append(gpd.GeoDataFrame(geometry=polygons, crs=crs))

        if gdfs:
            log_debug("Concatenating GeoDataFrames")
            return pd.concat(gdfs, ignore_index=True)
        else:
            st.error("No valid geometries found in the DXF file.")
            log_debug("No valid geometries found")
            return None
    except Exception as e:
        st.error(f"Error processing DXF: {str(e)}")
        log_debug(f"Error in process_dxf: {str(e)}")
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
    st.write("This app converts CSV or DXF files to shapefiles.")
    log_debug("App started")

    file = st.file_uploader("Choose a CSV or DXF file", type=["csv", "dxf"])
    log_debug("File uploader displayed")
    
    crs = st.text_input("Enter the coordinate system (e.g., EPSG:4326)", "EPSG:4326")
    log_debug(f"CRS input displayed: {crs}")

    if file is not None:
        log_debug(f"File uploaded: {file.name}")
        file_extension = os.path.splitext(file.name)[1].lower()
        
        if file_extension == '.csv':
            log_debug("Processing CSV file")
            gdf = process_csv(file, crs)
        elif file_extension == '.dxf':
            log_debug("Processing DXF file")
            gdf = process_dxf(file, crs)
        else:
            st.error("Unsupported file format. Please use CSV or DXF files.")
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
        st.write("Please upload a CSV or DXF file to begin.")
        log_debug("Waiting for file upload")

if __name__ == "__main__":
    main()
