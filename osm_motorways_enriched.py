# -*- coding: utf-8 -*-
"""
Created on Wed Jan 21 15:02:56 2026

@author: Katarzyna Krasnodębska
"""

import geopandas as gpd
# import shapely
from shapely.geometry import Point
from shapely.ops import substring
from collections import defaultdict
import os
import numpy as np
import networkx as nx

# Parameters
MAX_DISTANCE = 1000.0     # max distance [m] between authoritative data centreline and osm carriageways
MAX_AZIMUTH_DIFF = 30.0   # max angle [degrees] between auth and osm sections (set to None to disable)
EPS = 1e-6                # numeric tolerance
BUFFER = 40.0             # buffer [m] around auth sections to select osm 'trunk' roads (additionally to 'motorway' roads)

# Data paths
root = 'C:\\PROCESSING\\2025_Multitemporal_highways_Poland'
result_dir = "results_v1_0"
auth = gpd.read_file(os.path.join(root,'motorways_expressroads_Poland',"poland_2023_motorways-expressroads_2180.gpkg")).to_crs(2180)
# Assign ID to auth dataframe 
auth = auth.reset_index().rename(columns={"index": "auth_id"})

# OSM motorways with links and trunk roads. Tun below lines in terminal:
#osmium tags-filter poland-260118.osm.pbf w/highway=motorway,motorway_link,trunk -o poland-260118_motorway_motorwaylink_trunk.osm.pbf --overwrite
#ogr2ogr -f GPKG poland-260118_motorway_motorwaylink_trunk.gpkg poland-260118_motorway_motorwaylink_trunk.osm.pbf -oo OSM_CONFIG_FILE=osmconf.ini -lco GEOMETRY_NAME=geom -lco FID=id lines
#ogr2ogr -t_srs EPSG:2180 poland-260118_motorway_motorwaylink_trunk_2180.gpkg poland-260118_motorway_motorwaylink_trunk.gpkg lines
osm_all = gpd.read_file(os.path.join(root,'osm_Poland',"poland-260118_motorway_motorwaylink_trunk_2180.gpkg")).to_crs(2180)

# Helper functions
def line_azimuth(line):
    coords = list(line.coords)
    if len(coords) < 2:
        return None
    x1, y1 = coords[0]
    x2, y2 = coords[-1]
    angle = np.degrees(np.arctan2(x2 - x1, y2 - y1))
    return abs(angle) % 180

# Angular difference (0–90°)
def azimuth_diff(a1, a2):
    diff = abs(a1 - a2) % 180
    return min(diff, 180 - diff)

def clean_positions(pos_set, eps=EPS):
    pos = sorted(pos_set)
    cleaned = []
    for p in pos:
        if p <= eps or p >= 1 - eps:
            continue
        if not cleaned or abs(p - cleaned[-1]) > eps:
            cleaned.append(p)
    return cleaned



# Buffer authoritative highway data by 40 m
auth_buff = gpd.GeoDataFrame(
    auth[["auth_id"]].copy(),
    geometry=auth.buffer(BUFFER, cap_style="square", join_style="mitre"),
    crs=auth.crs
)

# auth_buff.to_file(
#     os.path.join(root,'motorways_expressroads_Poland',"TEST_auth_buffer_40m.gpkg"),
#     layer="test_buffer",
#     driver="GPKG"
# )
# Not all of the trunk roads are relevent, therefore
# select only the trunk roads that are inside the buffer around the auth data
trunk = osm_all[osm_all.highway == "trunk"].copy()
trunk_buff = gpd.sjoin(
    trunk,
    auth_buff,
    how="inner",
    predicate="intersects"
)
# trunk_buff.to_file(
#     os.path.join(root,'osm_Poland',"TEST_trunk_roads.gpkg"),
#     layer="test_buffer",
#     driver="GPKG"
# )

# Now join the selected trunk roads with motorways and motorway links
idx_motorways = osm_all.index[
    osm_all.highway.isin(["motorway", "motorway_link"])
]
idx_trunk = trunk_buff.index
idx_main = idx_motorways.union(idx_trunk)

# Create the OSM data that you want to enrich with the auth attributes
osm = osm_all.loc[idx_main].copy()

# osm.to_file(
#     os.path.join(root,'osm_Poland',"TEST_selected_roads.gpkg"),
#     layer="test_buffer",
#     driver="GPKG"
# )

# precompute azimuths for both OSM and auth data (avoids recomputation)
auth["azimuth"] = auth.geometry.apply(line_azimuth)
osm["azimuth"] = osm.geometry.apply(line_azimuth)

split_positions = defaultdict(set)
section_index = defaultdict(list)

# Assign to OSM data auth road segment endpoints
for sec_id, sec in auth.iterrows():
    sec_geom = sec.geometry
    sec_az = sec.azimuth

    # spatial pre-filter
    candidates = osm[osm.geometry.distance(sec_geom) < MAX_DISTANCE]

    for osm_idx, osm_row in candidates.iterrows():
        osm_geom = osm_row.geometry

        # optional azimuth filter
        if MAX_AZIMUTH_DIFF is not None:
            if sec_az is None or osm_row.azimuth is None:
                continue
            if azimuth_diff(sec_az, osm_row.azimuth) > MAX_AZIMUTH_DIFF:
                continue

        # project authoritative endpoints onto OSM geometry
        for pt in [sec_geom.coords[0], sec_geom.coords[-1]]:
            proj = osm_geom.project(Point(pt), normalized=True)
            split_positions[osm_idx].add(proj)

        # remember association for attribute assignment
        section_index[osm_idx].append(sec_id)

segments = []

# Now split the OSM to match the auth segments
for osm_idx, osm_row in osm.iterrows():
    line = osm_row.geometry
    pos = clean_positions(split_positions.get(osm_idx, set()))

    cuts = [0.0] + pos + [1.0]

    for i in range(len(cuts) - 1):
        geom = substring(line, cuts[i], cuts[i + 1], normalized=True)

        if geom.length < 1.0:  # avoid slivers
            continue

        segments.append({
            "osm_id": osm_row.osm_id,
            "highway": osm_row.highway,
            "geometry": geom
        })

segments_gdf = gpd.GeoDataFrame(segments, crs=osm.crs)
segments_gdf["midpoint"] = segments_gdf.geometry.interpolate(0.5, normalized=True)

# Join the OSM data adjusted to auth segments with the nearest auth segments
enriched = gpd.sjoin_nearest(
    segments_gdf.set_geometry("midpoint"),
    auth,
    how="left",
    max_distance=MAX_DISTANCE
)

enriched = enriched.drop(columns=["midpoint", "index_right"])
enriched = enriched.set_geometry("geometry")

# Remain only segments with year of construction assigned
enriched["has_year"] = enriched["ROK"].notna()
hironpl = enriched[enriched["has_year"]]

matched_sections = set(hironpl["auth_id"].dropna())
auth["has_osm_match"] = auth.index.isin(matched_sections)

# Clean the final database
hironpl = hironpl.drop(columns=[
    'azimuth','has_year', 'Id', 'Nr_odcinka',
    'Dlug_osi','Nr_jezdni', 'Kod_pref', 'Kod_nref', 'Odleglosc',
    'Klasa_drog', 'Km_pocz', 'Km_kon', 'Km_gl_pocz', 'Km_gl_kon' ])
# Translate Polish names
hironpl = hironpl.rename(
    columns={"highway":"osm_highway","Droga":"name","ROK": "built_year","MIESIAC":"built_month",
             "DZIEN":"built_day", "WEZEL1": "node1","WEZEL2":"node2"})
# Add length of each road segment
hironpl['length_m'] = np.round(hironpl.length,2)

# Save
hironpl.to_file(
    os.path.join(root,result_dir,"hiron-pl_interim_2180_v1_0.gpkg"),
    layer="osm-poland-260118_motorways_motorways-links_trunks",
    driver="GPKG"
)

auth.to_file(
    os.path.join(root,result_dir,"INTERNAL_auth_matched_2180_v1_0.gpkg"),
    layer="poland_2023_motorways-expressroads",
    driver="GPKG"
)

print('database ready')



# -----------------------------------------------------------------------------
# CONSISTENCY CHECK - check that motorway links have consitent data for each link
# --------------------------------------------------
hironpl_post = gpd.read_file(
    os.path.join(root,result_dir,"hiron-pl_interim_2180_v1_0.gpkg"),
    layer="osm-poland-260118_motorways_motorways-links_trunks")
hironpl_post["uid"] = range(len(hironpl_post))

# --------------------------------------------------
# Parameters and helper function
# --------------------------------------------------
TOL = 5  # meters

DATE_COLS = ["built_year", "built_month", "built_day"]

def date_tuple(row):
    def safe(x):
        try:
            return int(x)
        except:
            return -1
    return tuple(safe(row[c]) for c in DATE_COLS)

# # --------------------------------------------------
# # 1. Select motorway_link segments
# # --------------------------------------------------
links = hironpl_post[hironpl_post.osm_highway == "motorway_link"].copy()

# # --------------------------------------------------
# # 2. Select endpoints 
# # --------------------------------------------------
links["start"] = links.geometry.apply(lambda g: Point(g.coords[0]))
links["end"]   = links.geometry.apply(lambda g: Point(g.coords[-1]))
print('endpoints collected. number of links:', len(links))

# # --------------------------------------------------
# # 3. Build graph of motorway_link connectivity
# # --------------------------------------------------
G = nx.Graph()

i=1
for idx, row in links.iterrows():
    G.add_node(idx)
    for jdx, other in links.iterrows():
        if idx >= jdx:
            continue
        if (
            row["end"].distance(other["start"]) <= TOL or
            row["start"].distance(other["end"]) <= TOL or
            row["start"].distance(other["start"]) <= TOL or
            row["end"].distance(other["end"]) <= TOL
        ):
            G.add_edge(idx, jdx)
    print('building graph: link ',i, '/',len(links))
    i=i+1

components = list(nx.connected_components(G))
links["link_group"] = -1

for i, comp in enumerate(components):
    for idx in comp:
        links.at[idx, "link_group"] = i
print('graph components selected')

# --------------------------------------------------
# 4. Resolve attributes per motorway link segment using the newest section
# --------------------------------------------------
links = links[links.link_group>=0]
# Boolean flags
links["affected"] = False
links["modified"] = False

cols_to_update = ["auth_id","name","built_year","built_month","built_day","node1","node2"]

# Collect index of modified links
affected_idx = []
# Collect index of resolved links
modified_idx = []
for group_id, group in links.groupby("link_group"):
    # Mark affected: more than one section in the segment
    if len(group) > 1:
        links.loc[group.index, "affected"] = True
    
    # Determine newest section
    dates = group.apply(date_tuple, axis=1)
    winner_idx = dates.idxmax()
    winner = links.loc[winner_idx]
     
    # Propagate attributes to all sections
    links.loc[group.index, cols_to_update] = winner[cols_to_update].values
     
    # Mark modified: all except the winner
    modified_indices = group.index.difference([winner_idx])
    links.loc[modified_indices, "modified"] = True
    
# Drop helper geometry columns
links_modified = links.drop(columns=["start", "end"])

# Ensure the correct active geometry
links_modified = links_modified.set_geometry("geometry")

print(f"Resolved conflicts on {len(links[links['affected']])} out of {len(links)} motorway_link sections.")
        
# --------------------------------------------------
# 5. Update the geodataframe
# --------------------------------------------------
# Remove duplicated columns, keep the first occurrence
links = links.loc[:, ~links.columns.duplicated()]

# Set index for alignment
links_indexed = links.set_index("uid")
hironpl_indexed = hironpl_post.set_index("uid")

# Update columns
hironpl_indexed.update(links_indexed[cols_to_update])
print('motorway links updated')

# --------------------------------------------------
# 6. Assign the class of the road and check field names
# --------------------------------------------------
hironpl_indexed = hironpl_indexed.rename(columns={"name": "road_name"})
# If road name starts with 'A' it refers to a motorway. Otherwise it is an expressroad
hironpl_indexed["road_class"] = np.where(
    hironpl_indexed["road_name"].str.startswith("A", na=False),
    "motorway",
    "expressroad"
)
new_order = [
    "osm_id",
    "osm_highway",
    "auth_id",
    "road_name",
    "road_class",
    "built_year",
    "built_month",
    "built_day",
    "node1",
    "node2",
    "length_m",
    "geometry"
]

hironpl_indexed = hironpl_indexed[new_order]


# -----------------------------------------------------------------------------

# Save

hironpl_indexed.to_file(
    os.path.join(root,result_dir,"hiron-pl_2180_v1_0.gpkg"),
    layer="osm-poland-260118_motorways_motorways-links_trunks",
    driver="GPKG"
)

links_modified.to_file(
    os.path.join(root,result_dir,"INTERNAL_motorway-links_resolved_2180_v1_0.gpkg"),
    layer="osm-poland-260118_motorways-links",
    driver="GPKG"
)


