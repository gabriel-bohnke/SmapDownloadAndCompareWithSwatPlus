"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... build HRU shapefile with r2 + color code as attributes
Version.......... 1.00
Last changed on.. 20.07.2022
"""

from util.sqlite_util import read_sqlite_table, count_sqlite_table_rows
from util.soil_util import get_hru_soil_dict, get_soil_correction
import numpy as np
import fiona
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd


# R square with NumPy library
# https://www.askpython.com/python/coefficient-of-determination
def r_square(observed, modeled):
    try:
        corr_matrix = np.corrcoef(observed, modeled)
        corr = corr_matrix[0, 1]
        r2_metric = corr ** 2
        return r2_metric
    except ValueError:
        # print(f'ValueError at index{unit_index}')
        return np.nan


# series1_df: SWAT+
# series2_df: SMAP
def determine_r2(series1_df, series2_df, soil_dict, unit_index):

    # filter dataframes by HRU (unit)
    series1_filter = series1_df['unit'] == unit_index
    series1_df = series1_df[series1_filter]

    series2_filter = series2_df['unit'] == unit_index
    series2_df = series2_df[series2_filter]

    # How to deal with SettingWithCopyWarning in Pandas
    # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
    series1_copy_df = series1_df.copy()  # series1_df is passed by reference: prevent warning at mult. by scalar

    # correct SWAT+ data
    series1_copy_df['sw_final'] = series1_copy_df['sw_final'] / 150 + get_soil_correction(soil_dict[unit_index])

    # ==================================================================================================================
    # plot time series for selected HRUs
    if unit_index > 1500 and unit_index < 1511:
        ax1 = plt.subplot()
        l1, = ax1.plot(series1_copy_df['period'], series1_copy_df['sw_final'],
                       linewidth=3, color='red')
        ax2 = ax1.twinx()
        l2, = ax2.plot(series2_df['period'], series2_df['soil_moisture_1km'],
                       linewidth=3, color='blue')
        plt.legend([l1, l2], ["sw_final", "soil_moisture_1km"])

        # http://www.python-simple.com/python-matplotlib/configuration-axes.php
        plt.gca().xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(8))

        plt.show()
    # ==================================================================================================================

    # sw_final=predictions, soil_moisture_1km=targets
    r2 = r_square(series2_df['soil_moisture_1km'], series1_copy_df['sw_final'])
    return r2


def main():

    # build soil dictionary only once
    soil_dict = get_hru_soil_dict('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite')

    # F_STATISTICS_INPUT directory is expected to have been created in a previous step
    sw_final_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'hru_sw_final_mon',
                                         ['period', 'unit', 'sw_final'])

    hru_sw_final_mon_count = count_sqlite_table_rows('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite',
                                                     'hru_sw_final_mon')
    print(f'{hru_sw_final_mon_count} in hru_sw_final_mon / SWAT+')

    soil_moisture_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite',
                                              'hru_soil_moisture_mon',
                                              ['period', 'unit', 'soil_moisture_1km'])
    hru_soil_moisture_mon_count = count_sqlite_table_rows('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite',
                                                          'hru_soil_moisture_mon')
    print(f'{hru_soil_moisture_mon_count} in hru_soil_moisture_mon / SMAP')

    # dictionary
    r2_dict = {}

    # get total number of HRUs
    hru_count = count_sqlite_table_rows('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite', 'hru_con')

    for index in range(hru_count):
        # determine r2 by HRU
        r2 = determine_r2(sw_final_mean_df, soil_moisture_mean_df, soil_dict, index + 1)

        print(index + 1, str(r2))
        r2_dict[index + 1] = r2  # <-- write entry to dictionary

    print('total entries', len(r2_dict))

    # directory for results of SWAT+ must have been created manually + and it must contain SQLITE file with HRU info
    point_df = read_sqlite_table('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite', 'hru_con', ['id', 'lon', 'lat'])

    # statistics input directory must have been created in a previous step
    statistics_input_directory = 'F_STATISTICS_INPUT'
    shapefile_path = statistics_input_directory + '/' + 'hru_r2.shp'

    # define schema
    schema = {
        'geometry': 'Point',
        'properties': [('HRU', 'str'), ('Value', 'float'), ('Color', 'str'), ('Size', 'int')]
    }

    # open a fiona object
    point_shp = fiona.open(shapefile_path, mode='w', driver='ESRI Shapefile',
                           schema=schema, crs="EPSG:4326")  # crs could be a variable

    # from dark green (= low correlation) to light green (= high correlation)
    colors = ['#032808', '#065712', '#097e1b', '#0ca223', '#0fc92b', '#12ed36']

    # 0.40 threshold
    zero_four_threshold = 0
    # 0.50 threshold
    zero_five_threshold = 0

    # iterate over each row in the dataframe and save record
    for row in point_df.values.tolist():
        hru = row[0]
        r2 = r2_dict[hru]  # <-- read entry from dictionary

        # color setting
        if r2 < 0.50:
            color = colors[0]  # dark green
        elif r2 < 0.525:
            color = colors[1]
        elif r2 < 0.55:
            color = colors[2]
        elif r2 < 0.575:
            color = colors[3]
        elif r2 < 0.60:
            color = colors[4]
        else:
            color = colors[5]  # light green

        row_dict = {
            'geometry': {'type': 'Point',
                         'coordinates': (row[1], row[2])},  # lon, lat
            'properties': {'HRU': hru, 'Value': round(r2, 2), 'Color': color, 'Size': 4}
        }
        point_shp.write(row_dict)

        if r2 > 0.40:
            zero_four_threshold += 1

        if r2 > 0.50:
            zero_five_threshold += 1

    # close fiona object
    point_shp.close()

    # remove entries with NaN values
    import numpy as np
    print(f'{len(r2_dict)} before')
    clean_r2_dict = {k: r2_dict[k] for k in r2_dict if not np.isnan(r2_dict[k])}
    print(f'{len(clean_r2_dict)} after')

    # ---------------------------------------------------------------------------------------------------------------- #
    print('SWAT developers recommend an acceptable calibration for hydrology at a R2 > 0.6 and NSE > 0.5')
    print('source: https://www.scirp.org/journal/paperinformation.aspx?paperid=103729')
    print('\n')
    print('r2 > 0.40:', int(zero_four_threshold / hru_count * 100), '% total HRUs')
    print('r2 > 0.50:', int(zero_five_threshold / hru_count * 100), '% total HRUs')

    # average r2
    print('Average r2:', round(sum(clean_r2_dict.values()) / len(clean_r2_dict), 2))
    # ---------------------------------------------------------------------------------------------------------------- #


if __name__ == '__main__':
    main()
