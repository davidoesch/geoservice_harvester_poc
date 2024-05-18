import requests
import csv
import requests
from bs4 import BeautifulSoup

"""
Utility functions for OGC services management.

Functions:
    remove_identical_lines(input_file, output_file): 
        Removes identical lines from a CSV file.
        
    get_ogc_services_for_canton(canton_organization, csv_file, canton_short, rows=1000): 
        Retrieves a list of all WMS, WFS, and WMTS services for a specified canton from the Open Data Swiss API 
        and writes the results to a CSV file.
        
    extract_urls_with_getcapabilities(source_url, csv_file, canton): 
        Extracts URLs containing "GetCapabilities" from a given source URL and stores the results in a CSV file.
"""

def remove_identical_lines(input_file, output_file):
    """
    Removes identical lines from a CSV file.

    Parameters:
        input_file (str): The path to the input CSV file.
        output_file (str): The path to the output CSV file without identical lines.

    Returns:
        None
    # Example usage:
        input_file = "input.csv"
        output_file = "output.csv"
        remove_identical_lines(input_file, output_file)
    """
    # Set to store unique lines
    unique_lines = set()

    # Read input file and store unique lines
    with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        for row in reader:
            unique_lines.add(tuple(row))

    # Write unique lines to output file
    with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        for line in unique_lines:
            writer.writerow(line)





import csv
import requests

def get_ogc_services_for_canton(canton_organization, csv_file, canton_short, rows=1000):
    """
    Retrieves a list of all WMS, WFS, and WMTS services for a specified canton from the Open Data Swiss API
    and writes the results to a CSV file.

    Parameters:
        canton_organization (str): The organization name of the canton to filter datasets (e.g., 'geoinformation_kanton_freiburg').
        csv_file (str): The path to the CSV file to store the results.
        canton_short (str): The abbreviation of the canton.
        rows (int): The number of rows to return. Defaults to 1000.

    Returns:
        None

    Example usage:
        canton_organization = 'geoinformation_kanton_freiburg'
        csv_file = "ogc_services.csv"
        canton_short = "KT_FR"
        get_ogc_services_for_canton(canton_organization, csv_file, canton_short, rows=1000)    
    """
    url = "https://ckan.opendata.swiss/api/3/action/package_search"
    params = {
        'fq': f'organization:{canton_organization} AND (res_format:WMS OR res_format:WFS OR res_format:WMTS)',
        'rows': rows
    }

    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Error {response.status_code}: {response.text}")

    data = response.json()
    ogc_services = []

    for result in data['result']['results']:
        for resource in result['resources']:
            if resource['format'].lower() in ['wms', 'wfs', 'wmts']:
                ogc_services.append({
                    'title': result['title'],
                    'url': resource['url'],
                    'format': resource['format'],
                    'description': result.get('notes', ''),
                })

    # Write the data to the CSV file
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(["Canton", "URL"])  # Write the header row
        for service in ogc_services:
            writer.writerow([canton_short, service["url"]])



def extract_urls_with_getcapabilities(source_url, csv_file, canton):
    """
    Extracts URLs containing "GetCapabilities" from a given source URL and stores the results in a CSV file.

    Parameters:
        source_url (str): The URL to parse and extract URLs from.
        csv_file (str): The path to the CSV file to store the results.
        canton (str): The canton abbreviation.

    Returns:
        None

    Example usage:
        source_url = "https://zg.ch/de/planen-bauen/geoinformation/geoinformationen-nutzen/geoinformationen-von-a-bis-z#WThemenkatalog"
        csv_file = "ogc_services.csv"
        canton = "KT_ZG"
        extract_urls_with_getcapabilities(source_url, csv_file, canton)    
    """
    # Fetch the HTML content of the page
    response = requests.get(source_url)

    # Parse the HTML content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract all URLs containing "GetCapabilities"
    urls_with_get_capabilities = [link.get('href') for link in soup.find_all('a', href=True) if 'GetCapabilities' in link.get('href')]

    # Write the data to the CSV file
    with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(["Canton", "URL"])  # Write the header row
        for url in urls_with_get_capabilities:
            writer.writerow([canton, url])


