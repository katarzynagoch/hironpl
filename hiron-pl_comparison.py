# -*- coding: utf-8 -*-
"""
Created on Wed Apr 1 15:02:56 2026

@author: Katarzyna Krasnodębska
"""

# Import necessary libraries
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
import math
import os
from shapely.ops import unary_union, linemerge
from shapely.geometry import LineString
from matplotlib.patches import Patch
import matplotlib.colors as mcolors

# Define the path to the geopackage and layer name
root = 'C:\\PROCESSING\\2025_hironpl'
v = 'v1_1'

# Read the geopackage with hiron-pl data, in Polish CRS 2180
result_dir = "results_%s"%v
hiron = gpd.read_file(os.path.join(root,result_dir,"hiron-pl_2180_%s.gpkg"%v),layer="osm-poland-260118_motorways_motorways-links_trunks")
print('hiron CRS', hiron.crs)
# Remove motorway links
hiron = hiron[hiron.osm_highway.isin(['motorway', 'trunk'])]
hiron = hiron.reset_index(drop=True)
# Build spatial index
sindex = hiron.sindex

# functon to detect parallel lines: default threshold 15 degrees
def is_parallel(line1, line2, angle_threshold=15):
    def angle(line):
        x1, y1, x2, y2 = *line.coords[0], *line.coords[-1]
        return np.degrees(np.arctan2(y2 - y1, x2 - x1))
    
    a1 = angle(line1)
    a2 = angle(line2)
    
    return abs(a1 - a2) < angle_threshold or abs(abs(a1 - a2) - 180) < angle_threshold

# Detect dual carriageways
hiron['is_dual'] = False

for idx, row in hiron.iterrows():
    geom = row.geometry
    possible = list(sindex.intersection(geom.buffer(30).bounds))
    
    for j in possible:
        if j == idx:
            continue
        other = hiron.loc[j].geometry
        
        if geom.distance(other) < 30 and is_parallel(geom, other):
            hiron.at[idx, 'is_dual'] = True
            break
        
hiron['effective_length'] = hiron['length_m']
hiron.loc[hiron['is_dual'], 'effective_length'] /= 2


cm = 1/2.54
fs = 10

# Create a barplot with the length of road segments by year
# df = hiron.groupby('built_year')['effective_length'].apply(lambda x: x.effective_length.sum() / 1000).reset_index()
df = hiron.groupby('built_year')['effective_length'].sum()/1000
df = df.reset_index()
# df = df.rename(columns={'geometry': 'length'})
df.built_year = df.built_year.astype(int)
full_years = pd.DataFrame({'built_year': range(1936, 2024)})
df = full_years.merge(df, on='built_year', how='left')
df = df.sort_values('built_year')
df['effective_length'] = df['effective_length'].fillna(0)
df['cumulative_length'] = df['effective_length'].cumsum()


# plt.figure(figsize=(16*cm, 5*cm), dpi=300)
# sns.barplot(x='built_year', y='effective_length', data=df,edgecolor='black', lw=0.3, color='cornflowerblue', width=1)
# plt.xlabel('Year of construction', fontname='Arial', fontsize=fs)
# plt.ylabel('Length [km]', fontname='Arial', fontsize=fs)
# plt.xticks(np.arange(-1,99, 10), np.arange(1935, 2026, 10), fontname='Arial', fontsize=fs)
# # plt.yticks([250,500,750],fontname='Arial', fontsize=fs)
# plt.tight_layout()
# plt.xlim(left=-1)
# plt.savefig(os.path.join(root,result_dir,'vis','road_segments_length_barplot_hiron_%s.png'%v), dpi=300)
# plt.show()


# Set seaborn plot style
sns.set_style('white')

fig, ax1 = plt.subplots(figsize=(10*cm, 5*cm), dpi=300)

# --- Barplot (left axis) ---
sns.barplot(
    x='built_year',
    y='effective_length',
    data=df,
    edgecolor='black',
    lw=0.3,
    color='cornflowerblue',
    width=1,
    ax=ax1
)

ax1.set_xlabel('Year of construction', fontname='Arial', fontsize=fs)
ax1.set_ylabel('Length [km]', fontname='Arial', fontsize=fs)

# --- X ticks ---
ax1.set_xticks(np.arange(-1, 99, 15))
ax1.set_xticklabels(np.arange(1935, 2026, 15), fontname='Arial', fontsize=fs)

ax1.set_xlim(left=-1)

# --- Second axis (right) ---
ax2 = ax1.twinx()

ax2.plot(
    range(len(df)),
    df['cumulative_length'],
    color='black',
    lw=0.8,
    linestyle='-',
    marker='o',
    ms=1,
    markerfacecolor='none'
)

ax2.set_ylabel('Cumulative length [km]', fontname='Arial', fontsize=fs)
ax2.set_yticks(np.arange(0,5001, 1000))

# --- Styling ---
ax1.tick_params(axis='both', labelsize=fs)
ax2.tick_params(axis='y', labelsize=fs)
ax1.set_facecolor('white')
 
fig.tight_layout()

# --- Save ---
# plt.savefig(os.path.join(root, result_dir, 'vis', f'road_segments_length_barplot_hiron_{v}.png'), dpi=300)
plt.show()




# Load Polish border
gdf_eu = gpd.read_file(r"C:\\DATA\\GADM_4_1_European_countries\\Europe\\Europe_merged.shp").to_crs(epsg=3857)
poland_border = gdf_eu[gdf_eu["COUNTRY"] == "Poland"]
poland_data = hiron.to_crs(poland_border.crs)

####################
# Three maps showing Poland from different periods

fig, axs = plt.subplots(1, 3, figsize=(20*cm, 8*cm), dpi=300)

# Plot the oldest highways on the first subplot
break1=2004
break2=2015
old_roads = poland_data[poland_data.built_year<=break1]
old_roads.plot(color='azure', ax=axs[0], legend=False)
poland_border.plot(ax=axs[0], facecolor='darkgrey', edgecolor='black')
axs[0].set_title('1936-%s'%break1, fontname='Arial', fontsize=fs)
axs[0].axis('off')

# Plot the midlle ages on the second subplot
old_roads = poland_data[poland_data.built_year<=break1]
old_roads.plot(color='dimgrey', ax=axs[1], legend=False)
new_roads = poland_data[(poland_data.built_year>break1) & (poland_data.built_year<=break2)]
new_roads.plot(color='azure', ax=axs[1], legend=False)
poland_border.plot(ax=axs[1], facecolor='darkgrey', edgecolor='black')
axs[1].set_title('%s-%s'%(break1+1, break2), fontname='Arial', fontsize=fs)
axs[1].axis('off')

# Plot the newest roads on the last subplot
old_roads = poland_data[poland_data.built_year<=break2]
old_roads.plot(color='dimgrey', ax=axs[2], legend=False)
new_roads = poland_data[poland_data.built_year>break2]
new_roads.plot(color='azure', ax=axs[2], legend=False)
poland_border.plot(ax=axs[2], facecolor='darkgrey', edgecolor='black')
axs[2].set_title('%s-2023'%(break2+1), fontname='Arial', fontsize=fs)
axs[2].axis('off')

# Layout so plots do not overlap
fig.tight_layout()
# Save the plot
plt.savefig(os.path.join(root,result_dir,'vis','stage_maps_HiRoN-PL_%s.png'%v), dpi=300)
# Show the plot
plt.show()


####################
# Map showing motorway and expressway distinction

fig, axs = plt.subplots(1, 1, figsize=(8*cm, 8*cm), dpi=300)
# Plot the oldest highways on the first subplot
poland_data.plot(column='road_class', ax=axs, legend=False, cmap='RdYlGn_r')
poland_border.plot(ax=axs, facecolor='lightgrey', edgecolor='black')
axs.set_title('road class', fontname='Arial', fontsize=fs)
axs.axis('off')
# Layout so plots do not overlap
fig.tight_layout()
# Save the plot
plt.savefig(os.path.join(root,result_dir,'vis','road_class_HiRoN-PL_%s.png'%v), dpi=300)
# Show the plot
plt.show()


####################

# Reference Data from https://pl.wikipedia.org/wiki/Autostrady_i_drogi_ekspresowe_w_Polsce#D%C5%82ugo%C5%9B%C4%87_autostrad_i_dr%C3%B3g_ekspresowych
reference_data = pd.DataFrame({
'Year': [1936, 1937, 1945, 1976, 1978, 1982, 1983, 1984, 1985, 1987, 1988, 1989, 1990, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
'Length': [95.0, 133.0, 133.0, 133.0, 169.0, 190.0, 255.0, 278.0, 321.0, 327.0, 348.0, 366.0, 381.0, 399.0, 403.0, 405.0, 440.0, 453.0, 456.0, 490.0, 502.0, 592.0, 630.0, 639.0, 727.0, 781.0, 848.0, 1013.0, 1083.0, 1282.0, 1454.0, 1560.0, 1865.0, 2495.0, 2805.0, 3100.0, 3131.0, 3252.0, 3510.0, 3811.0, 4214.0, 4337.0, 4625.0, 4887.0, 5116.0, 5332.0, 5776.0]
})

# Merge datasets based on year for RMSE and correlation calculation
merged_data = pd.merge(reference_data, df, left_on='Year', right_on='built_year', how='inner')
merged_data['Difference']=merged_data.Length-merged_data.cumulative_length
merged_data.rename(columns={'Length': 'Reference [km]', 'cumulative_length': 'HiRoN-PL [km]'}, inplace=True)
# Copy to clipboard
table_data = merged_data[['Year', 'Reference [km]', 'HiRoN-PL [km]', 'Difference']].applymap(lambda x: round(x, 2))
table_data.to_csv(os.path.join(root,result_dir,'vis','cumulative_length_comparison_%s.csv'%v))

#####################################################
################# Plot comparison ###################
#####################################################

# Define the classes of road section commissioning
built_classes_5 = [[1936,1980], [1981,1989], [1990,2004], [2005,2014], [2015,2023]] 
# Create a selected colour palette from turbo cmap

built_classes_6 = [[1936,1945], [1946, 1980],[1981,1989], [1990,2004], [2005,2014], [2015,2023]]
# built_classes = [[1936,1980], [1981,2000], [2001,2012]]

# Number of classes/colors
n_classes = len(built_classes_5)
# Generate colors from selected colormap
cmap = plt.get_cmap("turbo")
# built_colors_5 = [mcolors.to_hex(cmap(i / (n_classes - 1))) for i in range(n_classes)]

built_colors_5 = ['#004BE0','#00FFFF','#00FF00','#FFFF00','#FF0000'] # blue, cyan, green, yellow, red
built_colors_6 = ['#569000','#90F000','#FFFF00','#FFD040','#FF0000','#800000']
# pantone built_colors_2012 = ['#00899b','#fdac53','#dd4132']
built_colors_2012 = ['#121f3c', '#00899b','#dd4132']

bg_color = 'whitesmoke'#'#303030'

# Create labels
built_labels = [f"{start}-{end}" for start, end in built_classes_5]

# Map period → color
color_map = dict(zip(built_labels, built_colors_5))

def assign_period(year):
    if pd.isna(year):
        return None
    for start, end in built_classes_5:
        if start <= year <= end:
            return f"{start}-{end}"
    return None

#################### Poland Data ####################
poland_data = hiron.to_crs(poland_border.crs)
poland_data['built_period'] = poland_data['built_year'].apply(assign_period)
poland_data['built_class_colour'] = poland_data['built_period'].map(color_map)

#################### European Data ####################

# Read the European dataset
eu_data = gpd.read_file("C:\\DATA\\2015_European_roads_1955_2012\\DELIBERABLE_STAGE_3.gdb", layer='European_Network_Planarized').to_crs(poland_border.crs)
# Clip the European dataset to the Polish border
eu_data_clipped = gpd.clip(eu_data, poland_border)

# Define a dictionary to map the NCLASS_XXX attribute names to their corresponding years
year_map = {
    'NCLASS_955': 1955,
    'NCLASS_970': 1970,
    'NCLASS_980': 1980,
    'NCLASS_990': 1990,
    'NCLASS_000': 2000,
    'NCLASS_012': 2012
}

# Initialize the 'YEAR_highway' attribute with NaN values
eu_data_clipped['YEAR_highway'] = np.nan

# Iterate over the rows in the dataset
for index, row in eu_data_clipped.iterrows():
    # Initialize the earliest year to infinity
    earliest_year = float('inf')
    
    # Iterate over the NCLASS_XXX attributes
    for attribute, year in year_map.items():
        # If the NCLASS_XXX value is 1 and the year is earlier than the current earliest year
        if row[attribute] == 1 and year < earliest_year:
            # Update the earliest year
            earliest_year = year
    
    # If an earliest year was found, assign it to the 'YEAR_highway' attribute
    if earliest_year != float('inf'):
        eu_data_clipped.at[index, 'YEAR_highway'] = earliest_year
# Assign construction period
eu_data_clipped['built_period'] = eu_data_clipped['YEAR_highway'].apply(assign_period)

# Read the VA museum dataset
va_data = gpd.read_file('C:\\DATA\\2020_VA_European_road_network\\european-highways_all.geojson\\191118_ALL_Merged_DEF.geojson').to_crs(poland_border.crs)
# Clip the European dataset to the Polish border
va_data_clipped = gpd.clip(va_data, poland_border)
# Ensure year is a number
va_data_clipped.end_year = va_data_clipped.end_year.astype(int)
# Assign construction period
va_data_clipped['built_period'] = va_data_clipped['end_year'].apply(assign_period)

# Assign colours
eu_data_clipped['built_class_colour'] = eu_data_clipped['built_period'].map(color_map)
va_data_clipped['built_class_colour'] = va_data_clipped['built_period'].map(color_map)

####################
# New plot:
fig, axs = plt.subplots(1, 4, figsize=(20*cm, 7*cm), dpi=300)

# --- Flatten axes for easier indexing
axs = axs.flatten()

# --- Poland ---
pl_data_plot = poland_data[~poland_data['built_class_colour'].isna()]
pl_data_plot.plot(color='black', lw=3, ax=axs[0], legend=False)
pl_data_plot.plot(color=pl_data_plot['built_class_colour'], ax=axs[0], legend=False)
poland_border.plot(ax=axs[0], facecolor=bg_color, edgecolor='black')
axs[0].set_title('HiRoN-PL', fontname='Arial', fontsize=fs)
axs[0].axis('off')

# --- EU ---
eu_data_plot = eu_data_clipped[~eu_data_clipped['built_class_colour'].isna()]
eu_data_plot.plot(color='black', lw=3, ax=axs[1], legend=False)
eu_data_plot.plot(color=eu_data_plot['built_class_colour'],  ax=axs[1], legend=False)
poland_border.plot(ax=axs[1], facecolor=bg_color, edgecolor='black')
axs[1].set_title('DG REGIO', fontname='Arial', fontsize=fs)
axs[1].axis('off')

# --- VA ---
va_data_plot = va_data_clipped[~va_data_clipped['built_class_colour'].isna()]
va_data_plot.plot(color='black', lw=3, ax=axs[2], legend=False)
va_data_plot.plot(color=va_data_plot['built_class_colour'], ax=axs[2], legend=False)
poland_border.plot(ax=axs[2], facecolor=bg_color, edgecolor='black')
axs[2].set_title('VA Museum', fontname='Arial', fontsize=fs)
axs[2].axis('off')

# --- Add legend ---
legend_elements = [
    Patch(facecolor=color_map[label], edgecolor='black', label=label)
    for label in reversed(built_labels)
]
axs[3].axis('off')

axs[3].legend(
    handles=legend_elements,
    title='Year of construction',
    loc='center',
    frameon=False,
    prop={'family': 'Arial', 'size': fs},
    title_fontsize=fs
)

# --- Layout ---
fig.tight_layout()

# --- Save ---
plt.savefig(os.path.join(root, result_dir, 'vis', f'EU_vs_HiRoN-PL_classes_{v}.png'), dpi=300)

plt.show()



####################
# Plot cumulative road length on single plot
# --- HiRon-PL data ---
hiron_data = hiron.groupby('built_year')['geometry'].apply(lambda x: x.length.sum() / 1000).reset_index()
hiron_data = hiron_data.rename(columns={'geometry': 'length'})
hiron_data = hiron_data.sort_values(by='built_year')
hiron_data['cumulative_length'] = hiron_data['length'].cumsum()/2

# --- EU data ---
eu_data_length = eu_data_clipped.groupby('YEAR_highway')['geometry'].apply(lambda x: x.length.sum() / 1000).reset_index()
eu_data_length = eu_data_length.rename(columns={'geometry': 'length'})
eu_data_length = eu_data_length.sort_values(by='YEAR_highway')
eu_data_length['cumulative_length'] = eu_data_length['length'].cumsum()

# --- VA data ---
va_data_length = va_data_clipped.groupby('end_year')['geometry'].apply(lambda x: x.length.sum() / 1000).reset_index()
va_data_length = va_data_length.rename(columns={'geometry': 'length'})
va_data_length = va_data_length.sort_values(by='end_year')
# Remove silvers
va_data_length = va_data_length[va_data_length.length>1]
va_data_length['cumulative_length'] = va_data_length['length'].cumsum()

# Align year naming
hiron_df = hiron_data.rename(columns={'built_year': 'year'})[['year', 'cumulative_length']]
eu_df = eu_data_length.rename(columns={'YEAR_highway': 'year'})[['year', 'cumulative_length']]
va_df = va_data_length.rename(columns={'end_year': 'year'})[['year', 'cumulative_length']]
ref_df = reference_data.rename(columns={'Year': 'year', 'Length': 'reference_length'})

# Years as int
hiron_df['year'] = hiron_df['year'].astype(int)
eu_df['year'] = eu_df['year'].astype(int)
va_df['year'] = va_df['year'].astype(int)
ref_df['year'] = ref_df['year'].astype(int)


# Plot on single plot
plt.figure(figsize=(9*cm, 8*cm), dpi=300)

# --- Plot all on same axis ---
plt.plot(
    hiron_df['year'],
    hiron_df['cumulative_length'],
    marker='o',lw=0.4,ms=3,color='darkgreen',
    markerfacecolor='none',  
    markeredgecolor='darkgreen',
    linestyle='-',
    label='HiRoN-PL')

plt.plot(
    eu_df['year'],
    eu_df['cumulative_length'],
    marker='o',lw=0.4,ms=3,color='orangered',
    markerfacecolor='none',   
    markeredgecolor='orangered',
    linestyle='-',
    label='DG REGIO')

plt.plot(
    va_df['year'],
    va_df['cumulative_length'],
    marker='o',lw=0.4,ms=3,color='darkblue',
    markerfacecolor='none',
    markeredgecolor='darkblue',
    linestyle='-',
    label='VA Museum')

plt.plot(
    ref_df['year'],
    ref_df['reference_length'],color='black',
    markerfacecolor='none',  
    markeredgecolor='black',
    marker='x',lw=0.6,ms=3,
    linestyle='--',
    label='Reference Data')

# --- Labels ---
plt.xlabel('Year', fontname='Arial', fontsize=fs)
plt.ylabel('Cumulative length (km)', fontname='Arial', fontsize=fs)

ticks = np.arange(1935, 2026, 15)
plt.xticks(ticks, rotation=0, fontname='Arial', fontsize=fs)
plt.yticks(fontname='Arial', fontsize=fs)

plt.legend(prop={'family': 'Arial', 'size': fs})
plt.tight_layout()
plt.grid(False)

ax = plt.gca()

# Show ticks on both sides
ax.yaxis.set_ticks_position('both')

# Keep tick marks on both sides but labels only on the right
ax.tick_params(
    axis='y',
    which='both',
    left=True,
    right=True,
    labelleft=False,
    labelright=True
)

# Ensure label stays on the left
ax.yaxis.set_label_position("left")

# --- Save ---
plt.savefig(os.path.join(root, result_dir, 'vis', f'cumulative_length_all_{v}.png'), dpi=300)
plt.show()


##################################
# Plot relative cumulative lengths
period = [max(hiron_df.year.min(), eu_df.year.min(), va_df.year.min(), ref_df.year.min()),
          min(hiron_df.year.max(), eu_df.year.max(), va_df.year.max(), ref_df.year.max())]

df = pd.DataFrame({'year': range(1936, 2026)})

df = df.merge(hiron_df[['year', 'cumulative_length']], on='year', how='left') \
       .merge(eu_df[['year', 'cumulative_length']], on='year', how='left', suffixes=('_hiron', '_eu')) \
       .merge(va_df[['year', 'cumulative_length']], on='year', how='left') \
       .merge(ref_df[['year', 'reference_length']], on='year', how='left')

df = df.rename(columns={'cumulative_length': 'va_cumulative'})

df[['cumulative_length_hiron',
    'cumulative_length_eu',
    'va_cumulative',
    'reference_length']] = df[['cumulative_length_hiron',
                                'cumulative_length_eu',
                                'va_cumulative',
                                'reference_length']].ffill()
                               
df['hiron_rel'] = df['cumulative_length_hiron'] / df['reference_length'] * 100
df['eu_rel']    = df['cumulative_length_eu']    / df['reference_length'] * 100
df['va_rel']    = df['va_cumulative']           / df['reference_length'] * 100

df['ref_rel'] = 100  # reference baseline

df = df.dropna()
df = df[(df.year>=period[0]) & (df.year<=period[1])]


plt.figure(figsize=(9*cm, 8*cm), dpi=300)

plt.plot(
    df['year'], df['hiron_rel'],
    marker='o', lw=0.4, ms=3, color='darkgreen',
    markerfacecolor='none', markeredgecolor='darkgreen',
    linestyle='-',
    label='HiRoN-PL'
)

plt.plot(
    df['year'], df['eu_rel'],
    marker='o', lw=0.4, ms=3, color='orangered',
    markerfacecolor='none', markeredgecolor='orangered',
    linestyle='-',
    label='DG REGIO'
)

plt.plot(
    df['year'], df['va_rel'],
    marker='o', lw=0.4, ms=3, color='darkblue',
    markerfacecolor='none', markeredgecolor='darkblue',
    linestyle='-',
    label='VA Museum'
)

# Reference = 100%
plt.plot(
    df['year'], df['ref_rel'],
    color='black',
    linestyle='--',
    lw=0.6,
    label='Reference (100%)'
)

# Labels
plt.xlabel('Year', fontname='Arial', fontsize=fs)
plt.ylabel('Relative cumulative length (%)', fontname='Arial', fontsize=fs)

ticks = np.arange(1935, 2026, 15)
# plt.xticks(ticks, fontname='Arial', fontsize=fs)
plt.yticks(fontname='Arial', fontsize=fs)

plt.legend(prop={'family': 'Arial', 'size': fs})
plt.tight_layout()
plt.grid(False)

plt.axhline(100, color='black', lw=0.5, linestyle=':')

# Axis styling (same as yours)
ax = plt.gca()
ax.yaxis.set_ticks_position('both')
ax.tick_params(axis='y', which='both', left=True, right=True, labelleft=False, labelright=True)
ax.yaxis.set_label_position("left")

plt.savefig(os.path.join(root, result_dir, 'vis', f'cumulative_relative_{v}.png'), dpi=300)
plt.show()

      

                         
# Calculate data stats
# Load hiron data one more time

# Read the geopackage with hiron-pl data, in Polish CRS 2180
hiron = gpd.read_file(os.path.join(root,result_dir,"hiron-pl_2180_%s.gpkg"%v),layer="osm-poland-260118_motorways_motorways-links_trunks")
print('hiron CRS', hiron.crs)
# Remove motorway links
hiron = hiron[hiron.osm_highway.isin(['motorway', 'trunk'])]
hiron = hiron.reset_index(drop=True)
# Build spatial index
sindex = hiron.sindex

# functon to detect parallel lines: default threshold 15 degrees
def is_parallel(line1, line2, angle_threshold=15):
    def angle(line):
        x1, y1, x2, y2 = *line.coords[0], *line.coords[-1]
        return np.degrees(np.arctan2(y2 - y1, x2 - x1))
    
    a1 = angle(line1)
    a2 = angle(line2)
    
    return abs(a1 - a2) < angle_threshold or abs(abs(a1 - a2) - 180) < angle_threshold

# Detect dual carriageways
hiron['is_dual'] = False

for idx, row in hiron.iterrows():
    geom = row.geometry
    possible = list(sindex.intersection(geom.buffer(30).bounds))
    
    for j in possible:
        if j == idx:
            continue
        other = hiron.loc[j].geometry
        
        if geom.distance(other) < 30 and is_parallel(geom, other):
            hiron.at[idx, 'is_dual'] = True
            break
        
hiron['effective_length'] = hiron['length_m']
hiron.loc[hiron['is_dual'], 'effective_length'] /= 2


# # Create a histogram of the segment counts - not used
# plt.figure(figsize=(16*cm, 6.5*cm), dpi=300)
# sns.histplot(hiron['built_year'], bins=range(1935, 2026), edgecolor='black', kde=False, color='cornflowerblue')
# # plt.title('Distribution of Road Segments by Year of Construction', fontname='Arial', fontsize=11)
# plt.xlabel('Year of construction', fontname='Arial', fontsize=fs)
# plt.ylabel('Number of road segments', fontname='Arial', fontsize=fs)
# ticks = np.arange(1935, 2026, 10)
# plt.xticks(ticks, rotation=0, fontname='Arial', fontsize=fs)
# plt.yticks(fontname='Arial', fontsize=fs)
# plt.tight_layout()
# plt.savefig(os.path.join(root,result_dir,'vis','road_segments_histogram_%s.png'%v), dpi=300)
# plt.show()