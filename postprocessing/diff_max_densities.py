import fiona
import json
import os
from pathlib import Path
import pandas as pd
from statistics import mean, stdev, median
import json
import geopandas
import matplotlib.pyplot as plt 


def create_dict_from_files(base, compare, outfile):
    base_gdf = geopandas.read_file(base)
    base_gdf['diff_mean'] = None
    base_gdf['diff_median'] = None
    base_gdf['diff_std'] = None

    compare_gdf = geopandas.read_file(compare)
    # for row in compare_gdf:
    base_gdf['diff_mean'] = base_gdf['avg_max_density'].subtract(compare_gdf['avg_max_density'])
    base_gdf['diff_median'] = base_gdf['median_max_density'].subtract(compare_gdf['median_max_density'])
    base_gdf['diff_std'] = base_gdf['std_max_density'].subtract(compare_gdf['std_max_density'])
    base_gdf.to_file(outfile, driver="GPKG")

def calc_diffs(input_dict):
    diff_dict = {}
    for key in input_dict:
        diff = input_dict[key][0] - input_dict[key][1]
        diff_dict[str(key)] = diff
        print(json.dumps(diff_dict,
            sort_keys=True, indent=4))
    return diff_dict

def write_to_gpk(outfile, infile, dicts):
    gdf = geopandas.read_file(infile)
    diffs_mean = []
    diffs_median = []
    diffs_std = []
    for row in gdf["ID"]:
            diffs_mean.append(dicts[0][str(row)])
            diffs_median.append(dicts[1][str(row)])
            diffs_std.append(dicts[2][str(row)])
    gdf["diff_mean"] = diffs_mean
    gdf["diff_median"] = diffs_median
    gdf["diff_std"] = diffs_std
    gdf.to_file(outfile, driver="GPKG")


# text = input("Please enter file path: ")
text = "Experiment/output/1675423435"
list_of_files = ["%s/averages/out_no_comp.gpgk" % text,"%s/averages/out_full_comp.gpgk" % text,"%s/averages/out_cali_comp.gpgk" % text]

Path("%s/differences/" % text).mkdir(parents=True, exist_ok=True)
create_dict_from_files(base="%s/averages/out_cali_comp.gpgk" % text, compare="%s/averages/out_full_comp.gpgk" % text,outfile="%s/differences/cali_full" % text)
create_dict_from_files(base="%s/averages/out_cali_comp.gpgk" % text, compare="%s/averages/out_no_comp.gpgk" % text,outfile="%s/differences/cali_no" % text)
# no compliance

def plot_maps(file_names):
    f, axs = plt.subplots(len(file_names),3,figsize=(10, 10))
    viridis = plt.cm.get_cmap('PiYG', 256)
    cols = ['{}'.format(col) for col in ['Mean', 'Median', 'Standard deviation']]
    rows = ['{}'.format(row) for row in ['Calibrated - Full Compliance', 'Calibrated - No Interventions']]
    for ax, col in zip(axs[0], cols):
        ax.set_title(col)

    for ax, row in zip(axs[:,0], rows):
        ax.set_ylabel(row, rotation=90, size='large')

    for index, file in enumerate(file_names):
        gdf = geopandas.read_file(file)
        gdf.plot(ax=axs[index, 0], column='diff_mean', legend=True, cmap=viridis, vmin=-0.15, vmax=0.15)
        axs[index, 0].legend()
        axs[index, 0].set_xticks([])
        axs[index, 0].set_yticks([])
        
        gdf.plot(ax=axs[index, 1], column='diff_median', legend=True, cmap=viridis, vmin=-0.15, vmax=0.15)
        axs[index, 1].legend()
        axs[index, 1].set_xticks([])
        axs[index, 1].set_yticks([])

        gdf.plot(ax=axs[index, 2], column='diff_std', legend=True, cmap=viridis, vmin=-0.05, vmax=0.05)
        axs[index, 2].legend()
        axs[index, 2].set_xticks([])
        axs[index, 2].set_yticks([])

    plt.show()
plot_maps(["%s/differences/cali_full" % text,"%s/differences/cali_no" % text])

print("done")