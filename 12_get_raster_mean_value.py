"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... get raster mean by month
Version.......... 1.00
Last changed on.. 29.05.2022
"""

# Computing mean of all rasters in a directory using python
# https://gis.stackexchange.com/questions/244376/computing-mean-of-all-rasters-in-a-directory-using-python
import os
import glob
import rasterio
import numpy as np


def get_raster_shape(file):
    with rasterio.open(file) as src:
        data = src.read(1)
        return np.array(data).shape


def is_outlier(file, height, width, threshold):
    with rasterio.open(file) as src:
        data = src.read(1)
        shape = np.array(data).shape
        if shape[0] < height * threshold or shape[1] < width * threshold:
            return True
        else:
            return False


def get_raster_cleaned(file, median_shape):
    with rasterio.open(file) as src:
        data = src.read(1)
        shape = np.array(data).shape
        if shape[0] >= median_shape[0] and shape[1] >= median_shape[1]:
            raster = src.read(1)[0:median_shape[0], 0:median_shape[1]]
            raster[raster == -9999.0] = np.nan
            raster[raster == 0] = np.nan
            return raster
        else:
            return None


def save_averaged_raster(filepath_out, raster, meta):

    meta.update(dtype=rasterio.float32)

    # write output file
    with rasterio.open(filepath_out, 'w', **meta) as dst:
        dst.write(raster.astype(rasterio.float32), 1)

def main():

    # set search criteria to select all tif files
    search_criteria = '*.tif'
    query = os.path.join('G_RASTER_MASKS', search_criteria)
    file_paths_in = glob.glob(query)

    # 1) get mean/median shape values
    input_files = 0
    raster_shapes = []
    for file in file_paths_in:
        input_files += 1
        shape = get_raster_shape(file)
        raster_shapes.append(shape)

    array = np.array(raster_shapes)
    array = array.transpose()
    print(array)

    # mean values
    mean_height = array[0].mean()
    mean_width = array[1].mean()
    print('mean height: ', mean_height)
    print('mean width: ', mean_width)

    # median values
    median_height = np.median(array[0])
    median_width = np.median(array[1])
    print('median height: ', median_height)
    print('median width: ', median_width)

    threshold = 0.98  # best compromise on shape crop/raster loss
    mean_outliers = 0
    median_outliers = 0
    smallest_shape_on_mean = None
    smallest_shape_on_median = None

    # 2) list outliers from mean/median values and determine best compromise on shape crop/raster loss
    for file in file_paths_in:

        is_outlier_on_mean = is_outlier(file, mean_height, mean_width, threshold)
        if is_outlier_on_mean:
            mean_outliers += 1
            # print('outlier of mean:', file)
        else:
            shape = get_raster_shape(file)
            if smallest_shape_on_mean is None:
                smallest_shape_on_mean = shape
            else:
                smallest_shape_on_mean = (
                min(shape[0], smallest_shape_on_mean[0]), min(shape[1], smallest_shape_on_mean[1]))

        is_outlier_on_median = is_outlier(file, median_height, median_width, threshold)
        if is_outlier_on_median:
            median_outliers += 1
            # print('outlier of median:', file)
            # if is_outlier_on_mean != is_outlier_on_median:
            #     print('<<<<<<')
        else:
            shape = get_raster_shape(file)
            if smallest_shape_on_median is None:
                smallest_shape_on_median = shape
            else:
                smallest_shape_on_median = (
                min(shape[0], smallest_shape_on_median[0]), min(shape[1], smallest_shape_on_median[1]))

    print('total number of input files: ', input_files)
    print('number of mean outliers: ', threshold, mean_outliers)
    print('number of median outliers : ', threshold, median_outliers)
    print('smallest shape on mean: ', threshold, smallest_shape_on_mean)
    print('smallest shape on median: ', threshold, smallest_shape_on_median)  # <-- this one, with threshold 0.98

    # 3) read all data as a list of numpy arrays

    # get metadata from one of the input files
    with rasterio.open(file_paths_in[0]) as src:
        meta = src.meta

    raster_list_by_month = []

    previous_year = None
    previous_month = None

    for file in file_paths_in:
        # G_RASTER_MASKS\2020-11-26.tif
        year = file.split('\\')[1].split('-')[0]
        month = file.split('\\')[1].split('-')[1]
        if previous_year is None and previous_month is None:  # first entry in loop
            previous_year = year
            previous_month = month
            raster = get_raster_cleaned(file, smallest_shape_on_median)
            if raster is not None:  # not interested in outliers
                raster_list_by_month.append(raster)
        else:
            if month != previous_month:
                # processing for previous month
                # perform average on previous month
                averaged_raster = np.nanmean(raster_list_by_month, axis=0)
                # save averaged raster
                filepath_out = 'H_RASTER_MEANS/' + previous_year + '-' + previous_month + '.tif'
                save_averaged_raster(filepath_out, averaged_raster, meta)
                # reset raster list
                raster_list_by_month = []

                # processing for new month
                previous_month = month
                # has the year changed?
                if year != previous_year:
                    previous_year = year
                # fill a new raster list for current month
                raster = get_raster_cleaned(file, smallest_shape_on_median)
                if raster is not None:  # not interested in outliers
                    raster_list_by_month.append(raster)
            else:
                # add raster to current month
                raster = get_raster_cleaned(file, smallest_shape_on_median)
                if raster is not None:  # not interested in outliers
                    raster_list_by_month.append(raster)

    # last month has no follower => explicit processing
    # perform average on previous month
    averaged_raster = np.nanmean(raster_list_by_month, axis=0)
    # and save last year/month entry
    filepath_out = 'H_RASTER_MEANS/' + previous_year + '-' + previous_month + '.tif'
    save_averaged_raster(filepath_out, averaged_raster, meta)


if __name__ == '__main__':
    main()
