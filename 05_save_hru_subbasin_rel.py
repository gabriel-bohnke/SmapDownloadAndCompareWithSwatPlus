"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... save HRU-subbasin relationship
Version.......... 1.00
Last changed on.. 02.05.2022
"""

import sqlite3
import pandas as pd
import os


def main():

    # Connect to SQLite database
    conn = sqlite3.connect('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite')

    # create cursor object
    cursor = conn.cursor()

    # Query for INNER JOIN: gis_hrus > gis_lsus > gis_channels (gis_channels contains subbasin information)
    sql = '''SELECT gis_hrus.id, gis_channels.subbasin
    FROM gis_hrus 
    INNER JOIN gis_lsus
    ON gis_hrus.lsu = gis_lsus.id
    INNER JOIN gis_channels
    ON gis_lsus.channel = gis_channels.id;'''

    # executing the query
    cursor.execute("select name from sqlite_master where type='table';")

    # transfer rows to dataframe
    hru_subbasin_df = pd.read_sql_query(sql, conn)

    # closing the connection
    conn.close()

    for row in hru_subbasin_df.iterrows():
        print(row[1].id, row[1].subbasin)

    print('total number of HRUs assigned to subbasins: ', hru_subbasin_df.shape[0])

    # database filepath OUT
    statistics_input_directory = 'F_STATISTICS_INPUT'
    if not os.path.exists(statistics_input_directory):
        os.makedirs(statistics_input_directory)

    # new sqlite database
    database_filepath_out = 'F_STATISTICS_INPUT/swatplus_smap_merge.sqlite'

    con = sqlite3.connect(database_filepath_out)
    hru_subbasin_df.to_sql('hru_subbasin_rel', con, if_exists="replace")
    con.close()
    print('\n')
    print('dataframe saved to: ' + database_filepath_out)


if __name__ == '__main__':
    main()