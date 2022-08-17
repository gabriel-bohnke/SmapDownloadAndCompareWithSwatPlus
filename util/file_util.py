"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... file util functions
Version.......... 1.00
Last changed on.. 02.05.2022
"""

import pandas as pd
import os
import shutil


# Delete all files in a directory in Python
# https://www.techiedelight.com/delete-all-files-directory-python/
def delete_complete_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
        print(directory + ' deleted')


def xlsx_to_dataframe(filepath):

    # requires openpyxl
    df = pd.read_excel(filepath, dtype=str)  # force dtype to string for all columns

    # Python pandas: how to specify data types when reading an Excel file?
    # https://stackoverflow.com/questions/32591466/python-pandas-how-to-specify-data-types-when-reading-an-excel-file
    # # Assuming data types for `a` and `b` columns to be altered
    # pd.read_excel('file_name.xlsx', dtype={'a': np.float64, 'b': np.int32})

    # print(rows.shape[0])

    # # original dataframe, as specified before download
    # flattened_date_set = pd.DataFrame(flattened_entries,
    #                                   columns=['date', 'KML filename', 'nb_required_polygons', 'nb_total_polygons',
    #                                            'coverage_item_list', 'coverage_url_list'])

    # item lists were saved in Excel to single cells as PIPE-separated strings (|)
    # this function reconverts PIPE-separated strings to Python lists
    def pipe_separated_to_list(x):
        # Check for NaN values in Python
        # https://www.techiedelight.com/check-for-nan-values-python/#:~:text=isnan()%20function,a%20NaN%20and%20False%20otherwise.
        if not pd.isna(x):
            return str(x).split('|')
        else:
            return []

    # date_items['items'] = date_items['coverage_item_list'].apply(lambda x: str(x).split('|'))  # issue with NaN values
    df['items'] = df['coverage_item_list'].apply(pipe_separated_to_list)
    df['urls'] = df['coverage_url_list'].apply(pipe_separated_to_list)

    # keep columns of interest
    df = df[['date', 'items', 'urls']]

    return df
