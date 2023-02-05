# -*- coding: utf-8 -*-
"""
Title: Scraper a.k.a Geoharvester
Author: David Oesch
Date: 2022-11-05
Purpose: Retrieve information about a web map service and save it to a file
Notes: 
- Uses the OWSLib library to access the geo services
- Processes the service information to extract the layer names and other details
- Writes the extracted information to  files for future use
"""

import os
import requests
import csv
from owslib.wms import WebMapService
from owslib.wmts import WebMapTileService
from owslib.wfs import WebFeatureService
import sys
import logging
import configuration as config
import importlib
import glob
from collections import defaultdict
from statistics import mean
import xml.etree.ElementTree as ET
import re

#globals
sys.path.insert(0,config.SOURCE_SCRAPER_DIR)

service_keys=(("WMSGetCap","n.a."),("WMTSGetCap","n.a."),("WFSGetCap","n.a."))

def service_result_empty():
    """
    This function creates a dictionary object with default values for various service related fields.

    The default values are represented by the string "n.a." and are used as placeholders until actual data is available.

    The fields in the dictionary include:
    OWNER, TITLE, NAME, MAPGEO, TREE, GROUP, ABSTRACT, KEYWORDS, LEGEND, CONTACT,
    SERVICELINK, METADATA, UPDATE, LEGEND, SERVICETYPE, MAX_ZOOM, CENTER_LAT,
    CENTER_LON, MAPGEO, BBOX.

    Returns:
        A dictionary object with default values for various service related fields.

    """
    SERVICE_RESULT={"OWNER":"n.a.","TITLE":"n.a","NAME":"n.a","MAPGEO":"n.a.","TREE":"n.a.","GROUP":"","ABSTRACT":"n.a",
    "KEYWORDS":"n.a.","LEGEND":"n.a.","CONTACT":"n.a.","SERVICELINK":"n.a.",
    "METADATA":"n.a.","UPDATE":"n.a.","LEGEND":"n.a.","SERVICETYPE":"n.a.","MAX_ZOOM":"n.a.",
    "CENTER_LAT":"n.a.","CENTER_LON":"n.a.","MAPGEO":"n.a.","BBOX":"n.a."}
    return SERVICE_RESULT

#Get the Service Version
def get_version(input_url):
    response = requests.get(input_url)
    xml_data = response.content

    root = ET.fromstring(xml_data)
    try:
        version = root.attrib["version"]
    except KeyError:
        print("version attribute not found.")
        version == None
    return(version)

def write_file(input_dict,output_file):
    #Writing the Result file
    if os.path.isfile(output_file):
        with open(output_file, "a", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=list(input_dict.keys()),
                                        delimiter=",", quotechar='"',
                                        lineterminator="\n")
            dict_writer.writerow(input_dict)
            
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=list(input_dict.keys()),
                                        delimiter=",", quotechar='"',
                                        lineterminator="\n")
            dict_writer.writeheader()
            dict_writer.writerow(input_dict)
    return

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
        request = requests.get(source['URL'])
        if request.status_code == 200:
           return True
        else:
            
            log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"), 'a+')
            log_file.write(source['Description']+" "+source['URL']+": "+str(request.status_code))
            log_file.close()
            print (source['Description']+": "+str(request.status_code))
            return False
    except Exception as e_request:
        log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"),  'a+')
        log_file.write(source['Description']+" "+source['URL']+": "+str(e_request)+"\n")
        log_file.close()
        logger.info(source['Description']+source['URL']+": "+str(e_request))
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
        #Testing if WMS or WMTS/WFS
            # test for specific Version for service whcih needs to be passed to OWSLIB
        source_version=get_version(source['URL'])
        match = re.match(r"^\d+\.\d+\.\d+$", source_version)
        if match:
           source_version == source_version
        else:
            log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"),  'a+')
            log_file.write(source['Description']+": "+"invalid service version number, trying default"+"\n")
            log_file.close()
            logger.info(source['Description']+": "+"invalid service version number, trying default")
            source_version == None
        #if source['Description'] in config.SOURCE_COLLECTION_VERSION:
        #   source_version=config.SOURCE_COLLECTION_VERSION[source['Description']]
        #else:
        #   source_version=None

        #breakpoint()
        try:
            service = WebMapService(source['URL']) if source_version == None else WebMapService(source['URL'],version=source_version)
            child=True #assuming that wms can child/parent relation
        except:
            child=False #assuming that wmts can't have child/parent relation
            try:
                service = WebMapTileService(source['URL'])
            except:
                service = WebFeatureService(source['URL'], version='2.0.0') if source_version == None else WebFeatureService(source['URL'],version=source_version)
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
                #breakpoint()
                #check for parent layer, when yes use  it for tree
                if children > 0 :
                    #print(i+" processing parent layer")
                    for j in range(len(service.contents[i].children)):
                        if service.contents[i]._children[j].id not in layers_done :
                            layertree= source['Description']+"/"+service.identification.title+"/"+i.replace('"', '') if service.identification.title is not None else source['Description']+"/"+i.replace('"', '')                
                            #print(str(j)+" "+i+""+service.contents[i]._children[j].id)
                            #breakpoint()
                            write_service_info(source,service,(service.contents[i]._children[j].id),layertree,group=i)
                            layers_done.append(service.contents[i]._children[j].id)


                else:
                    #Extracting the description for simple layer
                    #print(i+" processing NORMAL layer")
                    layertree= source['Description']+"/"+service.identification.title if service.identification.title is not None else source['Description']+"/"
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
    #Load Empty parameter list
    layer_data=service_result_empty()
    
    #print(i)
    try:
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
        write_file(layer_data,config.GEOSERVICES_CH_CSV)
                
        return True

    except Exception as e_request:
        log_file = open(os.path.join(config.DEAD_SERVICES_PATH,source['Description']+"_error.txt"),  'a+')
        log_file.write(source['Description']+" "+source['URL']+" "+i+": "+str(e_request)+"\n")
        log_file.close()
        logger.info(source['Description']+i+": "+str(e_request))
        print (e_request)
        return False

def write_dataset_info(csv_filename,output_file,output_simple_file):
    """bring data in NF1 (erste normalform): one entry per data set , service is an attribut
    Parameters:
    Var with source file
    Var with Outputfile 
    Var with simplified output file (just title nad map geo link
    """
    # create an empty list to store already processed  datasetUID
    geo_data_done=[] 

    #read CSV in dict
    lst=[*csv.DictReader(open(csv_filename, encoding="utf-8"),delimiter=",", quotechar='"',lineterminator="\n")]

    for i in lst:
    #filter for unique ID consisting of TITLE NAME and OWNER
        lst_layers=list(filter(lambda lst: (lst['TITLE'] == i['TITLE']) and (lst['NAME'] == i['NAME']) and (lst['OWNER'] == i['OWNER']), lst))  
        
        checklayer=i['OWNER']+"_"+i['TITLE']+"_"+i['NAME']#create a datasetUID

        if checklayer not in geo_data_done:
            #get new empty layer
            dataset=service_result_empty()
            dataset.update(service_keys)
            dataset['OWNER']=i['OWNER']
            dataset['TITLE']=i['TITLE']
            dataset['NAME']=i['NAME']
            #check if multiple datasets are found, ege there must be WMS  WFS or WMTS if lst_layers is bigger
            
            for j in range(len(lst_layers)):
                #check if multiple datasets are found, ege there must be WMS  WFS or WMTS if lst_layers is bigger
                if "layers=WMS" in dataset['MAPGEO']:
                    dataset['MAPGEO']=dataset['MAPGEO']
                elif "layers=WMS" in lst_layers[j]['MAPGEO']:
                    dataset['MAPGEO']=lst_layers[j]['MAPGEO']
                elif "layers=WMTS" in lst_layers[j]['MAPGEO']:
                    dataset['MAPGEO']=lst_layers[j]['MAPGEO']
                dataset['ABSTRACT']=lst_layers[j]['ABSTRACT'] if lst_layers[j]['ABSTRACT'] != "n.a." else dataset['ABSTRACT']
                dataset['METADATA']=lst_layers[j]['METADATA'] if lst_layers[j]['METADATA'] != "n.a." else dataset['METADATA']
                dataset['CONTACT']=lst_layers[j]['CONTACT'] if lst_layers[j]['CONTACT'] != "n.a." else dataset['CONTACT']
                dataset['KEYWORDS']=lst_layers[j]['KEYWORDS'] if lst_layers[j]['KEYWORDS'] != "n.a." else ""
                dataset['WMSGetCap']=lst_layers[j]['SERVICELINK'] if "wms".casefold() in lst_layers[j]['SERVICETYPE'].casefold() else dataset['WMSGetCap']
                dataset['WMTSGetCap']=lst_layers[j]['SERVICELINK'] if "wmts".casefold() in lst_layers[j]['SERVICETYPE'].casefold() else dataset['WMTSGetCap']
                dataset['WFSGetCap']=lst_layers[j]['SERVICELINK'] if "wfs".casefold() in lst_layers[j]['SERVICETYPE'].casefold() else dataset['WFSGetCap']
            #remove duplicates from keywords
            keywordlist=dataset['KEYWORDS']
            li = list(keywordlist.split(","))
            keywords=list(dict.fromkeys(li))
            dataset['KEYWORDS']=','.join(keywords)

            #writing the datasetfile
            datasetfile_keys=['OWNER','TITLE','NAME','MAPGEO','ABSTRACT','KEYWORDS','CONTACT','WMSGetCap','WMTSGetCap','WFSGetCap']
            datasetfile=dict((k, dataset[k]) for k in datasetfile_keys if k in dataset)
            write_file(datasetfile,output_file)
            
            #writing the simple overview file
            datasetfile_keys=['OWNER','TITLE','MAPGEO']
            datasetfile=dict((k, dataset[k]) for k in datasetfile_keys if k in dataset)
            write_file(datasetfile,output_simple_file)
            
            #add datasetID to lyer done
            geo_data_done.append(checklayer)
    return

def write_dataset_stats(csv_filename,output_file):
    # Read in the data from the CSV file
    data = []
    with open(csv_filename, mode="r", encoding="utf8") as f:
        data = list(csv.DictReader(f, delimiter=",", quotechar='"', lineterminator="\n"))

    # Calculate the number of occurrences of each OWNER
    owner_counts = defaultdict(int)
    for entry in data:
        owner_counts[entry['OWNER']] += 1

    # Calculate the counts and percentages of entries with non-empty fields for each OWNER
    fields = ['KEYWORDS', 'ABSTRACT', 'CONTACT', 'METADATA']
    counts = defaultdict(lambda: defaultdict(int))
    percentages = defaultdict(lambda: defaultdict(float))

    for field in fields:
        for entry in data:
            if entry[field]:
                counts[field][entry['OWNER']] += 1
        for owner, count in counts[field].items():
            percentages[field][owner] = count / owner_counts[owner]

    # Write the results to a CSV file
    with open(output_file, mode="w", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=['OWNER', 'DATASET_COUNT', 'KEYWORDS_COUNT', 'KEYWORDS_MISSING', 'KEYWORDS_PERCENTAGE', 'ABSTRACT_COUNT', 'ABSTRACT_MISSING', 'ABSTRACT_PERCENTAGE', 'CONTACT_COUNT', 'CONTACT_MISSING', 'CONTACT_PERCENTAGE', 'METADATA_COUNT', 'METADATA_MISSING', 'METADATA_PERCENTAGE', 'TOTAL_PERCENTAGE'], lineterminator="\n")
        writer.writeheader()
        for owner in owner_counts.keys():
            row = {
                'OWNER': owner,
                'DATASET_COUNT': owner_counts[owner],
            }
            total_percentages = []
            for field in fields:
                percentage = percentages[field].get(owner, None)
                if percentage is not None:
                    percentage = "{:.1%}".format(percentage)
                    total_percentages.append(percentages[field][owner])
                else:
                    percentage = "0%"
                row[field + '_COUNT'] = counts[field].get(owner, 0)
                row[field + '_MISSING'] = owner_counts[owner] - counts[field].get(owner, 0)
                row[field + '_PERCENTAGE'] = percentage
            row['TOTAL_PERCENTAGE'] = "{:.1%}".format(mean(total_percentages))
            writer.writerow(row)
    return

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
        if test_server(source) == True :

            #GetInfo From services per layer
            get_service_info(source)
            


        else:
            logger.info(source['Description']+" with "+source['URL']+" aborted")
    #Create dataset view and stats
    print("Creating dataset files ...") 
    try:
        os.remove(config.GEODATA_CH_CSV)
        os.remove(config.GEODATA_SIMPLE_CH_CSV)
        os.remove(config.GEOSERVICES_STATS_CH_CSV)
    except OSError:
        pass
    write_dataset_info(config.GEOSERVICES_CH_CSV,config.GEODATA_CH_CSV,config.GEODATA_SIMPLE_CH_CSV)
    write_dataset_stats(config.GEOSERVICES_CH_CSV,config.GEOSERVICES_STATS_CH_CSV)

    print("scraper completed")    
    logger.info("scraper completed")
