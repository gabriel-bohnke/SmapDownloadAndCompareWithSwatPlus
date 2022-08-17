"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... build HRU shapefile with Nash-Sutcliffe Efficiency (NSE) + color code as attributes
Version.......... 1.00
Last changed on.. 10.05.2022
"""

from util.sqlite_util import read_sqlite_table, count_sqlite_table_rows
from util.soil_util import get_hru_soil_dict, get_soil_correction
import numpy as np
import fiona
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd


# Calculate Nash-Sutcliff-Efficiency
# https://stackoverflow.com/questions/63903016/calculate-nash-sutcliff-efficiency
def nash_sutcliffe_efficiency(observed, modeled):

    nse_metric = 1 - (np.sum((observed - modeled) ** 2) / np.sum((observed - np.mean(observed)) ** 2))
    return nse_metric


def determine_nse(series1_df, series2_df, soil_dict, unit_index):

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
        plt.legend([l1, l2], ['sw_final', 'soil_moisture_1km'])

        # http://www.python-simple.com/python-matplotlib/configuration-axes.php
        plt.gca().xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(8))

        plt.show()
    # ==================================================================================================================

    # observed=SMAP, modeled=SWAT+
    nse = nash_sutcliffe_efficiency(series2_df['soil_moisture_1km'], series1_copy_df['sw_final'])
    return nse


def main():

    # build soil dictionary only once
    soil_dict = get_hru_soil_dict('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite')

    # F_STATISTICS_INPUT directory is expected to have been created in a previous step
    sw_final_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'hru_sw_final_mon',
                                       ['period', 'unit', 'sw_final'])

    soil_moisture_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'hru_soil_moisture_mon',
                                              ['period', 'unit', 'soil_moisture_1km'])

    # ---------------------------------------------------------------------------------------------------------------- #
    # # test: exclude some periods from time series
    # # periods to include / exclude (using ~)
    # periods = pd.period_range('2017-05', '2019-04', freq='M').array
    # tuple_of_periods = tuple(i.strftime('%Y-%m') for i in periods)
    # print(tuple_of_periods)
    #
    # # drop entries with period contained in tuple of periods: SWAT+
    # sw_final_mean_df = sw_final_mean_df[~sw_final_mean_df.period.str.startswith(
    #     tuple_of_periods)]  # negate str.startswith using tuple of values
    #
    # # drop entries with period contained in tuple of periods: SMAP
    # soil_moisture_mean_df = soil_moisture_mean_df[~soil_moisture_mean_df.period.str.startswith(
    #     tuple_of_periods)]  # negate str.startswith using tuple of values
    # ---------------------------------------------------------------------------------------------------------------- #

    # dictionary
    nse_dict = {}

    # get total number of HRUs
    hru_count = count_sqlite_table_rows('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite', 'hru_con')

    for index in range(hru_count):

        # determine NSE by HRU
        nse = determine_nse(sw_final_mean_df, soil_moisture_mean_df, soil_dict, index + 1)

        print(index + 1, str(nse))
        nse_dict[index + 1] = nse  # <-- write entry to dictionary

    print('total entries', len(nse_dict))

    # directory for results of SWAT+ must have been created manually + and it must contain SQLITE file with HRU info
    point_df = read_sqlite_table('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite', 'hru_con', ['id', 'lon', 'lat'])

    # statistics input directory must have been created in a previous step
    statistics_input_directory = 'F_STATISTICS_INPUT'
    shapefile_path = statistics_input_directory + '/' + 'hru_nash_sutcliffe_efficiency_new.shp'

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

    # 0.5 threshold
    zero_sixty_threshold = 0
    # 0.65 threshold
    zero_eighty_threshold = 0


    # iterate over each row in the dataframe and save record
    for row in point_df.values.tolist():

        hru = row[0]
        nse = nse_dict[hru]  # <-- read entry from dictionary

        # color setting
        if nse < 0.40:
            color = colors[0]  # dark green
        elif nse < 0.45:
            color = colors[1]
        elif nse < 0.50:
            color = colors[2]
        elif nse < 0.55:
            color = colors[3]
        elif nse < 0.65:
            color = colors[4]
        else:
            color = colors[5]  # light green

        row_dict = {
            'geometry': {'type': 'Point',
                         'coordinates': (row[1], row[2])},  # lon, lat
            'properties': {'HRU': hru, 'Value': round(nse, 2), 'Color': color, 'Size': 4}
        }
        point_shp.write(row_dict)

        if nse > 0.60:
            zero_sixty_threshold += 1

        if nse > 0.80:
            zero_eighty_threshold += 1

    # close fiona object
    point_shp.close()

    print('\n')
    print('SWAT developers recommend an acceptable calibration for hydrology at a R2 > 0.6 and NSE > 0.5')
    print('source: https://www.scirp.org/journal/paperinformation.aspx?paperid=103729')
    print('\n')
    print('NSE > 0.60:', int(zero_sixty_threshold / hru_count * 100), '% total HRUs')
    print('NSE > 0.80:', int(zero_eighty_threshold / hru_count * 100), '% total HRUs')

    # average NSE
    print('Average NSE:', round(sum(nse_dict.values()) / len(nse_dict), 2))


if __name__ == '__main__':

    main()
