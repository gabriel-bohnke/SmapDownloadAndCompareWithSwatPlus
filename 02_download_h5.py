"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... SMAP granules: download h5 files
Version.......... 1.00
Last changed on.. 02.05.2022
"""

import os
from util.file_util import xlsx_to_dataframe
from util.cmr_util import cmr_download
from util.performance_util import start_time_measure, end_time_measure
import glob
import shutil


# Excel -> calculate simple metrics about dates WITH coverage
# =COUNTIF(C2:C718,"<>0")   cells not zero
# =COUNTA(E2:E718)	        cells not empty


def smap_download_with_filter(selection_file, download_result_directory, polygon_selection_mode):

    # POLYGONS_COVERING_BOUNDING_BOX = False
    # ALL_POLYGONS = True
    use_all_polygons = polygon_selection_mode

    # dataframe value columns:
    # ['date', 'items', 'urls']
    df = xlsx_to_dataframe(selection_file)

    url_list = []

    # convert DataFrame to List and loop to extract all urls referenced in column 'items'
    for row in df.values.tolist():
        if use_all_polygons:
            # request download of all urls listed in column "urls"
            for url in row[2]:  # row['urls']
                url_list.append(url)  # append individual urls
        else:
            # request download of url(s) indexed in column "items"
            for item_index in row[1]:  # row[1] means row['items']
                url_list.append(row[2][int(item_index)])  # row[2][n] means nth element of row['urls']

    download_time = start_time_measure(">>> " + selection_file + " - starting h5 download...")
    cmr_download(url_list, download_result_directory)
    end_time_measure(download_time, ">>> " + selection_file + " - download time: ")


def main():

    global POLYGONS_COVERING_BOUNDING_BOX, ALL_POLYGONS

    # READY_FOR_DOWNLOAD and DOWNLOADED directories must have been created in a previous step
    ready_for_download_directory = 'B_FILTER_RESULT/B2_READY_FOR_DOWNLOAD'
    downloaded_directory = 'B_FILTER_RESULT/B3_DOWNLOADED'

    # check for existence of directory for DOWNLOAD results
    download_result_directory = 'C_DOWNLOAD_RESULT'
    if not os.path.exists(download_result_directory):
        os.makedirs(download_result_directory)

    search_criteria = '*.xlsx'
    query = os.path.join(ready_for_download_directory, search_criteria)
    selection_files = glob.glob(query)

    for xlsx_file in selection_files:
        smap_download_with_filter(xlsx_file, download_result_directory, ALL_POLYGONS)
        target_path = downloaded_directory + '/' + xlsx_file.split('\\')[-1]
        shutil.move(xlsx_file, target_path)


if __name__ == '__main__':

    # constants
    POLYGONS_COVERING_BOUNDING_BOX = False
    ALL_POLYGONS = True

    main()
