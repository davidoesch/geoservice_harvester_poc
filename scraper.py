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
import pytz
from datetime import datetime, timezone

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
        logger.warn("%s: Version attribute not found" % (input_url))
        version = None
    return version


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
        sources = csv.DictReader(f, delimiter=",", quotechar='"',
                                 lineterminator="\n")
        sources = list(sources)
    return sources


def is_online(source):
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
        log_to_operator_csv(server_operator, server_url, error_details)
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
    server_operator = source['Description']
    server_url = source['URL']

    try:
        # Check if this service has a valid service version number. If not,
        # set version to None (i.e., use default)
        source_version = get_version(source['URL'])
        match = re.match(r"^\d+\.\d+\.\d+$", source_version)
        if not match:
            error_details = "Invalid service version number. Scraper will try the default."
            log_to_operator_csv(server_operator, server_url, error_details)
            logger.info("%s, %s: %s" % (server_operator, server_url,
                                        error_details))
            source_version = None

        # Check if this service is a WMS, a WMTS or a WFS
        service_type = None
        try:
            if source_version is not None:
                service = WebMapService(server_url, version=source_version)
            else:
                service = WebMapService(server_url)
            service_type = "WMS"
            # We assume WMSs can have child/parent relations
            children_possible = True
        except:
            pass

        if service_type is None:
            try:
                service = WebMapTileService(server_url)
                service_type = "WMTS"
                # We assume WMTSs can't have child/parent relations
                children_possible = False
            except:
                pass

        if service_type is None:
            try:
                if source_version is None:
                    service = WebFeatureService(server_url, version='2.0.0')
                else:
                    service = WebFeatureService(server_url,
                                                version=source_version)
                service_type = "WFS"
                # We assume WFSs can't have child/parent relations
                children_possible = False
            except:
                pass

        if service_type is not None:
            # I.e., we have found a valid service endpoint of type WMS, WTMS or
            # WFS
            service_title = service.identification.title

            # Extract all layer names
            layers = list(service.contents)
            layers_done = []
            for i in layers:
                this_layer = service.contents[i].id
                # Check that we have not yet processed this layer as a child of
                # another layer before
                if this_layer not in layers_done:
                    # get root layer / extracting the description for simple layer
                    # Some root WMS layers are blocked so no get map is
                    # possible, so we check if we can load them as TOPIC
                    # (aka al children layer active)
                    if "wms" in server_url.lower():
                        # Even some Root layers do not have titles therfore
                        # skipping as well
                        if service.contents[i].title is None:
                            logger.warn("%s: Title is empty. Skipping." % i)
                        else:
                            try:
                                # check if root layer is loadable, by trying to
                                # call a Get Map, if it is blocked it will
                                # raise an error
                                service.getmap(layers=[i], srs='EPSG:4326',
                                               bbox=(service.contents[i].boundingBoxWGS84[0],
                                                     service.contents[i].boundingBoxWGS84[1],
                                                     service.contents[i].boundingBoxWGS84[2],
                                                     service.contents[i].boundingBoxWGS84[3]),
                                               size=(256, 256), format='image/png',
                                               transparent=True, timeout=10)
                                # Then extract abstract etc
                                if service_title is not None:
                                    layertree = "%s/%s/%s" % (server_operator,
                                                              service_title,
                                                              i.replace('"', ''))
                                else:
                                    layertree = "%s/%s" % (server_operator,
                                                           i.replace('"', ''))

                                write_service_info(source, service,
                                                   this_layer,
                                                   layertree, group=i)
                                layers_done.append(this_layer)
                            except Exception as e:
                                # Check if the exception indicates that the
                                # request was not allowed or forbidden
                                if any([msg in str(e) for msg in service.exceptions]):
                                    logger.error(
                                        "%s: GetMap request is blocked for this layer" % i)
                                else:
                                    logger.error(
                                        "%s: Unknown error: %s" % (i, e))
                    else:
                        if service_title is not None:
                            layertree = "%s/%s/%s" % (server_operator,
                                                      service_title,
                                                      i.replace('"', ''))
                        else:
                            layertree = "%s/%s" % (server_operator,
                                                   i.replace('"', ''))
                        write_service_info(source, service, this_layer,
                                           layertree, group=i)
                        layers_done.append(this_layer)

                    # Check if this layer is parent to child layers. If it is,
                    # check the child layers
                    if children_possible:
                        try:
                            number_children = len(service.contents[i].children)
                        except AttributeError:
                            number_children = 0

                    if children_possible and number_children > 0:
                        for j in range(number_children):
                            this_child_layer = service.contents[i]._children[j].id
                            if this_child_layer not in layers_done:
                                if service_title is not None:
                                    layertree = "%s/%s/%s" % (server_operator,
                                                              service_title,
                                                              i.replace('"', ''))
                                else:
                                    layertree = "%s/%s" % (server_operator,
                                                           i.replace('"', ''))

                                write_service_info(source, service,
                                                   this_child_layer, layertree,
                                                   group=i)
                                layers_done.append(this_child_layer)

                else:
                    # This layer has already been processed
                    pass
        else:
            # Service could not be identified as valid WMS, WMTS or WFS by
            # OWSLib
            error_details = "Service does not seem to be a valid WMS, WMTS or WFS"
            log_to_operator_csv(server_operator, server_url, error_details)
            logger.info("%s, %s: %s" %
                        (server_operator, server_url, error_details))

    except Exception as e_request:
        error_details = str(e_request)
        log_to_operator_csv(server_operator, server_url, error_details)
        logger.info("%s, %s: %s" %
                    (server_operator, server_url, error_details))
        return False


def log_to_operator_csv(server_operator, server_url, error_details):
    CET = pytz.timezone('Europe/Zurich')
    timestamp = datetime.now(timezone.utc).astimezone(CET).isoformat()

    log_file_name = "%s_errors.csv" % server_operator
    log_file_path = os.path.join(config.DEAD_SERVICES_PATH, log_file_name)

    error_log = '%s,%s,%s,"%s"' % (timestamp, server_operator, server_url,
                                   error_details)
    append_or_write = "a" if os.path.isfile(log_file_path) else "w"
    with open(log_file_path, append_or_write, encoding="utf-8") as f:
        if append_or_write == "w":
            f.write("Timestamp,Operator,URL,Issue\n")
        f.write(error_log + "\n")
    return


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
            scraper = importlib.import_module('default', package=None)
            layer_data = scraper.scrape(source, service, i, layertree, group,
                                        layer_data, config.MAPGEO_PREFIX)

        # Writing the Result file
        write_file(layer_data, config.GEOSERVICES_CH_CSV)

        return True

    except Exception as e_request:
        server_operator = source['Description']
        error_details = str(e_request)
        log_to_operator_csv(server_operator, i, error_details)
        logger.error("%s, %s: %s" % (server_operator, i, error_details))
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


def write_operator_stats(out_file):
    """
    Collates error statistics per server operator (if they had errors in this 
    scraper run) based on the files named "*_errors.csv" in 
    <config.DEAD_SERVICES_PATH>. Writes the overview statistics into a 
    markdown file that can comfortably viewed on GitHub

    Parameters:
    out_file: Name of the output markdown file (should end in "*.md" so that 
    GitHub recognizes it as such.

    Returns:
    None: This function does not return any value.

    """
    error_files = glob.glob(os.path.join(
        config.DEAD_SERVICES_PATH, "*_errors.csv"))

    CET = pytz.timezone('Europe/Zurich')
    datestamp = datetime.now(timezone.utc).astimezone(CET).strftime("%d.%m.%Y")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("# Issues found during the last run (%s)\n\n" % datestamp)
        for error_file in error_files:
            server_operator = error_file.replace(
                "_errors.csv", "").replace("tools/", "")
            with open(error_file, "r", encoding="utf-8") as in_file:
                error_data = in_file.readlines()[1:]
            f.write("- %s: [%s issue(s)](%s)\n" %
                    (server_operator, len(error_data), error_file))
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

    # Authorize credentials
    credentials = credentials
    http = credentials.authorize(httplib2.Http())

    # Build service
    service = build('indexing', 'v3', credentials=credentials)

    def insert_event(request_id, response, exception):
        if exception is not None:
            logger.error("Failed to update Google Index API: %s" % exception)
        else:
            print(response)

    batch = service.new_batch_http_request(callback=insert_event)

    for url, api_type in requests.items():
        batch.add(service.urlNotifications().publish(
            body={"url": url, "type": api_type}))

    batch.execute()


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
        c. Calls the is_online function to check if the server is online.
        d. If the server is online, calls the get_service_info function to get 
           information from the service.
        e. If the server is not online, logs a message indicating the scraper 
           was aborted.
    4 Create dataset view and stats: Calls the write_dataset_info and 
      write_dataset_stats functions to generate the dataset files.
    5 Logs and prints a message indicating that the scraper has completed.
    """
    # Initialize and configure the logger
    logger = logging.getLogger("scraper LOG")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(config.LOG_FILE, "w", "utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(filename)s >"
                                  "%(funcName)20s(): Line %(lineno)s - "
                                  "%(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Get the credentials for the Google Index API. The approach depends on
    # whether this script is running on GitHub (via GitHub Actions) or
    # locally. In the latter case you need a valid config.JSON_KEY_FILE in
    # this repo.
    if os.path.exists(config.JSON_KEY_FILE):
        # This script is running locally
        google_credentials = ServiceAccountCredentials.from_json_keyfile_name(
            config.JSON_KEY_FILE, scopes=config.SCOPES)
    else:
        # This script is running on GitHub
        client_secret = os.environ.get('CLIENT_SECRET')
        client_secret = json.loads(client_secret)
        client_secret_str = json.dumps(client_secret)
        google_credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(client_secret_str), scopes=config.SCOPES)

    # Clean up main data file and operator-specific error log files
    try:
        os.remove(config.GEOSERVICES_CH_CSV)
    except OSError as e:
        logger.error("Could not delete %s: %s" %
                     (config.GEOSERVICES_CH_CSV, e))
    error_log_files = glob.glob(os.path.join(
        config.DEAD_SERVICES_PATH, "*_error.csv"))
    for error_log_file in error_log_files:
        try:
            os.remove(error_log_file)
        except OSError as e:
            logger.error("Could not delete %s: %s" % (error_log_file, e))

    # Load sources
    sources = load_source_collection()
    num_sources = len(sources)
    n = 1

    for source in sources:
        server_operator = source['Description']
        server_url = source['URL']
        # Check if a custom scraper exists for this source
        if os.path.isfile(os.path.join(config.SOURCE_SCRAPER_DIR,
                                       "%s.py" % server_operator)):
            scraper_type = "custom"
        else:
            scraper_type = "default"

        status_msg = "Running %s scraper on %s > %s (source %s/%s)" % (
            scraper_type, server_operator, server_url, n, num_sources)
        print(status_msg)
        logger.info(status_msg)

        # Check if this server is online. If yes, proceed to gather
        # information
        if is_online(source):
            get_service_info(source)
        else:
            logger.warn("Scraping %s > %s aborted" % (
                server_operator, server_url))
        n += 1

    # Create dataset view and stats
    print("\nCreating dataset files")
    for f in [config.GEODATA_CH_CSV, config.GEODATA_SIMPLE_CH_CSV,
              config.GEOSERVICES_STATS_CH_CSV]:
        try:
            os.remove(f)
        except OSError as e:
            logger.error("Could not delete %s: %s" % (f, e))

    write_dataset_info(config.GEOSERVICES_CH_CSV,
                       config.GEODATA_CH_CSV, config.GEODATA_SIMPLE_CH_CSV)
    write_dataset_stats(config.GEOSERVICES_CH_CSV,
                        config.GEOSERVICES_STATS_CH_CSV)

    write_operator_stats(config.OPERATOR_STATS_FILE)

    # Publish to Google Index API
    publish_urls(google_credentials)

    print("\nScraper run completed")
    logger.info("Scraper run completed")
