# A Module to Clean MagnaProbe Data

import pandas as pd
import geopandas as gpd
import argparse
from shapely.geometry import Point

pd.options.mode.chained_assignment = None  # default='warn'


def read_tabular(raw_file, header_row):
    """Read raw MagnaProbe data (*. xls, *.dat, *.csv, etc.) to DataFrame"""
    if raw_file.split('.')[-1][:2] == 'xl':
        raw_df = pd.read_excel(raw_file, header=header_row)
    else:
        raw_df = pd.read_csv(raw_file, header=header_row)
    return raw_df


def strip_junk_rows(raw_df, first_n_rows):
    """Drop header rows that are not needed"""
    raw_df.drop(raw_df.index[:first_n_rows], inplace=True)
    return raw_df


def consolidate_coords(df):
    """Consolidate geospatial coordinate information.

    Coordinates may be split over many fields. There are at least 3 cases
    that need to be handled:
    1. Coordinates are stored in only two fields but not labeled (good)
    2. Coordinates are stored in only two fields but are labeled (great!)
    3. Coordinates are split over many fields (e.g. decimal degrees in one,
    integer degrees in another (yikes!)
    Note: This if-else code should be abstracted away to a dictionary to
    better handle new cases in the future."""

    # make input columns lower case for string matching
    df.columns = [c.lower() for c in df.columns]
    # get columns with coordinate info via pattern match
    coord_cols = sorted([col for col in df.columns if 'tude' in col.lower()])
    # case 1
    if len(coord_cols) == 2:
        df['Latitude'] = df[coord_cols[0]].astype('float')
        df['Longitude'] = df[coord_cols[1]].astype('float')
    # case 2
    elif 'lat' in df.columns:
        df['Latitude'] = df['lat'].astype('float')
        df['Longitude'] = df['lon'].astype('float')
    # case 3
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
    """Convert snow depth in cm to snow depth in m. cm column is retained.
    Again this is messy because there multiple cases. For example one of the
    raw fields name is 'depthBattVolts' so we need to a more careful
    pattern match for which field actually has the snow depth data."""

    depth_cols = sorted([col for col in df.columns if 'depth' in col.lower()])
    # multiple fields case
    if len(depth_cols) != 1:
        for i in depth_cols:
            if 'cm' in i.lower():
                df['Snow Depth m'] = df[i].astype('float') / 100.0
            elif '_m' in i.lower():
                df['Snow Depth m'] = df[i].astype('float')
    # single field case
    else:
        if 'cm' in depth_cols[0].lower():
            df['Snow Depth m'] = df[depth_cols[0]].astype('float') / 100.0
        else:
            df['Snow Depth m'] = df[depth_cols[0]].astype('float')
    return df


def trim_cols(df, list_of_cols_to_keep):
    """Remove all columns except list of specified columns"""
    df = df.copy()[list_of_cols_to_keep]
    return df


def drop_calibration_points(df, calibration_prefix, cal_lower, cal_upper):
    """Drop calibration data points.

    Calibration points are typically sequences of repeating or alternating
    lower bound (e.g. ~0 cm) and upper bound (e.g. ~120 cm) depth
    measurements. Best practice is to key calirbration sequences with a
    different counter prefix in the field (e.g. calibration points are 999*).
    That does not always happen so we can check for patterns of calibration
    points also. Many pattern exist (e.g. 0-120-0-120, 120-0-0) so we check
    common ones and use an A (cal_lower) B (cal_upper) pattern notation to
    keep track.
    """

    print("Starting number of rows: %s" % len(df))
    # drop data with calibration prefix, e.g. 99
    dfc = df[df.counter.astype('str').str[:2] != str(calibration_prefix)]

    print("Rows left after culling by counter prefix: %s" % len(dfc))

    # find rows with depths near cal_lower or cal_upper
    # this gets gnarly and should be abstracted away to a dict using a loop
    mp_bottom = dfc['Snow Depth m'] < cal_lower
    mp_top = dfc['Snow Depth m'] > cal_upper
    # check previous row
    prev_mp_bottom = dfc['Snow Depth m'].shift(-1) < cal_lower
    prev_mp_top = dfc['Snow Depth m'].shift(-1) > cal_upper
    # check if next row
    next_mp_bottom = dfc['Snow Depth m'].shift(+1) < cal_lower
    next_mp_top = dfc['Snow Depth m'].shift(+1) > cal_upper
    # check 2nd previous row
    prev2_mp_bottom = dfc['Snow Depth m'].shift(-2) < cal_lower
    prev2_mp_top = dfc['Snow Depth m'].shift(-2) > cal_upper
    # check 2nd next
    next2_mp_bottom = dfc['Snow Depth m'].shift(+2) < cal_lower
    next2_mp_top = dfc['Snow Depth m'].shift(+2) > cal_upper
    # check 3rd previous row
    prev3_mp_bottom = dfc['Snow Depth m'].shift(-3) < cal_lower
    prev3_mp_top = dfc['Snow Depth m'].shift(-3) > cal_upper
    # check 3rd next row
    next3_mp_bottom = dfc['Snow Depth m'].shift(+3) < cal_lower
    next3_mp_top = dfc['Snow Depth m'].shift(+3) > cal_upper
    # A-B calibration patterns
    # depth too low and previous depth too high
    cal1 = (mp_bottom) & (prev_mp_top)
    # depth too low and next depth too high
    cal2 = (mp_bottom) & (next_mp_top)
    # depth too high and previous depth too low
    cal3 = (mp_top) & (prev_mp_bottom)
    # depth too high and next depth too low
    cal4 = (mp_top) & (next_mp_bottom)
    # A-A-B patterns e.g. low-low-high
    cal5 = (mp_bottom) & (prev_mp_bottom) & (prev2_mp_bottom)
    cal6 = (mp_top) & (prev_mp_top) & (prev2_mp_top)
    cal7 = (mp_bottom) & (next_mp_bottom) & (next2_mp_top)
    cal8 = (mp_top) & (next_mp_top) & (next2_mp_bottom)
    # A-A-A-B patterns
    cal9 = (mp_bottom) & (prev_mp_bottom) & (prev2_mp_top) & (prev3_mp_top)
    cal10 = (mp_top) & (prev_mp_top) & (prev2_mp_bottom) & (prev3_mp_bottom)
    cal11 = (mp_bottom) & (next_mp_bottom) & (next2_mp_top) & (next3_mp_top)
    cal12 = (mp_top) & (next_mp_top) & (next2_mp_bottom) & (next3_mp_bottom)
    # OR condition for all calibration patterns
    cal_patterns = cal1 | cal2 | cal3 | cal4 | cal5 | cal6 | cal7 | cal8 |\
        cal9 | cal10 | cal11 | cal12
    # drop rows matching calibration patterns
    df2 = dfc.drop(dfc[cal_patterns].index)
    print("Rows left after culling by calibration patterns: %s" % len(df2))
    return df2


def create_geometry(df):
    """Add Geometry column to specify that these are spatial coordinates for
    point vector data"""
    df['geometry'] = df.apply(lambda x: Point(
        (float(x['Longitude']), float(x['Latitude']))), axis=1)
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
    """Save clean data to CSV"""
    df.to_csv(out_dst, index=False)
    print("CSV file written to %s" % out_dst)


def save_as_shp(gdf, out_dst):
    """Save clean data to point shapefile ready for GIS"""
    gdf.to_file(out_dst)
    print("Shapefile written to %s" % out_dst)


if __name__ == '__main__':
    """Clean Input File and Write UTM data to CSV and Shapefile"""
    parser = argparse.ArgumentParser(
        description='Utility to Clean MagnaProbe Data.')
    parser.add_argument('raw_data', metavar='d', type=str,
                        help='path to raw magnaprobe data file')
    parser.add_argument('epsg_code', metavar='e', type=int,
                        help='UTM epsg code, e.g. 32606 for 6N')
    parser.add_argument('output_utm_shp', metavar='utmshp', type=str,
                        help='output UTM shapefile destination')
    parser.add_argument('output_utm_csv', metavar='utmcsv', type=str,
                        help='output UTM CSV destination')
    parser.epilog = "Example of use: python magnaprobe.py 'example_data/Geo2_4_raw.dat' 32606 'output_data/Geo2_4_UTM.shp' 'output_data/Geo2_4_UTM.csv'"
    args = parser.parse_args()

    print("Cleaning MagnaProbe data file %s..." % args.raw_data)
    df = read_tabular(args.raw_data, 1)
    df = strip_junk_rows(df, 2)
    df = consolidate_coords(df)
    df = convert_depth_cm_to_m(df)
    df = trim_cols(df, ['timestamp', 'counter', 'Latitude',
                        'Longitude', 'Snow Depth m'])
    df = drop_calibration_points(df, 99, 0.02, 1.18)
    print("Cleaned Data Preview:")
    print(df.head(5))
    geom_df = create_geometry(df)
    gdf = create_geodataframe(geom_df)
    utm_df = convert_wgs_to_utm(gdf, args.epsg_code)
    print("UTM-Converted Preview: ")
    print(utm_df.head(5))
    save_as_csv(utm_df, args.output_utm_csv)
    save_as_shp(utm_df, args.output_utm_shp)
    print('MagnaProbe Cleaning Complete.')
