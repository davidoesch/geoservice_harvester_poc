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
    if hasattr(service, 'request'):
        layer_data["SERVICELINK"] = service.request
    elif hasattr(service, 'url'):
        layer_data["SERVICELINK"] = service.url
    else:
        layer_data["SERVICELINK"] = ""

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

    #maxzoom
    layer_data["MAX_ZOOM"]= 7 #this is the map.geo.admin.ch map zoom at approx 1:20k

    #center coords LAT
    
    if 'boundingBoxWGS84' in service.contents[i].__dict__ and service.contents[i].boundingBoxWGS84 is not None and len(service.contents[i].boundingBoxWGS84) == 4:
        layer_data["CENTER_LAT"]=(service.contents[i].boundingBoxWGS84[1]+service.contents[i].boundingBoxWGS84[3])/2
    elif 'boundingBox' in service.contents[i].__dict__ and service.contents[i].boundingBox is not None and len(service.contents[i].boundingBox) == 4:
        layer_data["CENTER_LAT"]=(service.contents[i].boundingBox[1]+service.contents[i].boundingBox[3])/2
    else:
        layer_data["CENTER_LAT"] = 46.78485

    #center coords LON
    if 'boundingBoxWGS84' in service.contents[i].__dict__ and service.contents[i].boundingBoxWGS84 is not None and len(service.contents[i].boundingBoxWGS84) == 4:
        layer_data["CENTER_LON"]=(service.contents[i].boundingBoxWGS84[0]+service.contents[i].boundingBoxWGS84[2])/2
    elif 'boundingBox' in service.contents[i].__dict__ and service.contents[i].boundingBox is not None and len(service.contents[i].boundingBox) == 4:
        layer_data["CENTER_LON"]=(service.contents[i].boundingBox[0]+service.contents[i].boundingBox[2])/2
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
    else:
        layer_data["BBOX"] = "7.88932 46.78485 7.88932 46.78485"




    #no the service specific stuff
    if "WMS" in type or "wms" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WMS"    

        #mapgeolink
        if source['Description'] != "Bund":
            layer_data["MAPGEO"]= r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.url+"?||"+\
                service.contents[i].id+"||"\
                +service.identification.version+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
                "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        else:
            layer_data["MAPGEO"]= r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.provider.url+"?||"+\
            service.contents[i].id+"||"+service.identification.version
        return(layer_data)

    elif "WMTS" in type or "wmts" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WMTS"    


        #mapgeolink
        if source['Description'] != "Bund":
            layer_data["MAPGEO"]= r""+prefix+"layers=WMTS||"+service.contents[i].id+"||"\
                +service.url+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
                "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        else:
            layer_data["MAPGEO"]= r""+prefix+"layers="+service.contents[i].id

        return(layer_data)

    elif "WFS" in type or "wfs" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WFS"    
        
        return(layer_data)
    elif "STAC" in type:
        print("STAC detetcted ..add config")
    else:
        return(False)        

    
