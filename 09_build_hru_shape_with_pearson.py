"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... build HRU shapefile with Pearson correlation + color code as attributes
Version.......... 1.00
Last changed on.. 02.05.2022
"""

from util.sqlite_util import read_sqlite_table, count_sqlite_table_rows
from util.soil_util import get_hru_soil_dict, get_soil_correction
import numpy as np
import fiona


def determine_pearson_correlation(series1_df, series2_df, soil_dict, unit_index):

    # filter dataframes by HRU (unit)
    series1_filter = series1_df['unit'] == unit_index
    series1_df = series1_df[series1_filter]

    series2_filter = series2_df['unit'] == unit_index
    series2_df = series2_df[series2_filter]

    # How to deal with SettingWithCopyWarning in Pandas
    # https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
    series1_copy_df = series1_df.copy()  # series1_df is passed by reference: prevent warning at mult. by scalar

    # correct SWAT+ data
    series1_df['sw_final'] = series1_df['sw_final'] / 150 + get_soil_correction(soil_dict[unit_index])

    try:
        rho = np.corrcoef(series1_copy_df['sw_final'], series2_df['soil_moisture_1km'])
        return rho
    except ValueError:
        None
        # return [[1, 0.5], [0.5, 1]]  # rho is a symmetric matrix


def main():

    # build soil dictionary only once
    soil_dict = get_hru_soil_dict('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite')

    # F_STATISTICS_INPUT directory is expected to have been created in a previous step
    sw_final_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'hru_sw_final_mon',
                                       ['period', 'unit', 'sw_final'])

    soil_moisture_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite',
                                              'hru_soil_moisture_mon',
                                              ['period', 'unit', 'soil_moisture_1km'])

    # ---------------------------------------------------------------------------------------------------------------- #
    # # test: remove SWAT+ rows for which there is no corresponding entry in SMAP
    # print(f'SWAT+ before: {sw_final_mean_df.shape[0]}')
    # sw_final_mean_df.drop((sw_final_mean_df.loc[
    #       ~(sw_final_mean_df.period.isin(soil_moisture_mean_df['period']) & sw_final_mean_df.unit.isin(
    #           soil_moisture_mean_df['unit']))]).index, inplace=True)
    # print(f'SWAT+ after: {sw_final_mean_df.shape[0]}')

    # dictionary
    hru_rho_dict = {}

    # get total number of HRUs
    hru_count = count_sqlite_table_rows('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite', 'hru_con')

    for index in range(hru_count):

        # determine correlation by HRU
        rho = determine_pearson_correlation(sw_final_mean_df, soil_moisture_mean_df, soil_dict, index + 1)

        print(index + 1, str(rho[0][1]))  # rho is a symmetric matrix
        hru_rho_dict[index + 1] = rho[0][1]  # <-- write entry to dictionary

    print('total entries', len(hru_rho_dict))

    # directory for results of SWAT+ must have been created manually + and it must contain SQLITE file with HRU info
    point_df = read_sqlite_table('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite', 'hru_con', ['id', 'lon', 'lat'])

    # statistics input directory must have been created in a previous step
    statistics_input_directory = 'F_STATISTICS_INPUT'
    shapefile_path = statistics_input_directory + '/' + 'hru_pearson_corr.shp'

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

    # iterate over each row in the dataframe and save record
    for row in point_df.values.tolist():

        hru = row[0]
        rho = hru_rho_dict[hru]  # <-- read entry from dictionary

        # color setting
        if rho < 0.40:
            color = colors[0]  # dark green
        elif rho < 0.45:
            color = colors[1]
        elif rho < 0.50:
            color = colors[2]
        elif rho < 0.55:
            color = colors[3]
        elif rho < 0.65:
            color = colors[4]
        else:
            color = colors[5]  # light green

        row_dict = {
            'geometry': {'type': 'Point',
                         'coordinates': (row[1], row[2])},  # lon, lat
            'properties': {'HRU': hru, 'Value': round(rho, 2), 'Color': color, 'Size': 4}
        }
        point_shp.write(row_dict)

    # close fiona object
    point_shp.close()

    # average Pearson correlation coefficient
    print('Average Pearson correlation coefficient:', round(sum(hru_rho_dict.values()) / len(hru_rho_dict), 2))


if __name__ == '__main__':
    main()
