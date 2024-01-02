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
    return max(base_gdf['diff_mean']), max(base_gdf['diff_median']), max(base_gdf['diff_std']), min(base_gdf['diff_mean']), min(base_gdf['diff_median']), min(base_gdf['diff_std'])


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
text = "Experiment/output/1683635583"
list_of_files = ["%s/averages/out_no_comp.gpgk" % text,"%s/averages/out_full_comp.gpgk" % text,"%s/averages/out_cali_comp.gpgk" % text]

Path("%s/differences/" % text).mkdir(parents=True, exist_ok=True)
cali_full_max_mean, cali_full_max_median, cali_full_max_std, cali_full_min_mean, cali_full_min_median, cali_full_min_std = create_dict_from_files(base="%s/averages/out_cali_comp.gpgk" % text, compare="%s/averages/out_full_comp.gpgk" % text,outfile="%s/differences/cali_full" % text)
cali_no_max_mean, cali_no_max_median, cali_no_max_std, cali_no_min_mean, cali_no_min_median, cali_no_min_std = create_dict_from_files(base="%s/averages/out_cali_comp.gpgk" % text, compare="%s/averages/out_no_comp.gpgk" % text,outfile="%s/differences/cali_no" % text)
# no compliance

def plot_maps(file_names, max_mean, max_median, max_std, min_mean, min_median, min_std):
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
        min_max_mean = max(abs(min_mean), abs(max_mean))
        gdf.plot(ax=axs[index, 0], column='diff_mean', legend=True, cmap=viridis, vmin=-min_max_mean, vmax=min_max_mean)
        axs[index, 0].legend()
        axs[index, 0].set_xticks([])
        axs[index, 0].set_yticks([])
        
        min_max_median = max(abs(min_median), abs(max_median))
        gdf.plot(ax=axs[index, 1], column='diff_median', legend=True, cmap=viridis, vmin=-min_max_median, vmax=min_max_median)
        axs[index, 1].legend()
        axs[index, 1].set_xticks([])
        axs[index, 1].set_yticks([])
        
        min_max_std = max(abs(min_std), abs(max_std))
        gdf.plot(ax=axs[index, 2], column='diff_std', legend=True, cmap=viridis, vmin=-min_max_std, vmax=min_max_std)
        axs[index, 2].legend()
        axs[index, 2].set_xticks([])
        axs[index, 2].set_yticks([])

    plt.show()


max_mean = max(cali_full_max_mean, cali_no_max_mean)
max_median = max(cali_full_max_median, cali_no_max_median)
max_std = max(cali_full_max_std, cali_no_max_std)
min_mean = min(cali_full_min_mean, cali_no_min_mean)
min_median = min(cali_full_min_median, cali_no_min_median)
min_std = min(cali_full_min_std, cali_no_min_std)

plot_maps(["%s/differences/cali_full" % text,"%s/differences/cali_no" % text], max_mean, max_median, max_std, min_mean, min_median, min_std)

print("done")