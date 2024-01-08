import fiona
import json
import os
from pathlib import Path
import pandas as pd
from statistics import mean, stdev, median
import json
import geopandas
import matplotlib.pyplot as plt 
import seaborn as sns


def create_dict_from_files(base, compare, outfile):
    """ Calculate differences between to edge files
    """
    # read basefile
    base_gdf = geopandas.read_file(base)
    # make sure fields are empty as we are editing the base file
    base_gdf['diff_mean'] = None
    base_gdf['diff_median'] = None
    base_gdf['diff_std'] = None
    base_gdf['diff_95th_percentile'] = None

    # read comparison file
    compare_gdf = geopandas.read_file(compare)
    # compare data and temporarily store results as fields in base file
    base_gdf['diff_mean'] = base_gdf['mean_density'].subtract(compare_gdf['mean_density'])
    base_gdf['diff_median'] = base_gdf['median_density'].subtract(compare_gdf['median_density'])
    base_gdf['diff_std'] = base_gdf['std_density'].subtract(compare_gdf['std_density'])
    base_gdf['diff_95th_percentile'] = base_gdf['95th_percentile'].subtract(compare_gdf['95th_percentile'])
    
    # write to new file
    base_gdf.to_file(outfile, driver="GPKG")

def plot_single_map(file, title, outname, abs_max):
    sns.set()
    sns.set_style(rc = {'axes.facecolor': '#989898'})
    viridis = plt.cm.get_cmap('PiYG', 256)
    f, ax = plt.subplots(figsize=(6, 4))
    # read file
    gdf = geopandas.read_file(file)
    # plot data as map
    gdf.plot(ax=ax, column='diff_mean', legend=True, legend_kwds={"label": "difference in people / $m^2$", "orientation": "vertical"},  cmap=viridis, vmin=-abs_max, vmax=abs_max, linewidth=3)
    ax.set_xticks([])
    ax.set_yticks([])
    # save to file and show
    plt.savefig(outname + ".pdf", bbox_inches='tight')
    plt.savefig(outname + ".png", bbox_inches='tight')
    plt.show()

# ---------------------------- MAIN --------------------------------
folder_name = "compliance_study"
base_path = "Experiment/output/" + folder_name

# create output folder
Path("%s/differences/" % base_path).mkdir(parents=True, exist_ok=True)

list_of_files = ["%s/averages/stats_by_street_no_interv.gpgk" % base_path,"%s/averages/stats_by_street_full_comp.gpgk" % base_path,"%s/averages/stats_by_street_cali_comp.gpgk" % base_path]
create_dict_from_files(base="%s/averages/stats_by_street_cali_comp.gpgk" % base_path, compare="%s/averages/stats_by_street_full_comp.gpgk" % base_path,outfile="%s/differences/cali_full" % base_path)
create_dict_from_files(base="%s/averages/stats_by_street_cali_comp.gpgk" % base_path, compare="%s/averages/stats_by_street_no_interv.gpgk" % base_path,outfile="%s/differences/cali_no" % base_path)

# get maximum absoulte difference value across both comparisons
ymax_mean = 0
for file in ["%s/differences/cali_full" % base_path, "%s/differences/cali_no" % base_path]:
    gdf = geopandas.read_file(file)
    max_gdf = gdf.max()
    min_gdf = gdf.min()
    ymax_mean = max(ymax_mean,max_gdf.diff_mean,abs(min_gdf.diff_mean))
plot_single_map("%s/differences/cali_full" % base_path, 'Calibrated - Full Compliance', "%s/differences/cali_full_map" % base_path, ymax_mean)
plot_single_map("%s/differences/cali_no" % base_path, 'Calibrated - No Interventions', "%s/differences/cali_no_map" % base_path, ymax_mean)

print("Script completed.")