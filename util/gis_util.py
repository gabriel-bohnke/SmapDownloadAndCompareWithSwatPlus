"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... GIS util functions
Version.......... 1.00
Last changed on.. 02.05.2022
"""

import os
import glob
import fiona
import geopandas
from rasterio import features


def get_bounding_box_from_shp(directory):

    search_criteria = '*.shp'
    query = os.path.join(directory, search_criteria)
    shp_files = glob.glob(query)

    # use first SHP file found
    if len(shp_files) > 0:

        file = shp_files[0]

        # Fiona: get each feature extent (bounds)
        # https://gis.stackexchange.com/questions/90553/fiona-get-each-feature-extent-bounds
        # print(shape(next(iter(fiona.open(file)))['geometry']).bounds)
        source = fiona.open(file)
        crs = source.crs

        # Change shapefile coordinate system using Python
        # https://gis.stackexchange.com/questions/265589/change-shapefile-coordinate-system-using-python
        if crs['init'] != 'epsg:4326':  # WGS84
            data = geopandas.read_file(file)
            # change CRS to epsg 4326
            data = data.to_crs(epsg=4326)
            converted_file = directory + '/' + '_converted_to_wgs84.shp'  # TEMP filename
            data.to_file(converted_file)
            source = fiona.open(converted_file)

        # first record
        feature = (next(iter(source)))
        bounds = features.bounds(feature['geometry'])
        # tuple to string
        bounding_box = ','.join(map(str, bounds))
        print("bounding box:", bounding_box)

        return bounding_box

    else:
        return None
