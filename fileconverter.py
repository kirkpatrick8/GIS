"""
File to Shapefile Converter

This script converts CAD (DXF) or CSV files to shapefiles. 

For CSV files, the following formats are supported:

1. Polygon:
   - Required columns: 'id', 'polygon'
   - 'polygon' column should contain coordinate pairs as a string, e.g.:
     "[(x1,y1), (x2,y2), (x3,y3), ...]"
   Example:
   id,polygon
   1,"[(0,0), (0,1), (1,1), (1,0)]"
   2,"[(2,2), (2,3), (3,3), (3,2)]"

2. Point:
   - Required columns: 'id', 'latitude', 'longitude'
   Example:
   id,latitude,longitude
   1,40.7128,-74.0060
   2,34.0522,-118.2437

3. Linestring:
   - Required columns: 'id', 'linestring'
   - 'linestring' column should contain coordinate pairs as a string, e.g.:
     "[(x1,y1), (x2,y2), ...]"
   Example:
   id,linestring
   1,"[(0,0), (1,1), (2,2)]"
   2,"[(3,3), (4,4), (5,5)]"

For DXF files, the script will automatically extract points, lines, and polygons.

Usage:
python file_to_shapefile.py input_file output_file [--geometry_type {polygon,point,linestring}]

Examples:
python file_to_shapefile.py input.csv output.shp --geometry_type polygon
python file_to_shapefile.py input.dxf output.shp
"""

import argparse
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point, LineString
import ezdxf

def csv_to_shapefile(input_file, output_file, geometry_type='polygon'):
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Ensure the CSV has the required columns
    if geometry_type == 'polygon':
        required_columns = ['id', 'polygon']
    elif geometry_type == 'point':
        required_columns = ['id', 'latitude', 'longitude']
    elif geometry_type == 'linestring':
        required_columns = ['id', 'linestring']
    
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"CSV must contain {required_columns} columns")
    
    # Convert to geometry based on the type
    if geometry_type == 'polygon':
        df['geometry'] = df['polygon'].apply(lambda x: Polygon(eval(x)))
    elif geometry_type == 'point':
        df['geometry'] = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    elif geometry_type == 'linestring':
        df['geometry'] = df['linestring'].apply(lambda x: LineString(eval(x)))
    
    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry='geometry')
    
    # Set the coordinate reference system (CRS) to EPSG:4326 (WGS84)
    gdf.crs = "EPSG:4326"
    
    # Save to shapefile
    gdf.to_file(output_file, driver='ESRI Shapefile')

def dxf_to_shapefile(input_file, output_file):
    # Read the DXF file
    doc = ezdxf.readfile(input_file)
    msp = doc.modelspace()
    
    # Create empty lists for different geometry types
    points = []
    lines = []
    polygons = []
    
    # Iterate through entities in the DXF file
    for entity in msp:
        if entity.dxftype() == 'POINT':
            points.append(Point(entity.dxf.location[:2]))
        elif entity.dxftype() == 'LINE':
            lines.append(LineString([entity.dxf.start[:2], entity.dxf.end[:2]]))
        elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
            polygons.append(Polygon(entity.get_points()))
    
    # Create GeoDataFrames for each geometry type
    gdf_points = gpd.GeoDataFrame(geometry=points) if points else None
    gdf_lines = gpd.GeoDataFrame(geometry=lines) if lines else None
    gdf_polygons = gpd.GeoDataFrame(geometry=polygons) if polygons else None
    
    # Combine all GeoDataFrames
    gdfs = [gdf for gdf in [gdf_points, gdf_lines, gdf_polygons] if gdf is not None]
    if gdfs:
        gdf = pd.concat(gdfs, ignore_index=True)
        gdf.crs = "EPSG:4326"  # Assuming WGS84, adjust if necessary
        
        # Save to shapefile
        gdf.to_file(output_file, driver='ESRI Shapefile')
    else:
        raise ValueError("No valid geometries found in the DXF file")

def main():
    parser = argparse.ArgumentParser(description="Convert CAD (DXF) or CSV files to shapefiles.")
    parser.add_argument("input_file", help="Input file path (DXF or CSV)")
    parser.add_argument("output_file", help="Output shapefile path")
    parser.add_argument("--geometry_type", choices=['polygon', 'point', 'linestring'], default='polygon',
                        help="Geometry type for CSV conversion (default: polygon)")
    
    args = parser.parse_args()
    
    input_extension = os.path.splitext(args.input_file)[1].lower()
    
    try:
        if input_extension == '.csv':
            csv_to_shapefile(args.input_file, args.output_file, args.geometry_type)
            print(f"CSV file successfully converted to shapefile: {args.output_file}")
        elif input_extension == '.dxf':
            dxf_to_shapefile(args.input_file, args.output_file)
            print(f"DXF file successfully converted to shapefile: {args.output_file}")
        else:
            raise ValueError("Unsupported file format. Please use CSV or DXF files.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
