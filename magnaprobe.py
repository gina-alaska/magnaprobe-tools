#!/usr/bin/env python

# Module to Clean, Analyze, and Plot MagnaProbe Data

import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt 


def read_tabular(raw_file, header_row):

	# Read in raw MagnaProbe data (*.dat, *.csv) to DataFrame and clean columns and headers
	raw = pd.read_csv(raw_file, header=header_row)
	return raw


def strip_junk_rows(raw_df, first_n_rows):

	raw_df.drop(raw_df.index[:first_n_rows], inplace=True)
	return raw_df


def consolidate_coords(df):

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




# data['Depth_m'] = data['DepthCm'].values.astype(float) / 100.0
# data['ID'] = data['Counter'].astype(int)
# data['DateTime'] = data['TIMESTAMP']
# data['id_check'] = data['ID'].astype(str)
# data['id_check'] = data['id_check'].apply(lambda x: x[0:2])


# 	"""Reads MagnaProbe data from *.dat file to Pandas DataFrame"""


# 	return df

# def clean_data():

