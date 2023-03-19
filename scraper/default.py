"""
Title: default scraper
Author: David Oesch
Date: 2022-11-05
Purpose: This script is be a part of a larger script that scrapes metadata information from 
    OGC web service metadata files and stores it in a dictionary called "layer_data". 
    It uses the OWSLib library to access the metadata information and the re library to 
    clean up the information (remove newlines, HTML fragments, etc.). The script collects 
    information such as owner, title, name, tree structure, group, abstract, keywords, and legend of the OGC web service layers.
"""

import re
import math
import requests
import json
import time
from requests.utils import requote_uri
from pyproj import Transformer
# Define a transformer to convert from WGS84 to LV95
transformer = Transformer.from_crs("EPSG:4326", 'EPSG:2056')

def shorten_mapgeo(mapgeo):
    # Set the API endpoint URL
    url = "https://s.geo.admin.ch/"

    # Set the headers for the POST request
    headers = {
        'content-type': 'application/json; charset=UTF-8',
        'origin': 'https://map.geo.admin.ch',
        'referer': 'https://map.geo.admin.ch/',
        'user-agent': 'GeoHarvester e2e' # Only to be nice
    }

    # Try the request up to 3 times    
    for i in range(3):
        # Make the POST request    
        r = requests.post(url=url, data=json.dumps({'url': requote_uri(mapgeo)}), headers=headers)
        # Code to execute if status code is 2xx (i.e. 200, 201, 202, etc.)
        if r.status_code // 100 == 2:
            # Convert the response data to a JSON object
            data = r.json()
            # Return the response data if the request was successful
            return data['shorturl']
        else:
            # If the response was not successful, print an error message
            print(f"Request failed with status code {r.status_code}. Retrying...")
            # Wait for a few seconds before retrying
            time.sleep(5)
    # If all retries fail, print an error message and return None
    print("Request failed after 3 retries. providing no shorted URL")
    data=mapgeo
    return data

def remove_newline(toclean):
    """
    Remove newline characters, enumeration, and HTML fragments from a string.

    Args:
        toclean (str): The string to be cleaned.

    Returns:
        str: The cleaned string.

    """
    if toclean:
        #remove newlines and ennumernation
        test=re.sub(r'[\n\r\t\f\v]', ' ', toclean)
        #remove HTML Fragments
        clean = re.compile('<.*?>')
        test=re.sub(clean, '', test)
    else:
        test=""
    return(test)

#SERVICE WMS
def scrape(source,service,i,layertree, group,layer_data,prefix):
    """
    Extract metadata information from WMS service and stores it in the `layer_data` dictionary.
    
    Parameters:
    source (dict): A dictionary containing information about the source of the service.
    service (owslib.wms.WebMapService): A WM(T/F)S service object from the owslib library.
    i (int): An index value pointing to a particular layer in the service.
    layertree (str): A string representation of the tree structure of the layer.
    group (str): The name of the parent layer group.
    layer_data (dict): A dictionary to store the extracted metadata information.
    prefix (str): A prefix string to add to each key in the `layer_data` dictionary.
    
    Returns:
    None
    
    Notes:
    The extracted metadata information includes the following fields:
    - OWNER: Description of the source of the service
    - TITLE: Title of the layer
    - NAME: Name of the layer
    - TREE: Tree structure of the layer
    - GROUP: Name of the parent layer group
    - ABSTRACT: Abstract information of the layer and access constraints of the service
    - KEYWORDS: Keywords associated with the layer and the service
    - LEGEND: Legend URL of the layer
    - CONTACT: Contact information of the provider of the service
    """
    type=source['URL']
    #breakpoint()

    #owner
    layer_data["OWNER"]= source['Description']
    
    #title
    layer_data["TITLE"]= service.contents[i].title

    #name
    if hasattr(service.contents[i], 'name'):
        layer_data["NAME"] = service.contents[i].name
    elif hasattr(service.contents[i], 'id'):
        layer_data["NAME"] = service.contents[i].id
    else:
        layer_data["NAME"] = ""

    
    #tree    
    layer_data["TREE"]= layertree
    
    #group
    layer = service.contents[i]
    if hasattr(layer, 'parent') and layer.parent is not None:
        layer_data["GROUP"] = layer.parent.name
    elif group != 0:
        layer_data["GROUP"] = group
    else:
        layer_data["GROUP"] = ""

    #abstract
    temp = service.contents[i].abstract
    layer_data["ABSTRACT"] = remove_newline(temp) if temp else ""

    #keywords
    keywords = [k for k in service.contents[i].keywords if k is not None]
    layer_data["KEYWORDS"] = ", ".join(keywords)    
    
    #legend    
    if service.contents[i].styles is not None:
        if 'default' in service.contents[i].styles.keys():
            if 'legend' in service.contents[i].styles['default']:
                layer_data["LEGEND"] = service.contents[i].styles['default']['legend']
            else:
                layer_data["LEGEND"] = ""
        elif len(service.contents[i].styles) == 1:
            if 'legend' in service.contents[i].styles[list(service.contents[i].styles.keys())[0]]:
                layer_data["LEGEND"] = service.contents[i].styles[list(service.contents[i].styles.keys())[0]]['legend']
            else:
                layer_data["LEGEND"] = ""
        elif service.contents[i]._children:
            if service.contents[i]._children[0].styles is not None and 'default' in service.contents[i]._children[0].styles.keys():
                if 'legend' in service.contents[i]._children[0].styles['default']:
                    layer_data["LEGEND"] = service.contents[i]._children[0].styles['default']['legend']
                else:
                    layer_data["LEGEND"] = ""
            else:
                layer_data["LEGEND"] = ""
        else:
            layer_data["LEGEND"] = ""
    else:
        layer_data["LEGEND"] = ""

    
    #contact
    if hasattr(service, 'provider'):
        if hasattr(service.provider, 'contact') and service.provider.contact and hasattr(service.provider.contact, 'email'):
            layer_data["CONTACT"] = service.provider.contact.email
        elif hasattr(service.provider, 'name'):
            layer_data["CONTACT"] = service.provider.name
    else:
        layer_data["CONTACT"] = ""

    
    #servicelink
    service_link=source['URL']
    if "?" in service_link:
        layer_data["SERVICELINK"] = service_link.split("?")[0]
    else:
        layer_data["SERVICELINK"] = source['URL']
        

    #metadata
    try:
        layer_data["METADATA"] = service.contents[i].metadataUrls[0]['url'] if len(service.contents[i].metadataUrls) == 1 else ""
    except:
        try:
            layer_data["METADATA"] = service.serviceMetadataURL
        except:
            try:
                layer_data["METADATA"] = service.contents[i].layers[0].metadataUrls[0]['url']
            except:
                try:
                    url = re.findall(regex,service.contents[i].abstract)
                    layer_data["METADATA"] = url[0][0] if len(url) == 1 else ""
                except:
                    layer_data["METADATA"] = ""

    #update
    layer_data["UPDATE"]=""

    #center coords LAT
    
    if 'boundingBoxWGS84' in service.contents[i].__dict__ and service.contents[i].boundingBoxWGS84 is not None and len(service.contents[i].boundingBoxWGS84) == 4:
        layer_data["CENTER_LAT"]=round((service.contents[i].boundingBoxWGS84[1]+service.contents[i].boundingBoxWGS84[3])/2,2)
    elif 'boundingBox' in service.contents[i].__dict__ and service.contents[i].boundingBox is not None and len(service.contents[i].boundingBox) == 4:
        layer_data["CENTER_LAT"]=round((service.contents[i].boundingBox[1]+service.contents[i].boundingBox[3])/2,2)
    else:
        layer_data["CENTER_LAT"] = 46.78485

    #center coords LON
    if 'boundingBoxWGS84' in service.contents[i].__dict__ and service.contents[i].boundingBoxWGS84 is not None and len(service.contents[i].boundingBoxWGS84) == 4:
        layer_data["CENTER_LON"]=round((service.contents[i].boundingBoxWGS84[0]+service.contents[i].boundingBoxWGS84[2])/2,2)
    elif 'boundingBox' in service.contents[i].__dict__ and service.contents[i].boundingBox is not None and len(service.contents[i].boundingBox) == 4:
        layer_data["CENTER_LON"]=round((service.contents[i].boundingBox[0]+service.contents[i].boundingBox[2])/2,2)
    else:
        layer_data["CENTER_LON"] = 7.88932
    
    #BBOX
    bbox = None
    if 'boundingBoxWGS84' in service.contents[i].__dict__:
        bbox = service.contents[i].boundingBoxWGS84
    elif 'boundingBox' in service.contents[i].__dict__ and len(service.contents[i].boundingBox) > 0:
        bbox = list(map(float, str(service.contents[i].boundingBox[0].extent).replace("(", "").replace(")", "").split(",")))

    if bbox and len(bbox) == 4:
        layer_data["BBOX"] = ' '.join([str(elem) for elem in bbox])
    else:#set to swiss box swiss bbox
        coordinates_str="5.88932 45.78485 10.88932 47.78485"
        layer_data["BBOX"] = coordinates_str 
        coordinates_list = coordinates_str.split()
        coordinates_float = [float(coord) for coord in coordinates_list]
        bbox = tuple(coordinates_float)

    
    #maxzoom
    """
    Calculates the appropriate zoom level for a bounding box in Web Mercator projection.
            bbox (tuple): A tuple containing the bounding box coordinates in Web Mercator projection
            as (xmin, ymin, xmax, ymax).
        map_width_px (int): The width of the map viewer in pixels.
        screen_dpi (int): The dots per inch (DPI) of the screen.
    
    
        int: The appropriate zoom level for the given bounding box and screen parameters.
    """
    map_width_px =800
    screen_dpi=96
    
    # Calculate the distance between the two corners of the bounding box in meters.
    distance = math.sqrt((bbox[2] - bbox[0])**2 + (bbox[3] - bbox[1])**2)
    
    if "test." in prefix: #webmapviewer use case
        # Calculate the appropriate zoom level using the formula for Web Mercator projection.
        zoom = math.log2((156543.03 * map_width_px) / (256 * screen_dpi * distance))
    else: #mf-geoadmin3 use case
       
        # Transform the WGS84 bbox to LV95
        xmin, ymin = transformer.transform(bbox[0], bbox[1])
        xmax, ymax = transformer.transform(bbox[2], bbox[3])
        
        # Calculate the distance between the two corners of the bounding box in meters.
        distance = math.sqrt((xmax - xmin)**2 + (ymax - ymin)**2)
        
        if math.isnan(distance) or distance <= 0:
            zoom=1
        else:
            # Calculate the appropriate zoom level using the formula for LV95 projection.
            zoom = 13 - math.floor(math.log2(distance / (map_width_px * screen_dpi / 96 / 0.0254 / 256)))
            
        # Ensure the zoom level is within the valid range (0 to 13)
        zoom = max(0, min(zoom, 13))
    # Round the zoom level to the nearest integer and return it.
    layer_data["MAX_ZOOM"]= round(zoom) # 7  is the map.geo.admin.ch map zoom at approx 1:20k
   


    #now the service specific stuff

    #see if we work with mf-geoadmin3
    if "test." not in prefix:
        if math.isnan(distance):
            lon_lv95=2663000 
            lat_lv95=1189572
        else:
            # Convert the latitude from WGS84 to LV95
            lon_lv95, lat_lv95 = transformer.transform(layer_data["CENTER_LAT"], layer_data["CENTER_LON"])
        


    if "WMS" in type or "wms" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WMS"    

        #mapgeolink
        if source['Description'] != "Bund":
        # for re3 
            # UNCOMMENT THIS SECTION and REMOVE SECTION below when not running on github since shortening takes time!
            # layer_data["MAPGEO"]= shorten_mapgeo(r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.url+"?||"+\
            #    service.contents[i].id+"||"\
            #    +service.identification.version+"&E="+str(lon_lv95)+\
            #    "&N="+str(lat_lv95)+"&zoom="+str(layer_data["MAX_ZOOM"]))

            layer_data["MAPGEO"]= r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.url+"?||"+\
                service.contents[i].id+"||"\
                +service.identification.version+"&E="+str(lon_lv95)+\
                "&N="+str(lat_lv95)+"&zoom="+str(layer_data["MAX_ZOOM"])
            
        #for web-mapviewer    
        #    layer_data["MAPGEO"]= shorten_mapgeo(r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.url+"?||"+\
        #        service.contents[i].id+"||"\
        #        +service.identification.version+"&lat="+str(layer_data["CENTER_LAT"])+"&lon="+\
        #        str(layer_data["CENTER_LON"])+"&z="+str(layer_data["MAX_ZOOM"]))
        else:
            # UNCOMMENT THIS SECTION and REMOVE SECTION below when not running on github since shortening takes time!
            #layer_data["MAPGEO"]= shorten_mapgeo(r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.provider.url+"?||"+\
            #service.contents[i].id+"||"+service.identification.version)
            layer_data["MAPGEO"]= r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.provider.url+"?||"+\
            service.contents[i].id+"||"+service.identification.version
        return(layer_data)

    elif "WMTS" in type or "wmts" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WMTS"    


        #mapgeolink
        if source['Description'] != "Bund":
        # for re3    
         # UNCOMMENT THIS SECTION and REMOVE SECTION below when not running on github since shortening takes time!
         #   layer_data["MAPGEO"]= shorten_mapgeo(r""+prefix+"layers=WMTS||"+service.contents[i].id+"||"\
         #       +service.url+"&E="+str(lon_lv95)+\
         #       "&N="+str(lat_lv95)+"&zoom="+str(layer_data["MAX_ZOOM"]))
            
            layer_data["MAPGEO"]= r""+prefix+"layers=WMTS||"+service.contents[i].id+"||"\
                +service.url+"&E="+str(lon_lv95)+\
                "&N="+str(lat_lv95)+"&zoom="+str(layer_data["MAX_ZOOM"])
        #for web-mapviewer
        #    layer_data["MAPGEO"]= shorten_mapgeo(r""+prefix+"layers=WMTS||"+service.contents[i].id+"||"\
        #        +service.url+"&lat="+str(layer_data["CENTER_LAT"])+"&lon="+\
        #        str(layer_data["CENTER_LON"])+"&z="+str(layer_data["MAX_ZOOM"]))

        else:
            layer_data["MAPGEO"]= shorten_mapgeo(r""+prefix+"layers="+service.contents[i].id)
        return(layer_data)

    elif "WFS" in type or "wfs" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WFS"    
        
        return(layer_data)
    elif "STAC" in type:
        print("STAC detetcted ..add config")
    else:
        return(False)        

    
