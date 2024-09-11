import streamlit as st
import ezdxf
from ezdxf.addons.geo import GeoProxy
import json
import tempfile

def convert_dwg_to_geojson(file_content):
    # Create a temporary file to save the uploaded content
    with tempfile.NamedTemporaryFile(delete=False, suffix='.dwg') as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name

    try:
        # Read the DWG file
        doc = ezdxf.readfile(tmp_file_path)
        msp = doc.modelspace()

        features = []

        for entity in msp:
            if entity.dxftype() == 'POINT':
                geometry = {
                    "type": "Point",
                    "coordinates": [entity.dxf.location.x, entity.dxf.location.y]
                }
            elif entity.dxftype() == 'LINE':
                geometry = {
                    "type": "LineString",
                    "coordinates": [
                        [entity.dxf.start.x, entity.dxf.start.y],
                        [entity.dxf.end.x, entity.dxf.end.y]
                    ]
                }
            elif entity.dxftype() == 'LWPOLYLINE':
                points = list(entity.get_points())
                geometry = {
                    "type": "LineString",
                    "coordinates": [[p[0], p[1]] for p in points]
                }
                if entity.closed:
                    geometry["type"] = "Polygon"
                    geometry["coordinates"] = [geometry["coordinates"]]
            else:
                continue  # Skip unsupported entities

            feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "layer": entity.dxf.layer,
                    "type": entity.dxftype()
                }
            }
            features.append(feature)

        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        return geojson

    except Exception as e:
        raise ValueError(f"An error occurred while processing the DWG file: {str(e)}")

st.title('DWG to GeoJSON Converter')

uploaded_file = st.file_uploader("Choose a DWG file", type=['dwg'])

if uploaded_file is not None:
    try:
        file_contents = uploaded_file.read()
        geojson = convert_dwg_to_geojson(file_contents)
        
        # Convert GeoJSON to a formatted JSON string
        geojson_str = json.dumps(geojson, indent=2)
        
        st.success("Conversion successful! You can now download the GeoJSON file.")
        
        st.download_button(
            label="Download GeoJSON",
            data=geojson_str,
            file_name="converted_drawing.geojson",
            mime="application/json"
        )
        
        # Display a preview of the GeoJSON
        st.subheader("GeoJSON Preview")
        st.json(geojson)
        
    except ValueError as ve:
        st.error(str(ve))
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")

st.write("Note: This app converts basic entities (points, lines, and polylines) from the model space of the DWG file to GeoJSON. Complex entities may not be fully supported.")
