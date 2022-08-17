"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... reset folders
Version.......... 1.00
Last changed on.. 02.05.2022
"""

from util.file_util import delete_complete_directory


def main():
    # delete_complete_directory('B_FILTER_RESULT')
    # delete_complete_directory('C_DOWNLOAD_RESULT')
    delete_complete_directory('D_RASTER_RESULT')
    delete_complete_directory('E_SWATPLUS_OUTPUT/HRU_SHAPEFILE')  # keep SWAT+ sqlite file


if __name__ == '__main__':
    main()


