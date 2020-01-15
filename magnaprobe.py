#!/usr/bin/env python

# A Module to Clean MagnaProbe Data

import pandas as pd
from shapely.geometry import Point
import geopandas as gpd
import argparse

pd.options.mode.chained_assignment = None  # default='warn'

def read_tabular(raw_file, header_row):
	"""Read 'raw' MagnaProbe data (*. xls, *.dat, *.csv, etc.) to DataFrame"""
	if raw_file.split('.')[-1][:2] == 'xl':
		raw = pd.read_excel(raw_file, header=header_row)
	else:	
		raw = pd.read_csv(raw_file, header=header_row)
	return raw


def strip_junk_rows(raw_df, first_n_rows):
	"""Drop n header rows that are not needed"""
	raw_df.drop(raw_df.index[:first_n_rows], inplace=True)
	return raw_df


def consolidate_coords(df):
	"""Consolidate coordinate information that is split across many columns"""
	# make input columns lower case for string matching
	df.columns = [c.lower() for c in df.columns]
	# get columns with coordinate info
	coord_cols = sorted([col for col in df.columns if 'tude' in col.lower()])
	# only two? that's our lat / lon b/c we sorted alphabetically
	if len(coord_cols) == 2:
	    df['Latitude'] = df[coord_cols[0]].astype('float')
	    df['Longitude'] = df[coord_cols[1]].astype('float')
	elif 'lat' in df.columns:
	    df['Latitude'] = df['lat'].astype('float')
	    df['Longitude'] = df['lon'].astype('float')
	else:
	    dec_deg_cols = sorted([col for col in coord_cols if 'dd' in col])
	    latitude_dd = df[dec_deg_cols[0]].astype('float')
	    longitude_dd = df[dec_deg_cols[1]].astype('float')
	    int_deg_cols = sorted([col for col in coord_cols if '_a' in col])
	    latitude_int = df[int_deg_cols[0]].astype('float')
	    longitude_int = df[int_deg_cols[1]].astype('float')
	    
	    df['Latitude'] = latitude_int + latitude_dd
	    df['Longitude'] = longitude_int + longitude_dd
	return df


def convert_depth_cm_to_m(df):
	"""Convert snow depth in cm to snow depth in m. cm column is retained."""
	# Ugly b/c there is a 'depthBattVolts' col in some data
	depth_cols = sorted([col for col in df.columns if 'depth' in col.lower()])
	
	# Multiple 'depth' cols case
	if len(depth_cols) != 1:
	    for i in depth_cols:
	        if 'cm' in i.lower():
	            df['Snow Depth m'] = df[i].astype('float') / 100.0
	        elif '_m' in i.lower():
	            df['Snow Depth m'] = df[i].astype('float')
	# Single 'depth' col case            
	else:
	    if 'cm' in depth_cols[0].lower():
	        df['Snow Depth m'] = df[depth_cols[0]].astype('float') / 100.0
	    else:
	        df['Snow Depth m'] = df[depth_cols[0]].astype('float')
	return df


def trim_cols(df, list_of_cols_to_keep):
	"""Remove all columns except list of columns specified by user to retain."""
	df = df[list_of_cols_to_keep]
	return df

def drop_calibration_points(df, calibration_prefix, c1, c2):
	"""Drop calibration points.

	Calibration points are typically sequences of repeating or alternating
	~0cm and ~120cm depth measurements. Ideally these are keyed with a
	different counter number in the field (e.g. all start with 99...).
	We can also check for the 0cm-120cm sequences if there is no such
	counter prefix. Many sequences exist (e.g. 0-120-0, 120-0-0) so we test
	for a few common ones.
	"""

	print("Starting number of rows: %s" % len(df))
	# drop data with calibration prefix, e.g. 99
	df = df[df.counter.str[:2] != str(calibration_prefix)]

	print("Rows left after culling by counter prefix: %s" % len(df))

	# find rows with depths near 0 m or 1.2 m 
	mp_bottom = df['Snow Depth m'] < c1
	mp_top = df['Snow Depth m'] > c2
	# check if previous row is near 0 m or 1.2 m
	prev_mp_bottom = df['Snow Depth m'].shift(-1) < c1
	prev_mp_top = df['Snow Depth m'].shift(-1) > c2
	# check if next row is near 0 m or 1.2 m
	next_mp_bottom = df['Snow Depth m'].shift(+1) < c1
	next_mp_top = df['Snow Depth m'].shift(+1) > c2
	# check if 2nd previous row is near 0 m or 1.2 m
	prev2_mp_bottom = df['Snow Depth m'].shift(-2) < c1
	prev2_mp_top = df['Snow Depth m'].shift(-2) > c2
	# check if 2nd next row is near 0 m or 1.2 m
	next2_mp_bottom = df['Snow Depth m'].shift(+2) < c1
	next2_mp_top = df['Snow Depth m'].shift(+2) > c2
	# check if 3rd previous row is near 0 m or 1.2 m
	prev3_mp_bottom = df['Snow Depth m'].shift(-3) < c1
	prev3_mp_top = df['Snow Depth m'].shift(-3) > c2
	# check if 3rd next row is near 0 m or 1.2 m
	next3_mp_bottom = df['Snow Depth m'].shift(+3) < c1
	next3_mp_top = df['Snow Depth m'].shift(+3) > c2
	# A-B calibration patterns
	# AA or BB is no good because that could stretch of scour or over-top
	# depth too low and previous depth too high
	cal1 = (mp_bottom) & (prev_mp_top)
	# depth too low and next depth too high	
	cal2 = (mp_bottom) & (next_mp_top)
	# depth too high and previous depth too low
	cal3 = (mp_top) & (prev_mp_bottom)
	# depth too high and next depth too low	
	cal4 = (mp_top) & (next_mp_bottom)
	# A-A-B patterns
	cal5 = (mp_bottom) & (prev_mp_bottom) & (prev2_mp_bottom)
	cal6 = (mp_top) & (prev_mp_top) & (prev2_mp_top)
	cal7 = (mp_bottom) & (next_mp_bottom) & (next2_mp_top)
	cal8 = (mp_top) & (next_mp_top) & (next2_mp_bottom)
	# A-A-A-B patterns
	cal9 = (mp_bottom) & (prev_mp_bottom) & (prev2_mp_top) & (prev3_mp_top)
	cal10 = (mp_top) & (prev_mp_top) & (prev2_mp_bottom) & (prev3_mp_bottom)
	cal11 = (mp_bottom) & (next_mp_bottom) & (next2_mp_top) & (next3_mp_top)
	cal12 = (mp_top) & (next_mp_top) & (next2_mp_bottom) & (next3_mp_bottom)
	# OR condition for calibration patterns
	cal_patterns = cal1 | cal2 | cal3 | cal4 | cal5 | cal6 | cal7 | cal8 |\
	               cal9 | cal10 | cal11 | cal12
	# drop rows matching calibration patterns
	df = df.drop(df[cal_patterns].index)
	print("Rows left after culling by calibration patterns: %s" % len(df))
	return df


def create_geometry(df):
	"""Add Geometry column to specify lat and lon are special, i.e. point vector data"""
	df['geometry'] = df.apply(lambda x: Point((float(x['Longitude']), float(x['Latitude']))), axis=1)
	return df


def create_geodataframe(df):
	"""Create GeoDataFrame with WGS 84 Spatial Reference"""
	gdf = gpd.GeoDataFrame(df, geometry='geometry')
	gdf.crs = ('epsg:4326')
	return gdf


def convert_wgs_to_utm(gdf, epsg_code):
	"""Convert WGS 84 GeoDataFrame to UTM GeoDataFrame"""
	epsg_str = 'epsg:' + str(epsg_code)	
	gdf_utm = gdf.to_crs(epsg_str)
	return gdf_utm


def save_as_csv(df, out_dst):
	"""Save a Clean CSV File"""
	df.to_csv(out_dst, index=False)
	print("CSV file written to %s" % out_dst)


def save_as_shp(gdf, out_dst):
	"""Save a point shapefile ready for GIS"""
	gdf.to_file(out_dst)
	print("Shapefile written to %s" % out_dst)


if __name__ == '__main__':
	"""Clean Input File and Write UTM CSV and Shapefile"""
	parser = argparse.ArgumentParser(description='Utility to Clean MagnaProbe Data.')
	parser.add_argument('raw_data', metavar='d', type=str,
	                     help='path to raw magnaprobe data file')
	parser.add_argument('epsg_code', metavar='e', type=int,
						 help='epsg code for UTM conversion, e.g. 32606 for 6N')
	parser.add_argument('output_utm_shp', metavar='utmshp', type=str,
	                     help='output UTM shapefile destination')
	parser.add_argument('output_utm_csv', metavar='utmcsv', type=str,
                     	 help='output UTM CSV destination')
	parser.epilog = "Example of use: python magnaprobe.py 'example_data/Geo2_4_raw.dat' 32606 'output_data/Geo2_4_UTM.shp' 'output_data/Geo2_4_UTM.csv'"
	args = parser.parse_args()
	
	print("Cleaning MagnaProbe data file %s..." % args.raw_data)
	df = read_tabular(args.raw_data, 1)
	strip_junk_rows(df, 2)
	consolidate_coords(df)
	convert_depth_cm_to_m(df)
	clean_df = trim_cols(df, ['timestamp', 'counter',
                                'Latitude', 'Longitude',
                                'Snow Depth m'])
	drop_calibration_points(clean_df, 99, 0.02, 1.18)
	print("Cleaned Data Preview:")
	print(clean_df.head(3))
	geom_df = create_geometry(clean_df)
	gdf = create_geodataframe(geom_df)
	utm_df = convert_wgs_to_utm(gdf, args.epsg_code)
	print("UTM-Converted Preview: ")
	print(utm_df.head(3))
	save_as_csv(utm_df, args.output_utm_csv)
	save_as_shp(utm_df, args.output_utm_shp)
	print('MagnaProbe Cleaning Complete.')
