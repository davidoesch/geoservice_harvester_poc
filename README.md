[![GitHub commit](https://img.shields.io/github/last-commit/davidoesch/geoservice_harvester_poc)](https://github.com/davidoesch/geoservice_harvester_poc/commits/master)

# Geoservice Harvester POC  open geo services reported by the Swiss Gov Agencies and Third parties

### Important note
> Find and use **high quality data published by our data colleagues of the [SWISS FEDERAL ADMINSTRATION](https://www.geo.admin.ch) [CANTONS](https://www.geodienste.ch)** for all Cantons and FL:
> 1. GeoServiceHarvesterPOC visualized (Dashboard): https://davidoesch.github.io/geoservice_harvester_poc
> 2. geo.admin.ch visualized (Dashboard): https://docs.google.com/spreadsheets/d/1QdxYv6RYWe9PFIq5XQ-BNLnKfgtFcDkfZ58ftZ_Va9I/edit?usp=sharing
> 3. all published as 'open government data': https://opendata.swiss/de/dataset/?groups=geography

## Aim of this repository

The aim of this repository is to provide a POC to open OGC Compliant geodata services  provided by the Swiss Confederation, Cantons Municipalities, the Principality of Liechtenstein and third parties. Inspired by the pre-POC [wmsChecker](https://github.com/davidoesch/wmschecker) and driven by the [ 4th Geounconference Workshop: Sujet / Thema 16 –– Service-Verzeichnis](https://github.com/GeoUnconference/discussions/discussions/38). For key findings, dive into the [ blog post](https://www.linkedin.com/pulse/geoharvesting-unexploiting-seo-treasures-geoservices-david-oesch/). Updates of services are infrequent.

If you have any questions, please don't hestitate to contact us: <br>
- https://twitter.com/davidoesch (follow us, we send you a private Direct Message, thanks!) <br>

## Datasets of all services : geoservices_CH.csv

**General description** <br>
This data is generated and validated daily using automated procedures. Note that we only publish data that are OGC compliant. Thus, gaps might be the case. 

**Data** <br>

>**https://github.com/davidoesch/geoservice_harvester_poc/blob/main/data/geoservices_CH.csv** <br>
>*Description:* Data description for each layer separately  <br>
>*Spatial unit:* Swiss cantons and Principality of Liechtenstein covered <br>
>*Updated:* daily <br>
>*Format:* csv <br>
>*Additional remark*: )

| Field Name  | Description                                                                                                      | Format                      | Note                        |
| ----------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------- | --------------------------- |
| OWNER       | Both Owner type and Owner Name are reflected,they corespond as well to the corrsponing py file with scraper info | Text <OwnerType\_OwnerName> |                             |
| TITLE       | Title of the dataset                                                                                             | Text                        |                             |
| NAME        | Name of the dataset                                                                                              | Text                        |                             |
| TREE        | Layertree derived from service info                                                                              | Text , tree separator „/“   |                             |
| GROUP       | Group Name of agreggated datasets                                                                                | Text                        | only applicable for WMS     |
| ABSTRACT    | Abstract                                                                                                         | Text                        |                             |
| KEYWORDS    | Keywords                                                                                                         | keywords, commaseparated    |                             |
| LEGEND      | Legend                                                                                                           | URL to Image                |                             |
| CONTACT     | Contact info                                                                                                     | Text, email                 |                             |
| SERVICELINK | Link to Get Capabilities                                                                                         | URL to Image                |                             |
| METADATA    | Link to Metadata                                                                                                 | URL                         |                             |
| UPDATE      | Publication Date                                                                                                 | Text                        |                             |
| SERVICETYPE | OGC Service type                                                                                                 | Text                        | WMTS WMS and STAC           |
| MAX ZOOM    | Zoom level (mapzoom) on which the data is visible                                                                | Int                         | Currently set to 7 globally |
| CENTER\_LAT | Lat center of data WGS84                                                                                         | Float                       |                             |
| CENTER\_LON | Lon center of data WGS84                                                                                         | Float                       |                             |
| MAPGEO      | permalink to map.geo.admin.ch                                                                                    | URL                         |                             |

## Unified data : geodata_CH.csv

**General description** <br>
This data is generated and validated daily using automated procedures based on geoservices_CH.csv (1NF / normalization). Note that we only publish data that are OGC compliant. Thus, gaps might be the case. 

**Data** <br>

>**https://github.com/davidoesch/geoservice_harvester_poc/blob/main/data/geodata_CH.csv** <br>
>*Description:* This dataset has been aggregated to include data from all of its different services. This means that the information is now more comprehensive and includes all relevant occurrences from each of the services that contribute to the dataset. <br>
>*Spatial unit:* Swiss cantons and Principality of Liechtenstein covered <br>
>*Updated:* daily <br>
>*Format:* csv <br>
>*Additional remark*: )

| Field Name  | Description                                                                                                      | Format                      | Note                        |
| ----------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------- | --------------------------- |
| OWNER       | Both Owner type and Owner Name are reflected,they corespond as well to the corrsponing py file with scraper info | Text <OwnerType\_OwnerName> |                             |
| TITLE       | Title of the dataset                                                                                             | Text                        |                             |
| NAME        | Name of the dataset                                                                                              | Text                        |                             |
| MAPGEO      | permalink to map.geo.admin.ch                                                                                    | URL                         |                             |
| CONTACT     | Contact info                                                                                                     | Text, email                 |                             |
| WMSGetCap | Link to WMSGetCap      | Link                        |            |
| WMTSGetCap | Link to WMTSGetCap      | Link                        |            |
| WFSGetCap | Link to WFSGetCap      | Link                        |            |


## Dataset title : geodata_simple_CH.csv

**General description** <br>
This data is generated and validated daily using automated procedures based on geodata_CH.csv. Note that we only publish data that are OGC compliant. Thus, gaps might be the case. 

**Data** <br>

>**https://github.com/davidoesch/geoservice_harvester_poc/blob/main/data/geodata_simple_CH.csv** <br>
>*Description:* This dataset  contains only the title of the datset and a link to map.geo.admin.ch. (no link if only WFS is availbale) . It's sole pupose is to serve as source for https://davidoesch.github.io/geoservice_harvester_poc <br>
>*Spatial unit:* Swiss cantons and Principality of Liechtenstein covered <br>
>*Updated:* daily <br>
>*Format:* csv <br>
>*Additional remark*: )

| Field Name  | Description                                                                                                      | Format                      | Note                        |
| ----------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------- | --------------------------- |
| OWNER       | Both Owner type and Owner Name are reflected,they corespond as well to the corrsponing py file with scraper info | Text <OwnerType\_OwnerName> |                             |
| TITLE       | Title of the dataset                                                                                             | Text                        |                             |
| MAPGEO      | permalink to map.geo.admin.ch                                                                                    | URL                         | in case of a WFS only: link will not work

## How to add additonal WMS WMTS Services
1. Add your service to [sources.csv](https://github.com/davidoesch/geoservice_harvester_poc/sources.csv) follwoing the OWNER Naming Convention and URL (only https) to the service endpoint
2. copy the [default](https://github.com/davidoesch/geoservice_harvester_poc/scraper/default.py) scraper configuration file, rename it based on the OWNER Naming Convention in 1.)
3. Adapt the scraper configuration file. Recommended procedure: Add a breakpoint on the first run, follow your nose to find the correct keys.Don't add parameters
4. Pray

## Current status Provider & Services

| Provider 	| Status 	| Notes 	|
|:---------:	|--------	|-------	|
|     AG    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS 'ok')      	|      	|
|     AI    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')       	| some layers do cover AI AR SG      	|
|     AR    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')       	| some layers do cover AI AR SG      	|
|     BE    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS 'ok')      	|   FR  to be done   	|
|     BL    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WMTS 'ok')      	|      	|
|     BS    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS-WMTS 'ok')      	|      	|
|     FR    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')      	|      	|
|     GE    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS 'ok')      	|  3 datasets can not be parsed, see error log in /tools     	|
|     GL    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')      	|  Drops WFS warnings, seems to be ok see error log in /tools     	|
|     GR    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')      	|      	|
|     JU    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS-WMTS 'ok')      	| no love for WebmerCator     	|
|     LU    	|  ![ok](https://placehold.jp/de77ae/000000/200x50.png?text=no-service 'ok')        	|     	|
|     NE    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS 'ok')       	|       	|
|     NW    	|  ![ok](https://placehold.jp/de77ae/000000/200x50.png?text=no-service 'ok')      	| |
|     OW    	|  ![ok](https://placehold.jp/de77ae/000000/200x50.png?text=no-service 'ok')      	|         	|
|     SG    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS-WMTS 'ok')      	|       	|
|     SH    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')       	|       	|
|     SO    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS-WMTS 'ok')      	|      	|
|     SZ    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS-WMTS 'ok')      	|      	|
|     TG    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')       	|       	|
|     TI    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS-WMTS 'ok')      	|      	|
|     UR    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')       	|       	|
|     VD    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS 'ok')      	|      	|
|     VS    	|  ![ok](https://placehold.jp/de77ae/000000/200x50.png?text=no-service 'nok')      	|   |
|     ZG    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS-WMTS 'ok')      	|      	|
|     ZH    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')       	|       	|
|     LI    	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS 'ok')        	|       	|
|     Geodienste |![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WFS 'ok')   	|  FR IT  to be done       	|       	
|     Bund   	|  ![ok](https://placehold.jp/b8e186/000000/200x50.png?text=WMS-WMTS 'ok')   	|  FR IT EN RM to be done       	|   



## Operation
Automated daily run of [scraper.py](https://github.com/davidoesch/geoservice_harvester_poc/scraper.py) via GithubAction [scheduler](https://github.com/davidoesch/geoservice_harvester_poc/blob/main/.github/workflows/scheduler-scraper.yml). The scraper results are logged in [debug.log](https://github.com/davidoesch/geoservice_harvester_poc/blob/main/tools/debug.log), faulty or offline services in [sources.csv](https://github.com/davidoesch/geoservice_harvester_poc/blob/main/sources.csv) are logged in [tools](https://github.com/davidoesch/geoservice_harvester_poc/tree/main/tools). Harvested data in [geoservices_CH.csv](https://github.com/davidoesch/geoservice_harvester_poc/blob/main/data/geoservices_CH.csv)

## Roadmap and Ideas
Are collected in [Issues](https://github.com/davidoesch/geoservice_harvester_poc/issues)


