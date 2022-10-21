#Create OWSLIB configfile 

#SERVICE WMS
def scrape(source,service,i,layertree, group,layer_data,prefix):
    type=service.identification.type
   
    if type == "WMS":
        layer_data["OWNER"]= source['Description']
        layer_data["TITLE"]= service.contents[i].title
        layer_data["NAME"]= service.contents[i].name
        layer_data["TREE"]= layertree
        layer_data["GROUP"]= group if group != 0 else ""
        temp=service.contents[i].abstract+" "+service.contents[i].parent.abstract
        layer_data["ABSTRACT"]=temp.replace('\n','') 
        #layer_data["KEYWORDS"]= ", ".join(service.contents[i].keywords+service.identification.keywords)
        layer_data["KEYWORDS"]=service.contents[i].keywords
        layer_data["LEGEND"]= service.contents[i].styles['default']['legend'] if 'default' in service.contents[i].styles.keys() else ""
        layer_data["CONTACT"]=service.provider.contact.email
        layer_data["SERVICELINK"]=service.request
        layer_data["METADATA"]=layer_data["METADATA"]=service.contents[i].metadataUrls[0]['url'] if 0 in service.contents[i].metadataUrls else ""
        layer_data["UPDATE"]=""
        layer_data["SERVICETYPE"]=service.identification.type
        layer_data["MAX_ZOOM"]= 7 #this is the map.geo.admin.ch map zoom at approx 1:20k
        layer_data["CENTER_LAT"]=(service[i].boundingBoxWGS84[1]+service[i].boundingBoxWGS84[3])/2
        layer_data["CENTER_LON"]=(service[i].boundingBoxWGS84[0]+service[i].boundingBoxWGS84[2])/2
        layer_data["MAPGEO"]= r""+prefix+"layers="+layer_data["SERVICETYPE"]+\
            "||"+service.contents[i].id+"||"+service.url+"?||"+service.contents[i].id+"||"\
            +service.identification.version+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
            "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        return(layer_data)
    elif type == "WMTS":
        print("WMTS detetcted ..add config")        
    elif type == "STAC":
        print("STAC detetcted ..add config")
    else:
        return(False)        

    