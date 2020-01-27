#!/usr/bin/env python

# A Batch Tool for MagnaProbe Data

import glob
import os
import magnaprobe as mp
import plot_magnaprobe as pltmp
import pandas as pd
import argparse

header_rows = 1
junk_rows = 2
cols_to_keep = ['timestamp', 'counter',
	            'Latitude', 'Longitude',
	            'Snow Depth m']
epsg_code = 32606
calibration_prefix = 99
calibration_depth_min_cutoff = 0.02
calibration_depth_max_cutoff = 1.18


def get_mp_file_list(mp_dir):

	mp_files = glob.glob(os.path.join(mp_dir, '*'))
	print(mp_files)
	d = dict()
	for f in mp_files:
		d[f]={}
	print(d)
	return d

	
def batch_clean(mp_file_dict):
	
	for f in mp_file_dict:

		print("Cleaning file: " + f)
		df = mp.read_tabular(f, header_rows)
		mp.strip_junk_rows(df, junk_rows)
		mp.consolidate_coords(df)
		mp.convert_depth_cm_to_m(df)
		clean_df = mp.trim_cols(df, cols_to_keep)
		mp.drop_calibration_points(clean_df,
								calibration_prefix,
								calibration_depth_min_cutoff,
								calibration_depth_max_cutoff)
		geom_df = mp.create_geometry(clean_df)
		gdf = mp.create_geodataframe(geom_df)
		utm_df = mp.convert_wgs_to_utm(gdf, epsg_code)

		mp_file_dict[f]['cleaned_utm_df'] = utm_df
		print(utm_df.columns)
	print(mp_file_dict.keys())
	return mp_file_dict


def batch_plots(mp_file_dict):
	for f in mp_file_dict:
		depth = pltmp.get_depth(mp_file_dict[f]['cleaned_utm_df'])
		pltmp.line_plot(depth, title=f)
		pltmp.plot_pdf(depth, title=f)
		pltmp.map_depth(mp_file_dict[f]['cleaned_utm_df'], title=f)


def concatenate_data(mp_file_dict):
	dfs = [mp_file_dict[k]['cleaned_utm_df'] for k in mp_file_dict]
	concat_df = pd.concat(dfs)
	print(len(concat_df))
	return concat_df


def plot_concat_data(concat_df):
	depth = pltmp.get_depth(concat_df)
	pltmp.plot_pdf(depth)
	pltmp.map_depth(concat_df)


if __name__ == '__main__':

	"""Batch Tool for Cleaning and Plotting MagnaProbe Data"""
	parser = argparse.ArgumentParser(description='Utility to Clean MagnaProbe Data.')
	parser.add_argument('raw_data_dir', metavar='d', type=str,
	                     help='path to raw magnaprobe data directory')
	
	parser.add_argument('concat_output', metavar='o', type=str,
	                     help='output concatenated data destination')
	# parser.epilog = "Example of use: python batch_magnaprobe.py example_data/batch_example/ output_data/batch_output/Geo1"
	args = parser.parse_args()

	
	clean_mp_dict = batch_clean(get_mp_file_list(args.raw_data_dir))
	concat_df = concatenate_data(clean_mp_dict)
	# batch_plots(clean_mp_dict)
	plot_concat_data(concat_df)
	mp.save_as_csv(concat_df, args.concat_output + '.csv')
	mp.save_as_shp(concat_df, args.concat_output + '.shp')


