#!/usr/bin/env python

# Module to Clean MagnaProbe Data

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
	    
	    # Only for N & W Hemishperes right now..
	    df['Latitude'] = latitude_int + latitude_dd
	    df['Longitude'] = longitude_int - longitude_dd

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


def trim_cols(df, cols_to_keep):

	df = df[cols_to_keep]
	return df


def create_geometry(df):

	df['geometry'] = df.apply(lambda x: Point((float(x['Longitude']),
											   float(x['Latitude']))), 
											   axis=1)
	return df


def create_geodataframe(df):

	gdf = gpd.GeoDataFrame(df, geometry='geometry')
	
	gdf.crs = ('epsg:4326')
	
	#gdf.crs = {'init' :'epsg:4326'}
	return gdf


def convert_wgs_to_utm(gdf, epsg_code):
	
	epsg_str = 'epsg:' + str(epsg_code)
	
	gdf_utm = gdf.to_crs(epsg_str)

	#gdf_utm = gdf.to_crs({'init': epsg_str})
	return gdf_utm


def save_as_csv(df, out_dst):

	df.to_csv(out_dst, index=False)
	print("CSV file written to %s" % out_dst)


def save_as_shp(gdf, out_dst):

	gdf.to_file(out_dst)
	print("Shapefile written to %s" % out_dst)


if __name__ == '__main__':

	parser = argparse.ArgumentParser(description='Clean MagnaProbe Data.')
	parser.add_argument('raw_data', metavar='d', type=str,
	                     help='path to raw magnaprobe data file')
	parser.add_argument('epsg_code', metavar='e', type=int,
						 help='epsg code for UTM conversion, Zone 6N=32606')
	parser.add_argument('output_utm_shp', metavar='utmshp', type=str,
	                     help='output UTM shapefile destination')
	parser.add_argument('output_utm_csv', metavar='utmcsv', type=str,
                     	 help='output UTM CSV destination')
	args = parser.parse_args()
	
	print("Cleaning MagnaProbe data file %s..." % args.raw_data)
	df = read_tabular(args.raw_data, 1)
	strip_junk_rows(df, 2)
	consolidate_coords(df)
	convert_depth_cm_to_m(df)
	clean_df = trim_cols(df, ['timestamp', 'counter',
                                'Latitude', 'Longitude',
                                'Snow Depth m'])
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
