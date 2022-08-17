"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... sqlite util functions
Version.......... 1.00
Last changed on.. 02.05.2022
"""

import sqlite3
import pandas as pd


def table_columns(db, table_name):

    cursor = db.cursor()
    sql = "select * from %s where 1=0;" % table_name
    cursor.execute(sql)
    return [d[0] for d in cursor.description]


def read_sqlite_table(database_filepath, table, columns):

    # connect to SQLite database
    conn = sqlite3.connect(database_filepath)

    # create cursor object
    cursor = conn.cursor()

    # executing the query
    cursor.execute("select name from sqlite_master where type='table';")

    # transfer rows to dataframe
    table_columns(conn, table)
    select_statement = 'SELECT ' + ', '.join(columns) + ' FROM ' + table
    result_df = pd.read_sql_query(select_statement, conn)

    # close connection
    conn.close()

    # return dataframe
    return result_df


def count_sqlite_table_rows(database_filepath, table):

    # connect to SQLite database
    conn = sqlite3.connect(database_filepath)

    # create cursor object
    cursor = conn.cursor()

    # count number of rows
    result = cursor.execute('SELECT COUNT() FROM ' + table).fetchone()[0]

    # close connection
    conn.close()

    # return row count
    return result
