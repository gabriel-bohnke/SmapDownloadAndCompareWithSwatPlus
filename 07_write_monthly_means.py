"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... write monthly means: by HRU and by subbasin
Version.......... 1.00
Last changed on.. 02.05.2022
"""

from util.sqlite_util import read_sqlite_table
import sqlite3

def get_dataframes_with_means(daily_values_df, aggregation_by):

    # add columns before any groupby/mean processing
    daily_values_df['period'] = daily_values_df[['yr', 'mon']].apply(
        lambda x: str(int(x[0])) + '-' + str(int(x[1])).zfill(2), axis=1)

    # sw_final mean
    sw_final_mean_df = daily_values_df.groupby(['period', aggregation_by])['sw_final'].mean().reset_index()
    print(sw_final_mean_df.head(10))

    # Pandas dataframe filter with Multiple conditions
    # https://kanoki.org/2020/01/21/pandas-dataframe-filter-with-multiple-conditions/
    valid_values_df = daily_values_df.loc[
        (daily_values_df['soil_moisture_1km'] != 0) & (daily_values_df['soil_moisture_1km'] != -9999.0)]
    print(valid_values_df.shape[0])

    # after groupby/mean, with reset_index(), we restore the DataFrame format to the previous form
    soil_moisture_mean_df = valid_values_df.groupby(['period', aggregation_by])['soil_moisture_1km'].mean().reset_index()
    print(soil_moisture_mean_df.head(10))

    return sw_final_mean_df, soil_moisture_mean_df


def main():

    # F_STATISTICS_INPUT directory is expected to have been created in a previous step
    merged_values_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'hru_day_values',
                                         ['swat_date', 'yr', 'mon', 'unit', 'sw_final', 'sw_ave', 'sw_init', 'soil_moisture_1km', 'subbasin'])

    statistics_input_directory = 'F_STATISTICS_INPUT'
    database_filepath_out = statistics_input_directory + '/' + 'swatplus_smap_merge.sqlite'

    con = sqlite3.connect(database_filepath_out)

    # group by period + hru
    sw_final_mean_df, soil_moisture_mean_df = get_dataframes_with_means(merged_values_df, 'unit')
    sw_final_mean_df.to_sql('hru_sw_final_mon', con, if_exists="replace")
    soil_moisture_mean_df.to_sql('hru_soil_moisture_mon', con, if_exists="replace")

    # group by period + subbasin
    sw_final_mean_df, soil_moisture_mean_df = get_dataframes_with_means(merged_values_df, 'subbasin')
    sw_final_mean_df.to_sql('subbasin_sw_final_mon', con, if_exists="replace")
    soil_moisture_mean_df.to_sql('subbasin_soil_moisture_mon', con, if_exists="replace")

    con.close()
    print('dataframe(s) saved to: ' + database_filepath_out)


if __name__ == '__main__':
    main()
