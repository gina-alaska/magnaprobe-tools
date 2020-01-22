import glob
import os
import magnaprobe as mp
import plot_magnaprobe as pltmp
import pandas as pd


header_rows = 1
junk_rows = 2
cols_to_keep = ['timestamp', 'counter',
	            'Latitude', 'Longitude',
	            'Snow Depth m']
epsg_code = 32606
calibration_prefix = 99
calibration_depth_min_cutoff = 0.02
calibration_depth_min_cutoff = 1.18


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
								calibration_depth_min_cutoff)
		print("Cleaned Data Preview:")
		print(clean_df.head(3))
		geom_df = mp.create_geometry(clean_df)
		gdf = mp.create_geodataframe(geom_df)
		utm_df = mp.convert_wgs_to_utm(gdf, epsg_code)
		print("UTM-Converted Preview: ")
		print(utm_df.head(3))

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
	print(concat_df.head(2))
	print(concat_df.tail(2))

def save_shps():
	pass
def save_csvs():
	pass


clean_mp_dict = batch_clean(get_mp_file_list('example_data'))
concatenate_data(clean_mp_dict)
print('MagnaProbe Cleaning Complete.')
#make_plots(clean_mp_dict)


#def save_shps():
#def save_csvs():


