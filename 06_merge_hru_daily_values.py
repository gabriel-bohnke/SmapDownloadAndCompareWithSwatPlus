"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... merge HRU daily values with raster band data
Version.......... 1.00
Last changed on.. 02.05.2022
"""

import os
import sqlite3
import pandas as pd
import geopandas as gpd
import rasterio
import numpy as np
from util.sqlite_util import read_sqlite_table
from pandasql import sqldf


def read_point_values_from_raster(date, raster_result_directory, hru_shape_file):

    hru_values = []

    try:
        # open raster file
        raster = rasterio.open(raster_result_directory + '/' + date + '.tif')

        # extract point value from raster
        for i, point in enumerate(hru_shape_file['geometry']):
            x = point.xy[0][0]
            y = point.xy[1][0]
            row, col = raster.index(x, y)
            point_value = raster.read(1)[row, col]
            hru = hru_shape_file['HRU'][i]
            hru_values.append([hru, point_value])
    except:
        # it is possible that raster exists, but that raster read fails during read => then reset hru_values!
        hru_values = []
        for hru in hru_shape_file['HRU']:
            hru_values.append([hru, 0])

    return hru_values


def get_date(*columns):

    return str(int(columns[0])) + '-' + str(int(columns[1])).zfill(2) + '-' + str(int(columns[2])).zfill(2)


def main():

    # D_RASTER_RESULT must have been created in a previous step
    raster_result_directory = 'D_RASTER_RESULT'

    # open hru shapefile
    hru_shape_file = gpd.read_file('E_SWATPLUS_OUTPUT/HRU_SHAPEFILE/hru_points.shp')

    # read table hru_wb_day
    swat_values_df = read_sqlite_table('E_SWATPLUS_OUTPUT/swatplus_output.sqlite', 'hru_wb_day',
                                       ['yr', 'mon', 'day', 'unit', 'sw_final', 'sw_ave', 'sw_init', 'et', 'precip'])
    print(swat_values_df.head())

    swat_values_df['swat_date'] = swat_values_df[['yr', 'mon', 'day']].apply(lambda x: get_date(*x), axis=1)

    # keep columns of interest
    swat_values_df = swat_values_df[['swat_date', 'yr', 'mon', 'unit', 'sw_final', 'sw_ave', 'sw_init', 'et', 'precip']]

    # add subbasin column

    # F_STATISTICS_INPUT directory is expected to have been created in a previous step
    hru_subbasin_rel_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'hru_subbasin_rel',
                                         ['id', 'subbasin'])

    # write query in SQL syntax: here we can use dataframes as normal SQL tables
    query = '''
        SELECT 
            df_left.*,
            df_right.subbasin
        FROM swat_values_df AS df_left
        INNER JOIN hru_subbasin_rel_df AS df_right
        ON df_left.unit = df_right.id;
        '''

    # run SQL query on dataframes
    swat_values_df = sqldf(query, locals())  # use locals here: dataframes are local variables
    print(swat_values_df.head())

    # group by date
    dates_df = swat_values_df[['swat_date', 'unit']].groupby('swat_date')
    print('number of days in SWAT+ output: ' + str(len(dates_df)))

    # read raster point values for all dates
    date_raster_values = []
    for entry in dates_df:
        date = entry[0]
        date_hru_values = read_point_values_from_raster(date, raster_result_directory, hru_shape_file)
        date_raster_values.append([date, date_hru_values])

    # reshape raster values into same format as SWAT+ table
    raster_entries = []
    for date_entry in date_raster_values:
        date = date_entry[0]
        hru_entries = date_entry[1]
        for hru_entry in hru_entries:
            hru = hru_entry[0]
            point_value = hru_entry[1]
            raster_entries.append([date, hru, point_value])

    raster_values_df = pd.DataFrame(raster_entries, columns=['raster_date', 'raster_unit', 'soil_moisture_1km'])

    print('swat_values_df length:   ' + str(swat_values_df.shape[0]))
    print('raster_values_df length: ' + str(raster_values_df.shape[0]))

    swat_values_df['raster_date'] = raster_values_df['raster_date']
    swat_values_df['raster_unit'] = raster_values_df['raster_unit']
    swat_values_df['soil_moisture_1km'] = raster_values_df['soil_moisture_1km']

    print('soil_moisture_1km <> zero:   ', np.count_nonzero(raster_values_df['soil_moisture_1km']))

    rows_with_zero = (raster_values_df['soil_moisture_1km'] == 0).sum()
    print('soil_moisture_1km == zero:   ', rows_with_zero)

    rows_with_neg_values = (raster_values_df['soil_moisture_1km'] == -9999.0).sum()
    print('soil_moisture_1km == -9999.0:', rows_with_neg_values)

    # database filepath OUT
    statistics_input_directory = 'F_STATISTICS_INPUT'
    if not os.path.exists(statistics_input_directory):
        os.makedirs(statistics_input_directory)

    # new sqlite database
    database_filepath_out = statistics_input_directory + '/' + 'swatplus_smap_merge.sqlite'

    con = sqlite3.connect(database_filepath_out)
    swat_values_df.to_sql('hru_day_values', con, if_exists="replace")
    con.close()
    print('dataframe saved to: ' + database_filepath_out)


if __name__ == '__main__':
    main()
