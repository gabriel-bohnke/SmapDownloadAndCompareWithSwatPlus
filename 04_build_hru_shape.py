"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... build HRU shapefile
Version.......... 1.00
Last changed on.. 02.05.2022
"""

from util.sqlite_util import read_sqlite_table
import os
import fiona


def main():

    # directory for results of SWAT+ must have been created manually + and it must contain SQLITE file with HRU info
    point_df = read_sqlite_table('E_SWATPLUS_OUTPUT/SWAT_Tunisie107.sqlite', 'hru_con', ['id', 'lon', 'lat'])

    print(point_df.head(10))

    # check for existence of directory for HRU shapefile
    hru_shapefile_directory = 'E_SWATPLUS_OUTPUT/HRU_SHAPEFILE/'
    if not os.path.exists(hru_shapefile_directory):
        os.makedirs(hru_shapefile_directory)

    shapefile_path = hru_shapefile_directory + 'hru_points.shp'

    # define schema
    schema = {
        'geometry': 'Point',
        'properties': [('HRU', 'str')]  # one property named HRU, of type string (str)
    }

    # structure of fiona object

    # fiona.open(fp, mode='r', driver=None, schema=None, crs=None, encoding=None, layer=None, vfs=None, enabled_drivers=None,
    #            crs_wkt=None, **kwargs, )

    # open a fiona object
    point_shp = fiona.open(shapefile_path, mode='w', driver='ESRI Shapefile',
                           schema=schema, crs="EPSG:4326")  # crs could be a variable

    # iterate over each row in the dataframe and save record
    for row in point_df.values.tolist():
        row_dict = {
            'geometry': {'type': 'Point',
                         'coordinates': (row[1], row[2])},  # lon, lat
            'properties': {'HRU': row[0]},
        }
        point_shp.write(row_dict)

    # close fiona object
    point_shp.close()


if __name__ == '__main__':
    main()
