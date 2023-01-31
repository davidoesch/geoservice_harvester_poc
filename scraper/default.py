#Create OWSLIB configfile 
import re
def remove_newline(toclean):
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
    temp = service.contents[i].abstract if hasattr(service.contents[i], 'abstract') and service.contents[i].abstract is not None else ""
    if hasattr(service.contents[i], 'parent') and hasattr(service.contents[i].parent, 'abstract') and service.contents[i].parent.abstract is not None:
        temp += " " + service.contents[i].parent.abstract
    if hasattr(service.identification, 'accessconstraints') and service.identification.accessconstraints is not None:
        temp += " " + service.identification.accessconstraints
    layer_data["ABSTRACT"] = remove_newline(temp) if temp else ""


    #keywords
    if service.contents[i].keywords and service.identification.keywords:
        keywords1 = [k for k in service.contents[i].keywords if k is not None]
        keywords2 = [k for k in service.identification.keywords if k is not None]
        layer_data["KEYWORDS"] = ", ".join(keywords1 + keywords2)
    elif service.contents[i].keywords:
        keywords = [k for k in service.contents[i].keywords if k is not None]
        layer_data["KEYWORDS"] = ", ".join(keywords)
    elif service.identification.keywords:
        keywords = [k for k in service.identification.keywords if k is not None]
        layer_data["KEYWORDS"] = ", ".join(keywords)
    else:
        layer_data["KEYWORDS"] = ""

    
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
        layer_data["MAPGEO"]= r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.url+"?||"+\
            service.contents[i].id+"||"\
            +service.identification.version+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
            "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        #breakpoint()
        return(layer_data)

    elif "WMTS" in type or "wmts" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WMTS"    

        #mapgeolink
        layer_data["MAPGEO"]= r""+prefix+"layers=WMTS||"+service.contents[i].id+"||"\
            +service.url+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
            "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        return(layer_data)

    elif "WFS" in type or "wfs" in type:
        #servicetype
        layer_data["SERVICETYPE"]="WFS"    
        
        return(layer_data)
    elif "STAC" in type:
        print("STAC detetcted ..add config")
    else:
        return(False)        

    