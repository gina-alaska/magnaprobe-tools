
import matplotlib as mpl
import pandas as pd 
import geopandas as gpd 
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os

uaf_blue = '#236192'
uaf_pantone420c = '#C7C9C7'
uaf_gold = '#FFCD00'
uaf_pantone_wheat = '#EFDBB2'
uaf_red = '#A6192E'
default_dpi = 144


def read_clean_data(clean_file):
	"""Read MagnaProbe datafile already cleaned"""
	if clean_file.endswith('.csv'):
		df = pd.read_csv(clean_file)
		return df
	elif clean_file.endswith('.shp'):
		df = gpd.read_file(clean_file)
		return df
	else:
		print("Please input a cleaned .shp or .csv file.")


def get_depth(df):
	depths = df[[col for col in df.columns if 'depth' in col.lower()][0]]
	return depths
	

def compute_depth_stats(depths):
	"""Compute basic snow depth statistics."""

	hs_N = int(len(depths))
	hs_min = np.min(depths)
	hs_max = np.max(depths)
	hs_mu = np.mean(depths)
	hs_sigma = np.std(depths)
	hs_stats = (hs_N, hs_min, hs_max, hs_mu, hs_sigma)
	return hs_stats
	

def make_stat_annotation(hs_stats):
	"""Create annotation box with basic stats inside."""

	textstr = 'N = %d\nmin = %.2f\nmax = %.2f\n$\mu=%.2f$\n$\sigma=%.2f$' % hs_stats
	props = dict(boxstyle='round', facecolor=uaf_pantone_wheat, alpha=0.5)
	return textstr, props
	

def append_id(fname, id):
	"""Utility function to rename output data"""
	return fname.split('.')[0] + '_' + id + '.' + fname.split('.')[1]


def line_plot(depths, title='MagnaProbe Snow Depth', save=False):
	"""Generates Line Plot. Good for single transects."""
	
	hs_stats = compute_depth_stats(depths)
	tstr, box = make_stat_annotation(hs_stats)
	fig, ax = plt.subplots(figsize=(8, 5))
	ax.plot(depths, c=uaf_blue, lw=2)
	ax.text(0.80, 0.95, tstr, transform=ax.transAxes,
    	fontsize=12, verticalalignment='top', bbox=box)
	ax.set_xlabel('MagnaProbe N')
	ax.set_ylabel('Snow Depth $[m]$')
	ax.set_title(title)
	if save:

		plt.savefig(save, dpi=default_dpi, bbox_inches='tight')
		plt.show()
	else:
		plt.show()


def plot_pdf(depths, n_bins=40, title='MagnaProbe Snow Depth', save=False):
	"""Computes and plots a normalized PDF"""
	fig, ax = plt.subplots(figsize=(8, 5))
	hs_stats = compute_depth_stats(depths)
	tstr, box = make_stat_annotation(hs_stats)
    
	sigma = np.std(depths)
	mu = np.mean(depths)
	count, bins, ignored = plt.hist(depths, n_bins, density=True, histtype='bar', edgecolor='k')
	ln = 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp( - (bins - mu)**2 / (2 * sigma**2))
 
	h = ax.plot(bins, ln, color=uaf_blue, linewidth=2, label='PDF')
	h[0].set_color(uaf_red)
	ax.set_xlabel('Snow Depth $[m]$')
	ax.set_ylabel('Normalized Frequency')
	ax.set_title(title)
	ax.text(0.05, 0.95, tstr, transform=ax.transAxes,
    		fontsize=12, verticalalignment='top', bbox=box)
	if save:
		plt.savefig(save, dpi=default_dpi, bbox_inches='tight')
		plt.show()
	else:
		plt.show()


def map_depth(gdf, title='MagnaProbe Snow Depth Map', save=False):
	"""Create map of probe locations with points colored by depth"""	
	dcol_name = [col for col in gdf.columns if 'depth' in col.lower()][0]
	depths = get_depth(gdf)
	hs_stats = compute_depth_stats(depths)
	tstr, box = make_stat_annotation(hs_stats)
	ext = [gdf['geometry'].x.min(), gdf['geometry'].x.max(),
		   gdf['geometry'].y.min(), gdf['geometry'].y.max()]
	fig_x = int((ext[1]-ext[0]) / (ext[3]-ext[2])) + 6
	fig_y = int((ext[3]-ext[2]) / (ext[1]-ext[0])) + 6
	
	if fig_y > fig_x:
			fig_x += 3
		
	if type(gdf) == gpd.geodataframe.GeoDataFrame:
		fig, ax = plt.subplots(1, 1, figsize=(fig_x, fig_y))
		gdf.plot(column=dcol_name, ax=ax, legend=True,
			legend_kwds={'label': "Snow Depth [m]",'orientation': "vertical"})
		ax.set_ylabel('UTM $m$ N')
		ax.set_xlabel('UTM $m$ E')
		ax.set_title(title)
		ax.text(0.05, 0.95, tstr, transform=ax.transAxes,
    		fontsize=14, verticalalignment='top', bbox=box)
		plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
	else:
		print("Todo: write x,y coords to csv upon crs transform")
	if save:
		plt.savefig(save, dpi=default_dpi, bbox_inches='tight')
		plt.show()
	else:
		plt.show()


if __name__ == '__main__':
	"""Generate Plots from Cleaned MagnaProbe Data"""
	parser = argparse.ArgumentParser(description='Plot Clean MagnaProbe Data.')
	parser.add_argument('clean_data', metavar='c', type=str,
	                     help='path to clean magnaprobe data file')
	parser.add_argument('--save_plots', default=False,
						type=lambda x: (str(x).lower() == 'true'))
	parser.epilog = "Example of use: python plot_magnaprobe.py output_data/Geo1_6_UTM.shp --save_plots true"
	args = parser.parse_args()
	
	clean_df = read_clean_data(args.clean_data)
	snow_depths = get_depth(clean_df)
	title = args.clean_data.split('/')[-1]
	fname_out = os.path.join('output_data', (title.split('.')[-2] + ".png"))
	if args.save_plots:
		print("Saving figures to output_data directory.")
		line_plot(snow_depths, title=title, save=append_id(fname_out, 'line_plot'))
		plot_pdf(snow_depths, title=title, save=append_id(fname_out, 'histogram'))
		map_depth(clean_df, title=title, save=append_id(fname_out, 'depth_map'))
	else:
		print("Not Saving Figures.")
		line_plot(snow_depths, title=title)
		plot_pdf(snow_depths, title=title)
		map_depth(clean_df, title=title)
	print("Plotting Complete.")
