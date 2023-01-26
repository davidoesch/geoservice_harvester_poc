#Create OWSLIB configfile 
#
# Source https://ckan.opendata.swiss/api/3/action/package_search?fq=organization:geoinformation-kanton-zuerich%20AND%20res_format:WMS&rows=10000
# 
#https://ckan.opendata.swiss/api/3/action/package_search?fq=organization:geoinformation-kanton-zuerich%20AND%20res_format:WFS&rows=10000
import re
def remove_newline(toclean):
    if toclean:
        test=re.sub(r'[\n\r\t\f\v]', ' ', toclean)
    else:
        test=""
    return(test)

#SERVICE WMS
def scrape(source,service,i,layertree, group,layer_data,prefix):
    type=source['URL']
    
    if "wms" in type:
        layer_data["OWNER"]= source['Description']
        layer_data["TITLE"]= service.contents[i].title
        layer_data["NAME"]= service.contents[i].name
        layer_data["TREE"]= layertree
        layer=service.contents[i]
        layer_data["GROUP"]= layer.parent.name if layer.parent is not None else ""
        if  service.contents[i].parent is not None and service.contents[i].parent.abstract is not None:
            temp=str(service.contents[i].abstract)+" "+service.contents[i].parent.abstract
        else:
            temp=service.contents[i].abstract
        layer_data["ABSTRACT"]=remove_newline(temp)
        layer_data["KEYWORDS"]= ", ".join(service.contents[i].keywords+service.identification.keywords)
        layer_data["LEGEND"]= service.contents[i].styles['default']['legend'] if 'default' in service.contents[i].styles.keys() else ""
        layer_data["CONTACT"]=service.provider.contact.email
        layer_data["SERVICELINK"]=service.request
        layer_data["METADATA"]=service.contents[i].metadataUrls[0]['url'] if len(service.contents[i].metadataUrls) == 1 else ""
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
        
        return(layer_data)
    elif "wmts" in type:
        layer_data["OWNER"]= source['Description']
        layer_data["TITLE"]= service.contents[i].title
        layer_data["NAME"]= service.contents[i].name
        layer_data["TREE"]= layertree
        layer_data["GROUP"]= group if group != 0 else ""
        layer_data["ABSTRACT"]= remove_newline(service.identification.abstract+" "+service.identification.accessconstraints)
        layer_data["KEYWORDS"]= ", ".join(service.contents[i].keywords+service.identification.keywords)
        layer_data["LEGEND"]= service.contents[i].styles['default']['legend'] if 'legend' in service.contents[i].styles.keys() else ""
        layer_data["CONTACT"]=service.provider.name
        layer_data["SERVICELINK"]=service.url
        layer_data["METADATA"]=service.serviceMetadataURL
        layer_data["UPDATE"]=""
        layer_data["SERVICETYPE"]=service.identification.type
        layer_data["MAX_ZOOM"]= 7 #this is the map.geo.admin.ch map zoom at approx 1:20k
        layer_data["CENTER_LAT"]=(service[i].boundingBoxWGS84[1]+service[i].boundingBoxWGS84[3])/2
        layer_data["CENTER_LON"]=(service[i].boundingBoxWGS84[0]+service[i].boundingBoxWGS84[2])/2
        layer_data["BBOX"]=' '.join([str(elem) for elem in (service.contents[i].boundingBox)])
        layer_data["MAPGEO"]= r""+prefix+"layers="+layer_data["SERVICETYPE"].partition(" ")[2]+\
            "||"+service.contents[i].id+"||"+service.url+"&swisssearch="+str(layer_data["CENTER_LAT"])+\
            "%20"+str(layer_data["CENTER_LON"])+"&zoom="+str(layer_data["MAX_ZOOM"])
        
        return(layer_data)   
    elif "wfs" in type:
        
        layer_data["OWNER"]= source['Description']
        layer_data["TITLE"]= service.contents[i].title
        layer_data["NAME"]= service.contents[i].id
        layer_data["TREE"]= layertree
        layer_data["GROUP"]= group if group != 0 else ""
        temp=service.contents[i].abstract
        layer_data["ABSTRACT"]=temp.replace('\r\n','') if temp is not None else ""
        layer_data["KEYWORDS"]= ", ".join(service.contents[i].keywords+service.identification.keywords)
        layer_data["LEGEND"]= ""
        layer_data["CONTACT"]=service.provider.contact.email
        layer_data["SERVICELINK"]=service.url
        layer_data["METADATA"]=service.contents[i].metadataUrls[0]['url'] if len(service.contents[i].metadataUrls) == 1 else ""
        layer_data["UPDATE"]=""
        layer_data["SERVICETYPE"]=service.identification.type
        layer_data["MAX_ZOOM"]= "" #this is the map.geo.admin.ch map zoom at approx 1:20k
        layer_data["CENTER_LAT"]=(service[i].boundingBoxWGS84[1]+service[i].boundingBoxWGS84[3])/2
        layer_data["CENTER_LON"]=(service[i].boundingBoxWGS84[0]+service[i].boundingBoxWGS84[2])/2
        layer_data["BBOX"]=' '.join([str(elem) for elem in (service.contents[i].boundingBoxWGS84)])
        
        return(layer_data)                
    elif type == "STAC":
        print("STAC detetcted ..add config")
    else:
        return(False)        

    