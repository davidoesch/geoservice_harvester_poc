#Create OWSLIB configfile 
#Source: https://www.geo.bs.ch/geodaten/geodienste.html

def remove_newline(toclean):
    if toclean:
        test= toclean.replace('\r\n', '')
    else:
        test=""
    return(test)

#SERVICE WMS
def scrape(source,service,i,layertree, group,layer_data,prefix):
    
    type=source['URL'] #since basel does not  identify it properly as WFS
    
    if "WMS" in type:
        layer_data["OWNER"]= source['Description']
        layer_data["TITLE"]= service.contents[i].title
        layer_data["NAME"]= service.contents[i].name
        layer_data["TREE"]= layertree
        layer=service.contents[i]
        layer_data["GROUP"]= layer.parent.name if layer.parent is not None else ""
        layer_data["ABSTRACT"]=remove_newline(service.contents[i].abstract+" "+service.identification.accessconstraints if service.contents[i].abstract is not None else service.identification.accessconstraints)
        layer_data["KEYWORDS"]= ", ".join(service.contents[i].keywords+service.identification.keywords)
        try:            
            layer_data["LEGEND"]= service.contents[i]._children[0].styles['default']['legend']
        except:
            try:
                layer_data["LEGEND"]= service.contents[i].styles['default']['legend']
            except:
                layer_data["LEGEND"]= ""
        layer_data["CONTACT"]=service.provider.contact.email
        layer_data["SERVICELINK"]=service.request
        try:
            layer_data["METADATA"]= service.contents[i].metadataUrls[0]['url'] 
        except:
            try:
                layer_data["METADATA"]= service.contents[i].layers[0].metadataUrls[0]['url']
            except:
                layer_data["METADATA"]= ""
        layer_data["UPDATE"]=""
        layer_data["SERVICETYPE"]=service.identification.type
        layer_data["MAX_ZOOM"]= 7 #this is the map.geo.admin.ch map zoom at approx 1:20k
        layer_data["CENTER_LAT"]=(service[i].boundingBoxWGS84[1]+service[i].boundingBoxWGS84[3])/2
        layer_data["CENTER_LON"]=(service[i].boundingBoxWGS84[0]+service[i].boundingBoxWGS84[2])/2
        layer_data["BBOX"]=' '.join([str(elem) for elem in (service.contents[i].boundingBox)])
        layer_data["MAPGEO"]= r""+prefix+"layers=WMS||"+service.contents[i].title+"||"+service.url+"?||"+\
            service.contents[i].id+"||"\
            +service.identification.version+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
            "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        #breakpoint()
        return(layer_data)
    elif "WMTS" in type:
        #breakpoint()
        layer_data["OWNER"]= source['Description']
        layer_data["TITLE"]= service.contents[i].title
        layer_data["NAME"]= service.contents[i].name
        layer_data["TREE"]= layertree
        layer_data["GROUP"]= group if group != 0 else ""
        layer_data["ABSTRACT"]= remove_newline(service.identification.abstract+" "+service.identification.accessconstraints)
        layer_data["KEYWORDS"]= ", ".join(service.contents[i].keywords+service.identification.keywords)
        layer_data["LEGEND"]= service.contents[i].styles['default']['legend'] if 'legend' in service.contents[i].styles.keys() else ""
        layer_data["CONTACT"]=service.provider.contact.email
        layer_data["SERVICELINK"]=service.url
        layer_data["METADATA"]=service.serviceMetadataURL
        layer_data["UPDATE"]=""
        layer_data["SERVICETYPE"]=service.identification.type
        layer_data["MAX_ZOOM"]= 7 #this is the map.geo.admin.ch map zoom at approx 1:20k
        try:
            layer_data["CENTER_LAT"]=(service[i].boundingBoxWGS84[1]+service[i].boundingBoxWGS84[3])/2
            layer_data["CENTER_LON"]=(service[i].boundingBoxWGS84[0]+service[i].boundingBoxWGS84[2])/2
            layer_data["BBOX"]=' '.join([str(elem) for elem in (service.contents[i].boundingBoxWGS84)])
        except:
            bbox=list((str(service.contents[i].boundingBox[0].extent)).replace("(","").replace(")","").split(","))
            layer_data["CENTER_LAT"]=(float(bbox[1])+float(bbox[3]))/2
            layer_data["CENTER_LON"]=(float(bbox[0])+float(bbox[2]))/2
            layer_data["BBOX"]=bbox[0]+" "+bbox[1]+" "+bbox[2]+" "+bbox[3]   
        layer_data["MAPGEO"]= r""+prefix+"layers=WMTS||"+service.contents[i].title+"||"\
            +service.url+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
            "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        
        return(layer_data)
    elif "wfs" in type:
        
        layer_data["OWNER"]= source['Description']
        layer_data["TITLE"]= service.contents[i].title
        layer_data["NAME"]= service.contents[i].id
        layer_data["TREE"]= layertree
        layer_data["GROUP"]= group if group != 0 else ""
        layer_data["ABSTRACT"]= remove_newline(service.contents[i].abstract+" "+service.identification.accessconstraints if service.contents[i].abstract is not None else service.identification.accessconstraints)
        layer_data["KEYWORDS"]= ", ".join(service.contents[i].keywords+service.identification.keywords)
        try:
            layer_data["METADATA"]= service.contents[i].metadataUrls[0]['url'] 
        except:
            try:
                layer_data["METADATA"]=service.contents[i]._children[0].metadataUrls[0]['url']
            except:
                layer_data["METADATA"]= ""
        layer_data["CONTACT"]=service.provider.contact.email
        layer_data["SERVICELINK"]=service.url
        try:            
            layer_data["LEGEND"]= service.contents[i]._children[0].styles['default']['legend']
        except:
            try:
                layer_data["LEGEND"]= service.contents[i].styles['default']['legend']
            except:
                layer_data["LEGEND"]= ""
        layer_data["UPDATE"]=""
        layer_data["SERVICETYPE"]="WFS"
        layer_data["MAX_ZOOM"]= "" #this is the map.geo.admin.ch map zoom at approx 1:20k
        layer_data["CENTER_LAT"]=(service[i].boundingBoxWGS84[1]+service[i].boundingBoxWGS84[3])/2
        layer_data["CENTER_LON"]=(service[i].boundingBoxWGS84[0]+service[i].boundingBoxWGS84[2])/2
        layer_data["BBOX"]=' '.join([str(elem) for elem in (service.contents[i].boundingBoxWGS84)])
        return(layer_data)               
    elif "STAC" in type:
        print("STAC detetcted ..add config")
    else:
        return(False)        

    