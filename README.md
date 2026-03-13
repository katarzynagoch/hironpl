# HiRoN-PL: Network of motorways and expressways in Poland attributed with the date of commissioning (1936-2023)
HiRoN-PL (Network of motorways and expressways in Poland attributed with the date of commissioning) is a vector dataset representing the spatial and temporal development of motorways and expressways in Poland from 1936 to 2023.

Road geometry is derived from OpenStreetMap (OSM) data. The road network was extracted by selecting all OSM way objects with highway=* tags corresponding to high-speed road classes, namely: motorway, motorway_link, and selected trunk roads functionally equivalent to expressways. OSM road geometries were further processed to ensure topological continuity at junctions and to align road sections with road crossings and distinct construction or commissioning phases derived from the authoritative data. 

Original OSM identifiers and highway tags are preserved to ensure traceability. Each road segment has a unique internal identifier, and its length in meters is provided as a derived attribute.

## Processing logic
The main logic behind the script `osm_motorways_enriched.py` is to adjust the geometry of the OSM data representing high speed roads to authoritative data. These two datasets differ in several ways. The OSM data is of higher spatial detail than the auth data, e.g. OSM highways usually contain two carriageways, while auth data is a single centerline. On the other hand, auth data geometry is adjusted to the commissioning phases. The auth data is of higher thematic detail, most importntly it contains road construction dates.

We combine these two datasets into one dataset based on OSM geometry but attributed with the auth data. To do so, we select from the OSM road data sections that are within a given dstance to the auth road data and with a similar azimuth (angle). The start and end points of the OSM data are adjusted to the auth data, to align the position of section nodes (place them as close as possible). Lastly, the auth data attributes are assigned to the corresponding OSM sections.

Three key parameters are used:
- MAX_DISTANCE: a maximum distance [m] between authoritative data centreline and osm carriageways
- MAX_AZIMUTH_DIFF: a maximum angle [degrees] between auth and osm sections
- BUFFER: a buffer [m] around auth sections to select osm 'trunk' roads (in addition to defualt 'motorway' roads)

**The process goes as follows:**
1. From OSM dump select high speed roads: motorways, motorway links and trunk roads
2. OSM semantics are not always consistent with the national road categories. By defualt we use OSM 'motorway' and 'motorway_links' road sections. Additionally we also use the 'trunk' road sections that are close to the the auth data. We combine them into out baseline OSM data.
3. We assign to the OSM data positions of the section end points of the corresponding auth road sections. First we select the OSM road sections that are nearby auth road sections (< MAX_DISTANCE) and are more less parallel (<MAX_AZIMUTH_DIFF).
4. Then we assign the auth end point positions to the selected OSM sections. We split the selected OSM data using the endpoint to resemble the geometry of the auth sections.
5. For each new (split) OSM section, attrbutes from the nearest (< MAX_DISTANCE) auth road sections are assigned: node names, date of construction and auth ID.
6. In the post-processing the motorway_links are checked: a motorway_link should be assign consistent attributes from the nearest and *newest* auth road section. Without this step, links are assigned more than one date of commissioning, which is not plausible.
7. The end.












