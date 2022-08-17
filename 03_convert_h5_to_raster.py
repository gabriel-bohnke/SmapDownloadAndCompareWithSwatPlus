"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... convert h5 to raster
Version.......... 1.00
Last changed on.. 02.05.2022
"""

import os
from util.file_util import xlsx_to_dataframe
import h5py
import numpy as np
from osgeo import gdal, osr
import rasterio
from rasterio.merge import merge
import glob
from util.performance_util import start_time_measure, end_time_measure
from util.file_util import delete_complete_directory
import shutil


# How to fix the reprojection from EASE-2 grid product SMAP to geographic coordinates?
# https://gis.stackexchange.com/questions/253923/how-to-fix-the-reprojection-from-ease-2-grid-product-smap-to-geographic-coordina
def h5_band_to_raster(filepath_in, band, filepath_out):

    try:
        h5_file = h5py.File(filepath_in, 'r')
    except:
        h5_file = None
        print('Filepath not found: ', filepath_in)

    if h5_file:
        data = h5_file.get(band)

        extent = h5_file["/Metadata/Extent"]
        coords = extent.attrs['polygonPosList']
        lat = [coords[0], coords[4]]
        lon = [coords[1], coords[3]]

        np_data = np.array(data)
        np_lat = np.array(lat)
        np_lon = np.array(lon)

        xmin = np_lon.min()
        xmax = np_lon.max()
        ymin = np_lat.min()
        ymax = np_lat.max()

        nrows, ncols = np_data.shape
        xres = (xmax - xmin) / float(ncols)
        yres = (ymax - ymin) / float(nrows)
        geotransform = (xmin, xres, 0, ymax, 0, -yres)

        output_raster = gdal.GetDriverByName('GTiff').Create(filepath_out, ncols, nrows, 1,
                                                             gdal.GDT_Float32)  # open tif file
        output_raster.SetGeoTransform(geotransform)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)  # <-- check if this is a constant!

        output_raster.SetProjection(srs.ExportToWkt())
        output_raster.GetRasterBand(1).WriteArray(np_data)  # writes array to raster


# Creating a raster mosaic
# https://automating-gis-processes.github.io/CSC18/lessons/L6/raster-mosaic.html
def merge_rasters(directory_in, filepath_out):

    # set search criteria to select all tif files
    search_criteria = '*.tif'

    query = os.path.join(directory_in, search_criteria)

    files = glob.glob(query)

    src_files_to_mosaic = []

    for file in files:
        src = rasterio.open(file)
        src_files_to_mosaic.append(src)
        out_meta = src.meta.copy()

    # merge function returns a single mosaic array and the transformation info
    try:
        mosaic, out_trans = merge(datasets=src_files_to_mosaic, method="max")

        # show(mosaic, cmap='terrain')

        # update metadata
        out_meta.update({"driver": "GTiff",
                         "height": mosaic.shape[1],
                         "width": mosaic.shape[2],
                         "transform": out_trans,
                         "crs": "+proj=utm +zone=35 +ellps=GRS80 +units=m +no_defs "
                         }
                        )

        # write mosaic raster to disk
        with rasterio.open(filepath_out, "w", **out_meta) as dest:
            dest.write(mosaic)
    except:
        print("Mosaic merge failed for: " + filepath_out)


def convert_h5_files_to_rasters(selection_file, band, download_result_directory, raster_result_directory,
                                raster_temp_directory, polygon_selection_mode):

    conversion_time = start_time_measure(">>> " + selection_file + " - starting file conversion...")

    # POLYGONS_COVERING_BOUNDING_BOX = False
    # ALL_POLYGONS = True
    use_all_polygons = polygon_selection_mode

    # dataframe value columns:
    # ['date', 'items', 'urls']
    df = xlsx_to_dataframe(selection_file)

    # convert dataframe to list and loop to process h5 files according to column 'items'
    for row in df.values.tolist():

        # number of h5 files
        if use_all_polygons:
            number_of_h5_files = len(row[2])  # all h5 files for this date
        else:
            number_of_h5_files = len(row[1])  # only those h5 files needed to cover bounding box

        if number_of_h5_files == 1:

            # index of single polygon to use
            if use_all_polygons:
                single_polygon_index = 0
            else:
                single_polygon_index = int(row[1][0])

            # convert this h5 file to raster and save with name <current date>.tif
            url = row[2][single_polygon_index]  # the unique url to process for this date
            h5_filename = url.split('/')[-1]  # h5 filename is last term of url
            h5_filepath = download_result_directory + '/' + h5_filename
            date = row[0]
            tif_filepath = raster_result_directory + '/' + date + ".tif"  # <date>.tif
            h5_band_to_raster(h5_filepath, band, tif_filepath)

        elif number_of_h5_files > 1:

            # check for existence of directory for RASTER TEMP processing
            if not os.path.exists(raster_temp_directory):
                # if TEMP directory does not exist, create it
                os.makedirs(raster_temp_directory)
            else:
                # if TEMP directory is not empty, delete all files
                if len(os.listdir(raster_temp_directory)) != 0:
                    for filename in os.listdir(raster_temp_directory):
                        os.remove(os.path.join(raster_temp_directory, filename))

            if use_all_polygons:
                # convert all h5 files listed in column "urls" to rasters, and save them to TEMP directory
                for url in row[2]:  # row['urls']
                    h5_filename = url.split('/')[-1]  # h5 filename is last term of url
                    h5_filepath = download_result_directory + '/' + h5_filename
                    date = row[0]
                    temp_tif_filepath = raster_temp_directory + '/' + h5_filename.split('.')[
                        0] + ".tif"  # <h5 filename>.tif
                    h5_band_to_raster(h5_filepath, band, temp_tif_filepath)  # write into TEMP directory
            else:
                # convert all h5 files indexed row[1] to rasters, and save them to TEMP directory
                for item_index in row[1]:  # row[1] means row['items']
                    url = row[2][int(item_index)]  # row[2][n] means nth element of row['urls']
                    h5_filename = url.split('/')[-1]  # h5 filename is last term of url
                    h5_filepath = download_result_directory + '/' + h5_filename
                    date = row[0]
                    temp_tif_filepath = raster_temp_directory + '/' + h5_filename.split('.')[
                        0] + ".tif"  # <h5 filename>.tif
                    h5_band_to_raster(h5_filepath, band, temp_tif_filepath)  # write into TEMP directory

            # for this date, merge all rasters of TEMP directory
            tif_filepath = raster_result_directory + '/' + date + ".tif"  # <date>.tif
            merge_rasters(raster_temp_directory, tif_filepath)

    end_time_measure(conversion_time, ">>> " + selection_file + " - file conversion: ")


def main():

    global POLYGONS_COVERING_BOUNDING_BOX, ALL_POLYGONS

    # band to extract and to convert to GTiff
    band_of_interest = 'Soil_Moisture_Retrieval_Data_1km/soil_moisture_1km'

    # directory B_FILTER_RESULT/B3_DOWNLOADED must have been created in a previous step
    downloaded_directory = 'B_FILTER_RESULT/B3_DOWNLOADED'
    rasterized_directory = 'B_FILTER_RESULT/B4_RASTERIZED'

    # directory for DOWNLOAD results must have been created in a previous step
    # download_result_directory = 'C_DOWNLOAD_RESULT'
    download_result_directory = 'C_DOWNLOAD_RESULT_ALL'

    # check for existence of directory for RASTER results
    raster_result_directory = 'D_RASTER_RESULT'
    if not os.path.exists(raster_result_directory):
        os.makedirs(raster_result_directory)

    # 03_RASTER_RESULT/TEMP directory is used to gather all rasters of one day that need to be merged
    raster_temp_directory = 'D_RASTER_RESULT/TEMP'

    search_criteria = '*.xlsx'
    query = os.path.join(downloaded_directory, search_criteria)
    selection_files = glob.glob(query)

    for xlsx_file in selection_files:
        convert_h5_files_to_rasters(xlsx_file, band_of_interest, download_result_directory, raster_result_directory,
                                    raster_temp_directory, ALL_POLYGONS)  # <-- adapt this, if needed
        target_path = rasterized_directory + '/' + xlsx_file.split('\\')[-1]
        shutil.move(xlsx_file, target_path)

    # finally, delete TEMP directory
    delete_complete_directory(raster_temp_directory)


if __name__ == '__main__':

    # constants
    POLYGONS_COVERING_BOUNDING_BOX = False
    ALL_POLYGONS = True

    main()
