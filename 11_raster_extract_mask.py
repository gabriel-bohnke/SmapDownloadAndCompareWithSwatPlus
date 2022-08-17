"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... apply mask extraction to raster
Version.......... 1.00
Last changed on.. 29.05.2022
"""

import os
import glob
import fiona
import rasterio
from rasterio.mask import mask


def extract(filepath_in):
    with fiona.open("A_BOUNDING_BOX_INPUT/_converted_to_wgs84.shp", "r") as shapefile:
        geoms = [feature["geometry"] for feature in shapefile]

    with rasterio.open(filepath_in) as src:
        out_image, out_transform = mask(src, geoms, crop=True)
        out_meta = src.meta.copy()

    out_meta.update({"driver": "GTiff",
                     "height": out_image.shape[1],
                     "width": out_image.shape[2],
                     "transform": out_transform})

    filepath_out = 'G_RASTER_MASKS/' + filepath_in.split('\\')[1]
    with rasterio.open(filepath_out, "w", **out_meta) as dest:
        dest.write(out_image)
        print('Masked raster saved:', filepath_out)


def main():
    # set search criteria to select all tif files
    search_criteria = '*.tif'
    query = os.path.join('D_RASTER_RESULT', search_criteria)
    file_paths_in = glob.glob(query)

    for file in file_paths_in:
        extract(file)


if __name__ == '__main__':
    main()
