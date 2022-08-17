import sqlite3
import pandas as pd


def get_hru_soil_dict(database_filepath):

    # Connect to SQLite database
    conn = sqlite3.connect(database_filepath)

    # create cursor object
    cursor = conn.cursor()

    # Query for INNER JOIN: hru_data_hru > soils_sol
    sql = '''SELECT hru_data_hru.id, soils_sol.name
    from hru_data_hru
    INNER JOIN soils_sol
    ON hru_data_hru.soil_id = soils_sol.id;'''

    # executing the query
    cursor.execute("select name from sqlite_master where type='table';")

    # transfer rows to dataframe
    hru_soil_df = pd.read_sql_query(sql, conn)

    # closing the connection
    conn.close()

    print(hru_soil_df.head())

    soil_dict = dict(hru_soil_df.values)

    return soil_dict


def get_soil_correction(soil):

    soil_corrections = {
        'S-700': 0.1674,
        'S-701': 0.00716,
        'S-702': 0.0816,
        'S-703': 0.07672,
        'S-705': 0.109772,
        'S-706': 0.1528096,
        'S-708': 0.145,
        'S-709': 0.206856,
        'S-711': 0.07672,
        'S-714': 0.07672
    }

    return soil_corrections[soil]