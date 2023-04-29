# -*- coding: utf-8 -*-
"""
Title: Scraper a.k.a Geoharvester
Author: David Oesch
Date: 2022-11-05
Purpose: Retrieve information about a web map service and save it to a file
Notes:
- Uses Python 3.9
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
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest
import httplib2
import json

# globals
sys.path.insert(0, config.SOURCE_SCRAPER_DIR)

service_keys = (("WMSGetCap", "n.a."),
                ("WMTSGetCap", "n.a."), ("WFSGetCap", "n.a."))


def service_result_empty():
    """
    This function creates a dictionary object with default values for various
    service related fields.

    The default values are represented by the string "n.a." and are used as
    placeholders until actual data is available.

    The fields in the dictionary include:
    OWNER, TITLE, NAME, MAPGEO, TREE, GROUP, ABSTRACT, KEYWORDS, LEGEND,
    CONTACT, SERVICELINK, METADATA, UPDATE, LEGEND, SERVICETYPE, MAX_ZOOM,
    CENTER_LAT, CENTER_LON, MAPGEO, BBOX.

    Returns:
        A dictionary object with default values for various service related
        fields.

    """
    SERVICE_RESULT = {"OWNER": "n.a.", "TITLE": "n.a", "NAME": "n.a",
                      "MAPGEO": "n.a.", "TREE": "n.a.", "GROUP": "",
                      "ABSTRACT": "n.a", "KEYWORDS": "n.a.", "LEGEND": "n.a.",
                      "CONTACT": "n.a.", "SERVICELINK": "n.a.",
                      "METADATA": "n.a.", "UPDATE": "n.a.", "LEGEND": "n.a.",
                      "SERVICETYPE": "n.a.", "MAX_ZOOM": "n.a.",
                      "CENTER_LAT": "n.a.", "CENTER_LON": "n.a.",
                      "MAPGEO": "n.a.", "BBOX": "n.a."}
    return SERVICE_RESULT


def get_version(input_url):
    """
    Retrieve the version attribute from an XML response from a geoservice at
    the input URL.

    Parameters:
    input_url (str): URL to retrieve XML data from.

    Returns:
    str or None: The version attribute value or None if not found.
    """
    response = requests.get(input_url)
    xml_data = response.content

    root = ET.fromstring(xml_data)
    try:
        version = root.attrib["version"]
    except KeyError:
        print("version attribute not found.")
        version == None
    return (version)


def write_file(input_dict, output_file):
    """
    Write a dictionary to a CSV file. If the file exists, the data is appended
    to it. If the file does not exist, a new file is created with a header.

    Parameters:
    input_dict (dict): Dictionary to be written to file.
    output_file (str): Path of the output file.

    Returns:
    None
    """
    append_or_write = "a" if os.path.isfile(output_file) else "w"

    with open(output_file, append_or_write, encoding="utf-8") as f:
        dict_writer = csv.DictWriter(f, fieldnames=list(input_dict.keys()),
                                     delimiter=",", quotechar='"',
                                     lineterminator="\n")
        if append_or_write == "w":
            dict_writer.writeheader()

        dict_writer.writerow(input_dict)

    return


def load_source_collection():
    """Function to open the file of sources and to load all
    sources  into a list of dicts where each list entry corresponds
    to an individual source (an individual line in the data file).
    Load a collection of sources from a CSV file into a list of dictionaries.

    Returns:
    list: A list of dictionaries, where each dictionary represents a source.
    """
    with open(config.SOURCE_COLLECTION_CSV, mode="r", encoding="utf8") as f:
        sources = list(csv.DictReader(f, delimiter=",",
                                      quotechar='"', lineterminator="\n"))
    return sources


def test_server(source):
    """
    Test if a server is online and reachable.

    Parameters:
    source (dict): A dictionary with GetCapabilities source parameters,
        including 'URL'.

    Returns:
    bool: True if the server is online, False otherwise.
    """
    server_operator = source['Description']
    server_url = source['URL']
    try:
        request = requests.get(server_url)
        if request.status_code == 200:
            success = True
        else:
            success = False
            error_details = ("GET requested yielded HTTP response status "
                             "code %s" % request.status_code)
    except Exception as e_request:
        success = False
        error_details = e_request
        logger.info("%s %s: %s" % (server_operator, server_url, e_request))

    # If there has been a problem, add the details to the operator's error
    # log file
    if not success:
        log_file_name = "%s_error.txt" % server_operator
        log_file_path = os.path.join(config.DEAD_SERVICES_PATH, log_file_name)
        error_log = "%s %s: %s" % (server_operator, server_url, error_details)
        with open(log_file_path, "a+") as f:
            f.write(error_log + "\n")

        print(error_log)
    return success


def get_service_info(source):
    """
    Extracts information from an OGC web service (WMS, WMTS, WFS) using the 
    OWSLib library. This function takes a dictionary called "source" as input 
    and runs an OGC GetCapabilities extraction. The function tries to determine 
    if the service is a Web Map Service (WMS), Web Map Tile Service (WMTS), or 
    Web Feature Service (WFS) based on the version number in the source URL. If 
    the version number is invalid, the function writes an error message to a 
    log file.

    The function then creates a service object using either WebMapService, 
    WebMapTileService, or WebFeatureService from the OWSLib library. The 
    function then loops through all the layers in the service contents and 
    checks if the layer is a parent or child layer. For each layer, the function 
    calls write_service_info to write the service information and layer tree.

    If an error occurs, the function writes an error message to a log file and 
    returns False.

    Parameters:
        source (dict): A dictionary containing the GetCapabilities URL and 
        Description of the OGC web service.

    Returns:
        None
    """

    try:
        # Testing if WMS or WMTS/WFS
        # test for specific Version for service whcih needs to be passed to
        # OWSLIB
        source_version = get_version(source['URL'])
        match = re.match(r"^\d+\.\d+\.\d+$", source_version)
        if match:
            source_version == source_version
        else:
            log_file = open(os.path.join(config.DEAD_SERVICES_PATH,
                            source['Description']+"_error.txt"),  'a+')
            log_file.write(
                source['Description']+": "+"invalid service version number, trying default"+"\n")
            log_file.close()
            logger.info(source['Description']+": " +
                        "invalid service version number, trying default")
            source_version == None
        # if source['Description'] in config.SOURCE_COLLECTION_VERSION:
        #   source_version=config.SOURCE_COLLECTION_VERSION[source['Description']]
        # else:
        #   source_version=None

        # breakpoint()
        try:
            service = WebMapService(source['URL']) if source_version == None else WebMapService(
                source['URL'], version=source_version)
            child = True  # assuming that wms can child/parent relation
        except:
            child = False  # assuming that wmts can't have child/parent relation
            try:
                service = WebMapTileService(source['URL'])
            except:
                service = WebFeatureService(source['URL'], version='2.0.0') if source_version == None else WebFeatureService(
                    source['URL'], version=source_version)
            child = False  # assuming that wmts can't have child/parent relation

        # extract all layer names
        layers = list(service.contents)
        layers_done = []
        for i in layers:
            # check if we did not yet have processed that layer as child before
            # breakpoint()
            if i not in layers_done:
                # print(i+" processing...")

                if child == True:
                    children = len(service.contents[i].children)
                else:
                    children = 0
                # breakpoint()

                # get root layer / extracting the description for simple layer
                if service.contents[i].id not in layers_done:
                    # Some root WMS layers are blocked so no get map is
                    # possible, so we check if we can load them as TOPIC
                    # (aka al children layer active)
                    if "WMS" in source['URL'] or "wms" in source['URL']:
                        # Even some Root layers do not have titles therfore
                        # skipping as well
                        if service.contents[i].title == None:
                            print(i+"Title is empty, skipping")
                        else:
                            try:
                                # check if root layer is loadable, by trying to
                                # call a Get Map, if it is blocked it will
                                # raise an error
                                service.getmap(layers=[i], srs='EPSG:4326', bbox=(service.contents[i].boundingBoxWGS84[0], service.contents[i].boundingBoxWGS84[1],
                                               service.contents[i].boundingBoxWGS84[2], service.contents[i].boundingBoxWGS84[3]), size=(256, 256), format='image/png', transparent=True, timeout=10)
                                # then extract abstract etc
                                layertree = source['Description']+"/"+service.identification.title+"/"+i.replace(
                                    '"', '') if service.identification.title is not None else source['Description']+"/"+i.replace('"', '')
                                write_service_info(
                                    source, service, (service.contents[i].id), layertree, group=i)
                                layers_done.append(service.contents[i].id)
                            except Exception as e:
                                # Check if the exception indicates that the request was not allowed or forbidden
                                if any([msg in str(e) for msg in service.exceptions]):
                                    print(
                                        i+' GetMap request is blocked for this layer')
                                else:
                                    print(i+' Unknown error:', e)
                    else:
                        layertree = source['Description']+"/"+service.identification.title+"/"+i.replace(
                            '"', '') if service.identification.title is not None else source['Description']+"/"+i.replace('"', '')
                        write_service_info(
                            source, service, (service.contents[i].id), layertree, group=i)
                        layers_done.append(service.contents[i].id)

                # check for parent layer, when yes use  it for tree
                if children > 0:
                    # print(i+" processing parent layer")
                    for j in range(len(service.contents[i].children)):
                        if service.contents[i]._children[j].id not in layers_done:
                            layertree = source['Description']+"/"+service.identification.title+"/"+i.replace(
                                '"', '') if service.identification.title is not None else source['Description']+"/"+i.replace('"', '')
                            # print(str(j)+" "+i+""+service.contents[i]._children[j].id)
                            # breakpoint()
                            write_service_info(
                                source, service, (service.contents[i]._children[j].id), layertree, group=i)
                            layers_done.append(
                                service.contents[i]._children[j].id)

            else:
                print(i+" already processed")

    except Exception as e_request:
        log_file = open(os.path.join(config.DEAD_SERVICES_PATH,
                        source['Description']+"_error.txt"),  'a+')
        log_file.write(source['Description']+": "+str(e_request)+"\n")
        log_file.close()
        logger.info(source['Description']+": "+str(e_request))
        print(e_request)

        return False


def write_service_info(source, service, i, layertree, group):
    """
    Write OGC GetCap results for a service, using a custom or default scraper 
    based on availability.

    Parameters:
    source (dict): Source information.
    service (var): GetCap results.
    i (str): Layer name.
    layertree (str): Tree structure.
    group (str): Group name.

    Returns:
    bool: Returns `True` if the function runs successfully, `False` otherwise.
    """
    # Load Empty parameter list
    layer_data = service_result_empty()

    # print(i)
    try:
        # check if custom scraper is available
        scraper_spec = importlib.util.find_spec(source['Description'])

        # run custom scraper
        if scraper_spec is not None:
            scraper = importlib.import_module(
                source['Description'], package=None)
            layer_data = scraper.scrape(source, service, i, layertree, group,
                                        layer_data, config.MAPGEO_PREFIX)

        # run default scraper
        else:
            # print ("...trying default scraper" )
            scraper = importlib.import_module('default', package=None)
            layer_data = scraper.scrape(source, service, i, layertree, group,
                                        layer_data, config.MAPGEO_PREFIX)

        # Writing the Result file
        write_file(layer_data, config.GEOSERVICES_CH_CSV)

        return True

    except Exception as e_request:
        log_file = open(os.path.join(config.DEAD_SERVICES_PATH,
                        source['Description']+"_error.txt"),  'a+')
        log_file.write(source['Description']+" " +
                       source['URL']+" "+i+": "+str(e_request)+"\n")
        log_file.close()
        logger.info(source['Description']+i+": "+str(e_request))
        print(e_request)
        return False


def write_dataset_info(csv_filename, output_file, output_simple_file):
    """
    Writes the processed data in First Normal Form (NF1) to two output files:
    one with detailed information and one with simple information (title and 
    map geo link). This function reads data from a CSV file and processes it to 
    bring the data into first normal form (NF1) with one entry per dataset. The 
    processed data is then written to two output files.

    Inputs
    csv_filename: the name of the input CSV file
    output_file: the name of the output file for the full dataset information
    output_simple_file: the name of the output file for the simplified dataset 
        information

    Functionality
    1. Store processed dataset IDs in geo_data_done to avoid processing the 
       same dataset multiple times.
    2. Loop over all rows in the CSV file and filter for unique datasets by 
       comparing the TITLE, NAME, and OWNER fields.
    3. For each unique dataset, create a new empty layer using the 
       service_result_empty function and update it with the dataset information.
    4. If there are multiple datasets with the same TITLE, NAME, and OWNER, 
       combine the information from all datasets into a single layer.
    5. Perform post-processing on the dataset information, such as removing 
       duplicates from the KEYWORDS field and updating the service links 
       (WMSGetCap, WMTSGetCap, WFSGetCap) based on the SERVICETYPE and 
       SERVICELINK fields in the CSV file. Write the processed dataset 
       information to the output files using the write_file function, with 
       different keys for each file.
    6. The full dataset information is written to output_file, while a 
       simplified version containing only the OWNER, TITLE, and MAPGEO fields 
       is written to output_simple_file.

    Parameters:
    csv_filename: str
        Path to the source CSV file
    output_file: str
        Path to the output file with detailed information
    output_simple_file: str
        Path to the output file with simple information

    Returns:
    None
    """
    # create an empty list to store already processed  datasetUID
    geo_data_done = []

    # read CSV in dict
    lst = [*csv.DictReader(open(csv_filename, encoding="utf-8"),
                           delimiter=",", quotechar='"', lineterminator="\n")]

    for i in lst:
        # filter for unique ID consisting of TITLE NAME and OWNER
        lst_layers = list(filter(lambda lst: (lst['TITLE'] == i['TITLE']) and (
            lst['NAME'] == i['NAME']) and (lst['OWNER'] == i['OWNER']), lst))

        checklayer = i['OWNER']+"_"+i['TITLE'] + \
            "_"+i['NAME']  # create a datasetUID

        if checklayer not in geo_data_done:
            # get new empty layer
            dataset = service_result_empty()
            dataset.update(service_keys)
            dataset['OWNER'] = i['OWNER']
            dataset['TITLE'] = i['TITLE']
            dataset['NAME'] = i['NAME']
            # check if multiple datasets are found, ege there must be WMS  WFS
            # or WMTS if lst_layers is bigger

            for j in range(len(lst_layers)):
                # check if multiple datasets are found, ege there must be WMS,
                # WFS or WMTS if lst_layers is bigger
                if "layers=WMS" in dataset['MAPGEO']:
                    dataset['MAPGEO'] = dataset['MAPGEO']
                elif "layers=WMS" in lst_layers[j]['MAPGEO']:
                    dataset['MAPGEO'] = lst_layers[j]['MAPGEO']
                elif "layers=WMTS" in lst_layers[j]['MAPGEO']:
                    dataset['MAPGEO'] = lst_layers[j]['MAPGEO']
                dataset['ABSTRACT'] = lst_layers[j]['ABSTRACT'] if lst_layers[j]['ABSTRACT'] != "n.a." else dataset['ABSTRACT']
                dataset['METADATA'] = lst_layers[j]['METADATA'] if lst_layers[j]['METADATA'] != "n.a." else dataset['METADATA']
                dataset['CONTACT'] = lst_layers[j]['CONTACT'] if lst_layers[j]['CONTACT'] != "n.a." else dataset['CONTACT']
                dataset['KEYWORDS'] = lst_layers[j]['KEYWORDS'] if lst_layers[j]['KEYWORDS'] != "n.a." else ""
                dataset['WMSGetCap'] = lst_layers[j]['SERVICELINK'] if "wms".casefold(
                ) in lst_layers[j]['SERVICETYPE'].casefold() else dataset['WMSGetCap']
                dataset['WMTSGetCap'] = lst_layers[j]['SERVICELINK'] if "wmts".casefold(
                ) in lst_layers[j]['SERVICETYPE'].casefold() else dataset['WMTSGetCap']
                dataset['WFSGetCap'] = lst_layers[j]['SERVICELINK'] if "wfs".casefold(
                ) in lst_layers[j]['SERVICETYPE'].casefold() else dataset['WFSGetCap']
            # remove duplicates from keywords
            keywordlist = dataset['KEYWORDS']
            li = list(keywordlist.split(","))
            keywords = list(dict.fromkeys(li))
            dataset['KEYWORDS'] = ','.join(keywords)

            # writing the datasetfile
            datasetfile_keys = ['OWNER', 'TITLE', 'NAME', 'MAPGEO', 'ABSTRACT',
                                'KEYWORDS', 'CONTACT', 'WMSGetCap', 'WMTSGetCap', 'WFSGetCap']
            datasetfile = dict((k, dataset[k])
                               for k in datasetfile_keys if k in dataset)
            write_file(datasetfile, output_file)

            # writing the simple overview file
            datasetfile_keys = ['OWNER', 'TITLE', 'MAPGEO']
            datasetfile = dict((k, dataset[k])
                               for k in datasetfile_keys if k in dataset)
            write_file(datasetfile, output_simple_file)

            # add datasetID to lyer done
            geo_data_done.append(checklayer)
    return


def write_dataset_stats(csv_filename, output_file):
    """
    Processes data from a CSV file and writes summary statistics to an output 
    file.

    The function reads data from a CSV file `csv_filename` and calculates the 
    number of occurrences of each `OWNER` and the counts and percentages of 
    entries with non-empty fields (`KEYWORDS`, `ABSTRACT`, `CONTACT`, 
    `METADATA`) for each `OWNER`.

    The summary statistics are then written to an output file `output_file` in 
    CSV format.

    Parameters:
    - csv_filename (str): The path to the input CSV file
    - output_file (str): The path to the output CSV file

    Returns:
    None
    """
    # Read in the data from the CSV file
    data = []
    with open(csv_filename, mode="r", encoding="utf8") as f:
        data = list(csv.DictReader(f, delimiter=",",
                    quotechar='"', lineterminator="\n"))

    # Calculate the number of occurrences of each OWNER
    owner_counts = defaultdict(int)
    for entry in data:
        owner_counts[entry['OWNER']] += 1

    # Calculate the counts and percentages of entries with non-empty fields for
    # each OWNER
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
        writer = csv.DictWriter(f, fieldnames=[
            'OWNER', 'DATASET_COUNT', 'KEYWORDS_COUNT', 'KEYWORDS_MISSING',
            'KEYWORDS_PERCENTAGE', 'ABSTRACT_COUNT', 'ABSTRACT_MISSING',
            'ABSTRACT_PERCENTAGE', 'CONTACT_COUNT', 'CONTACT_MISSING',
            'CONTACT_PERCENTAGE', 'METADATA_COUNT', 'METADATA_MISSING',
            'METADATA_PERCENTAGE', 'TOTAL_PERCENTAGE'], lineterminator="\n")
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
                row[field + '_MISSING'] = owner_counts[owner] - \
                    counts[field].get(owner, 0)
                row[field + '_PERCENTAGE'] = percentage
            if len(total_percentages) > 0:
                row['TOTAL_PERCENTAGE'] = "{:.1%}".format(
                    mean(total_percentages))
            else:
                row['TOTAL_PERCENTAGE'] = "0%"
            writer.writerow(row)
    return


def publish_urls(credentials):
    """
    Publishes a list of URLs to the Google Indexing API using the provided 
    credentials. 
    See https://www.jcchouinard.com/google-indexing-api-with-python/

    Parameters:
    credentials (google.oauth2.credentials.Credentials): The credentials for 
    accessing the Google Indexing API.

    Returns:
    None: This function does not return any value.

    Raises:
    Any errors or exceptions that occur during the execution of the function 
    will be raised.
    """
    requests = {
        'https://davidoesch.github.io/geoservice_harvester_poc/': 'URL_UPDATED',
        'https://davidoesch.github.io/geoservice_harvester_poc/data/geoservices_stats_CH.csv': 'URL_UPDATED',
        'https://davidoesch.github.io/geoservice_harvester_poc/data/geodata_CH.csv': 'URL_UPDATED'
    }

    SCOPES = ["https://www.googleapis.com/auth/indexing"]
    ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"

    # Authorize credentials
    credentials = credentials
    http = credentials.authorize(httplib2.Http())

    # Build service
    service = build('indexing', 'v3', credentials=credentials)

    def insert_event(request_id, response, exception):
        if exception is not None:
            print(exception)
            logger.info("ERROR updating Google Index API: "+exception)
        else:
            print(response)

    batch = service.new_batch_http_request(callback=insert_event)

    for url, api_type in requests.items():
        batch.add(service.urlNotifications().publish(
            body={"url": url, "type": api_type}))

    batch.execute()

# Main
# --------------------------------------------------------------------


# Initialize the logger
logger = logging.getLogger("scraper LOG")

# Set the logging level to INFO
logger.setLevel(logging.INFO)

# Create a file handler for logging
fh = logging.FileHandler(config.LOG_FILE, "a+", "utf-8")
fh.setLevel(logging.INFO)

# Create a formatter for the log messages
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(fh)

# check if we work local env or in github actions
if os.path.exists(config.JSON_KEY_FILE):
    github = False
    # get google secret
    config.SCOPES
    if os.path.getsize(config.JSON_KEY_FILE) > 0:
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            config.JSON_KEY_FILE, scopes=config.SCOPES)
        credentials_valid = True
    else:
        credentials_valid = False
else:
    github = True
    client_secret = os.environ.get('CLIENT_SECRET')
    client_secret = json.loads(client_secret)
    client_secret_str = json.dumps(client_secret)
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(client_secret_str), scopes=config.SCOPES)
    credentials_valid = True

if __name__ == "__main__":
    """
    This code block is the main function of the script. It performs the 
    following operations:

    1 Clean up: Deletes previous log files and scraped data.
    2 Load sources: Calls the load_source_collection function to get a list of 
      sources to scrape.
    3 For each source:
        a. Check if a scraper exists for the source. If not, it sets a message 
           indicating that the default scraper will be used.
        b. Prints and logs a message indicating the start of the scraper for 
           the source.
        c. Calls the test_server function to check if the server is online.
        d. If the server is online, calls the get_service_info function to get 
           information from the service.
        e. If the server is not online, logs a message indicating the scraper 
           was aborted.
    4 Create dataset view and stats: Calls the write_dataset_info and 
      write_dataset_stats functions to generate the dataset files.
    5 Logs and prints a message indicating that the scraper has completed.
    """
    # Clean up
    try:
        os.remove(config.GEOSERVICES_CH_CSV)
        fileList = glob.glob(os.path.join(
            config.DEAD_SERVICES_PATH, "*_error.txt"))
        for filePath in fileList:
            os.remove(filePath)
    except OSError:
        pass

    # Load sources
    sources = load_source_collection()

    for source in sources:

        # check if scraper exists for source
        if os.path.isfile(os.path.join(config.SOURCE_SCRAPER_DIR,
                                       source['Description'])+".py") == True:
            scraper_info = ""
        else:
            scraper_info = "trying DEFAULT scraper "

        print("Starting scraper  %s" %
              source['Description']+" with "+source['URL']+" "+scraper_info)
        logger.info("Starting scraper  %s" %
                    source['Description']+" with "+source['URL']+" "+scraper_info)
        # Is server online?
        if test_server(source) == True:

            # GetInfo From services per layer
            get_service_info(source)

        else:
            logger.info(source['Description']+" with " +
                        source['URL']+" aborted")
    # Create dataset view and stats
    print("Creating dataset files ...")
    try:
        os.remove(config.GEODATA_CH_CSV)
        os.remove(config.GEODATA_SIMPLE_CH_CSV)
        os.remove(config.GEOSERVICES_STATS_CH_CSV)
    except OSError:
        pass
    write_dataset_info(config.GEOSERVICES_CH_CSV,
                       config.GEODATA_CH_CSV, config.GEODATA_SIMPLE_CH_CSV)
    write_dataset_stats(config.GEOSERVICES_CH_CSV,
                        config.GEOSERVICES_STATS_CH_CSV)

    # Bublish to Google  Index API
    if credentials_valid:
        publish_urls(credentials)
    else:
        logger.info(" Google Indexing API not updated, non valid json (0KB)")

    print("scraper completed")
    logger.info("scraper completed")
