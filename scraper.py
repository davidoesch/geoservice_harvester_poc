# -*- coding: utf-8 -*-
import os
import requests
import csv
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
import sys
import logging
import configuration as config
import importlib
import glob
sys.path.insert(0,config.SOURCE_SCRAPER_DIR)


def load_source_collection():
    """Function to open the file of sources and to load all
    sources  into a list of dicts where each list entry corresponds
    to an individual source (an individual line in the data file).

    Parameters:
    -

    Returns:
    list: A list of dictionaries with source parameters
    """
    with open(config.SOURCE_COLLECTION_CSV, mode="r", encoding="utf8") as f:
        sources = list(csv.DictReader(f, delimiter=",",
                                         quotechar='"', lineterminator="\n"))
    return sources

def test_server(source):
    """identify, if server is online
    Parameters:
    string to server with get capabilities url
    Returns:
    true: if server is online
    false: if server is note reachable
    """
    try:
        request = requests.get(source)
        if request.status_code == 200:
           return True
        else:
            log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"), 'a+')
            log_file.write(source['Description']+": "+str(request.status_code))
            log_file.close()
            print (source['Description']+": "+str(request.status_code))
            return False
    except Exception as e_request:
        log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"),  'a+')
        log_file.write(source['Description']+": "+str(e_request)+"\n")
        log_file.close()
        logger.info(source['Description']+": "+str(e_request))
        print (e_request)
       
        return False

def get_service_info(source):
    """Run OGC GetCap extraction
    Parameters:
    string to server with get capabilities url
    Returns:
    Variable for each layer
    """
    try:
        #Testing if WMS or WMTS
        try:
            service = WebMapService(source['URL'])
            child=True #assuming that wms can child/parent relation
        except:
            service = WebMapTileService(source['URL'])
            child=False #assuming that wmts can't have child/parent relation
       
        #extract all layer names
        layers=list(service.contents)
        layers_done=[]
        for i in layers:
            
            #check if we did not yet have processed that layer as child before
            #print(i)
            #breakpoint()
            
            if i not in layers_done :           
                #print(i+" processing...")
                
                if child == True:
                   children=len(service.contents[i].children)  
                else:
                   children=0
                
                #check for parent layer, when yes use  it for tree
                if children > 0 :
                    #print(i+" processing parent layer")
                    for j in range(len(service.contents[i].children)):
                        if service.contents[i]._children[j].id not in layers_done :
                            layertree= source['Description']+"/"+service.identification.title+"/"+i
                            
                            write_service_info(source,service,(service.contents[i]._children[j].id),layertree,group=i)
                            layers_done.append(service.contents[i]._children[j].id)


                else:
                    #Extracting the description for simple layer
                    #print(i+" processing NORMAL layer")
                    layertree= source['Description']+"/"+service.identification.title
                    write_service_info(source,service,i,layertree,group=0)
                    layers_done.append(i)

            else:
                print(i+" already processed")
            


    except Exception as e_request:
        log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"),  'a+')
        log_file.write(source['Description']+": "+str(e_request)+"\n")
        log_file.close()
        logger.info(source['Description']+": "+str(e_request))
        print (e_request)
        
        return False

def write_service_info(source,service,i,layertree, group):
    """Write OGC GetCap results, can be mapped in the future indicdually to each service
    Parameters:
    Var with source
    Var with GetCap results 
    String  with layer name
    String  with tree
    String  with Groupname  
    """
    
     
    #print(i)
    try:
        #Load Empty parameter list
        layer_data=(config.SERVICE_RESULT)

        #check if custom scraper is available
        scraper_spec = importlib.util.find_spec(source['Description'])

        #run custom scraper 
        if scraper_spec is not None:
            scraper =importlib.import_module(source['Description'], package=None)
            layer_data=scraper.scrape(source,service,i,layertree, group,layer_data,config.MAPGEO_PREFIX)

        #run default scraper 
        else:
           # print ("...trying default scraper" )
            scraper =importlib.import_module('default', package=None)
            layer_data=scraper.scrape(source,service,i,layertree, group,layer_data,config.MAPGEO_PREFIX)
        
        #Writing the Result file
        if os.path.isfile(config.GEOSERVICES_CH_CSV):
            with open(config.GEOSERVICES_CH_CSV, "a", encoding="utf-8") as f:
                dict_writer = csv.DictWriter(f, fieldnames=list(layer_data.keys()),
                                            delimiter="\t", quotechar='"',
                                            lineterminator="\n")
                dict_writer.writerow(layer_data)
        else:
            with open(config.GEOSERVICES_CH_CSV, "w", encoding="utf-8") as f:
                dict_writer = csv.DictWriter(f, fieldnames=list(layer_data.keys()),
                                            delimiter="\t", quotechar='"',
                                            lineterminator="\n")
                dict_writer.writeheader()
                dict_writer.writerow(layer_data)
       
        return True

    except Exception as e_request:
        log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"),  'a+')
        log_file.write(source['Description']+i+": "+str(e_request)+"\n")
        log_file.close()
        logger.info(source['Description']+i+": "+str(e_request))
        print (e_request)
        return False

#Main 
#--------------------------------------------------------------------

logger = logging.getLogger("scraper LOG")
logger.setLevel(logging.INFO)
fh = logging.FileHandler(config.LOG_FILE, "a+", "utf-8")
fh.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)


if __name__ == "__main__":
    
    #Clean up
    try:
        os.remove(config.GEOSERVICES_CH_CSV)
        fileList = glob.glob(os.path.join(config.DEAD_SERVICES_PATH,"*_error.txt"))
        for filePath in fileList:
            os.remove(filePath)
    except OSError:
        pass

    #Load sources
    sources=load_source_collection()

    for source in sources:

        #check if scraper exists for source

        
        if os.path.isfile(os.path.join(config.SOURCE_SCRAPER_DIR,source['Description'])+".py") == True:
            scraper_info=""
        else:
            scraper_info="trying DEFAULT scraper "

        print("Starting scraper  %s" % source['Description']+" with "+source['URL']+" "+scraper_info) 
        logger.info("Starting scraper  %s" % source['Description']+" with "+source['URL']+" "+scraper_info)
        #Is server online?
        if test_server(source['URL']) == True :

            #GetInfo From services per layer
            get_service_info(source)
            


        else:
            logger.info(source['Description']+" with "+source['URL']+" aborted")

    print("scraper completed")    
    logger.info("scraper completed")