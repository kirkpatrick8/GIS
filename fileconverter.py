import streamlit as st
import pandas as pd
import geopandas as gpd
import ezdxf
from ezdxf import recover
from ezdxf.addons import odafc
from shapely.geometry import Point, LineString, Polygon
import tempfile
import os
import zipfile
from pyproj import CRS
import io
import traceback

def log_debug(message):
    st.sidebar.text(f"Debug: {message}")

def get_crs_options():
    return {
        'EPSG:4326': 'WGS 84',
        'EPSG:27700': 'OSGB 1936 / British National Grid',
        'EPSG:29901': 'TM65 / Irish Grid',
        'EPSG:29902': 'TM75 / Irish Grid',
        'EPSG:2157': 'IRENET95 / Irish Transverse Mercator',
        'EPSG:7405': 'OSGB36 / British National Grid + ODN height',
        'EPSG:4937': 'ETRS89-GRS80',
        'EPSG:3857': 'WGS 84 / Pseudo-Mercator',
    }

def process_csv(file, crs):
    try:
        log_debug("Reading CSV file")
        df = pd.read_csv(file)
        log_debug(f"CSV columns: {df.columns.tolist()}")
        
        geometry_column = None
        if 'latitude' in df.columns and 'longitude' in df.columns:
            log_debug("Using latitude and longitude columns")
            geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
        elif 'x' in df.columns and 'y' in df.columns:
            log_debug("Using x and y columns")
            geometry = [Point(xy) for xy in zip(df['x'], df['y'])]
        elif 'geometry' in df.columns:
            log_debug("Using geometry column")
            geometry_column = 'geometry'
        else:
            raise ValueError("CSV must contain 'latitude' and 'longitude', 'x' and 'y', or 'geometry' columns.")
        
        log_debug("Creating GeoDataFrame")
        if geometry_column:
            gdf = gpd.GeoDataFrame(df, geometry=geometry_column, crs=crs)
        else:
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
        log_debug(f"GeoDataFrame created with {len(gdf)} rows")
        return gdf
    except Exception as e:
        log_debug(f"Error processing CSV: {str(e)}")
        log_debug(f"Traceback: {traceback.format_exc()}")
        raise

def process_cad(file_path, crs):
    try:
        log_debug(f"Processing CAD file: {file_path}")
        try:
            doc = ezdxf.readfile(file_path)
        except ezdxf.DXFStructureError:
            log_debug("Error reading CAD file, attempting recovery")
            doc, auditor = recover.readfile(file_path)
            if auditor.has_errors:
                log_debug(f"Errors found during recovery: {auditor.errors}")
        
        msp = doc.modelspace()
        entities = []
        
        for entity in msp:
            try:
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
                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    geom = Point(center).buffer(radius)
                
                if geom:
                    for attr in entity.dxf.all_existing_dxf_attribs():
                        properties[attr] = str(getattr(entity.dxf, attr))
                    entities.append({'geometry': geom, 'properties': properties})
            except Exception as e:
                log_debug(f"Error processing entity {entity.dxftype()}: {str(e)}")
        
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
            raise ValueError("No valid geometries found in the CAD file.")
    except Exception as e:
        log_debug(f"Error processing CAD file: {str(e)}")
        log_debug(f"Traceback: {traceback.format_exc()}")
        raise

def convert_dwg_to_dxf(dwg_file_path):
    dxf_file_path = dwg_file_path.replace('.dwg', '.dxf')
    log_debug(f"Converting DWG to DXF: {dwg_file_path} -> {dxf_file_path}")
    odafc.convert(dwg_file_path, dxf_file_path)
    return dxf_file_path

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
        log_debug(f"Error saving shapefile: {str(e)}")
        log_debug(f"Traceback: {traceback.format_exc()}")
        raise

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
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file.getvalue())
                temp_file_path = temp_file.name

            if file_extension == '.csv':
                log_debug("Processing CSV file")
                gdf = process_csv(temp_file_path, crs)
            elif file_extension in ['.dxf', '.dwg']:
                if file_extension == '.dwg':
                    log_debug("Converting DWG to DXF")
                    dxf_file_path = convert_dwg_to_dxf(temp_file_path)
                    gdf = process_cad(dxf_file_path, crs)
                    os.unlink(dxf_file_path)
                else:
                    gdf = process_cad(temp_file_path, crs)
            else:
                raise ValueError("Unsupported file format. Please use CSV, DXF, or DWG files.")

            os.unlink(temp_file_path)

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
                    
                    log_debug(f"Shapefile created: {zip_filename}")
                    with open(zip_filename, "rb") as fp:
                        st.download_button(
                            label="Download Shapefile",
                            data=fp,
                            file_name=zip_filename,
                            mime="application/zip"
                        )
                    st.success(f"Shapefile created and zipped: {zip_filename}")
                    os.unlink(zip_filename)
            else:
                st.error("Failed to process the file. Please check the file format and try again.")
                log_debug("Failed to create GeoDataFrame")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            log_debug(f"Error in main: {str(e)}")
            log_debug(f"Traceback: {traceback.format_exc()}")
    else:
        st.write("Please upload a CSV, DXF, or DWG file to begin.")
        log_debug("Waiting for file upload")

if __name__ == "__main__":
    main()
