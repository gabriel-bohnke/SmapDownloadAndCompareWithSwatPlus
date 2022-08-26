# Download of SMAP rasters and compare with SWAT+ model output

This project represents a processing pipeline of SMAP rasters and of SWAT+ model output, with itermediate storage of results after each step. Restart of pipeline is possible at any step, without having to rerun previous steps.

<b>Note before cloning project:</b> read comments in requirements.txt regarding installation of GDAL, rasterio and Fiona libraries

Details of processing steps:

<b><i>01_search_and_filter_h5.py</i></b>
- purpose: searches and filters SMAP granules
- input: explicit 'bounding_box' parameter or SHP-file in folder A_BOUNDING_BOX_INPUT
- output a): folder B_FILTER_RESULT/B1_KML_FILES with KML-files showing coverage of requested bounding box 
- output b): folder B_FILTER_RESULT/B2_READY_FOR_DOWNLOAD with XLS-files showing data selection

<b><i>02_download_h5.py</i></b>
- purpose: download SMAP H5-files
- input: folder B_FILTER_RESULT/B2_READY_FOR_DOWNLOAD with XLS-files showing data selection
- output a): folder C_DOWNLOAD_RESULT(_ALL)
- output b): XLS-files showing data selection are moved to B_FILTER_RESULT/B3_DOWNLOADED

<b><i>03_convert_h5_to_raster.py</i></b>
- purpose: convert selected band of H5-files to rasters
- input: folder C_DOWNLOAD_RESULT(_ALL)
- output a): folder D_RASTER_RESULT
- output b): XLS-files showing data selection are moved to B_FILTER_RESULT/B4_RASTERIZED

<b><i>04_build_hru_shape.py</i></b>
- purpose: build HRU shapefile, with a datapoint at center of each HRU
- input: folder E_SWATPLUS_OUTPUT, in which the SWAT+ model output "project" database has been set (E_SWATPLUS_OUTPUT/"project".sqlite)
- output: shape file E_SWATPLUS_OUTPUT/HRU_SHAPEFILE/hru_points.shp

<b><i>05_save_hru_subbasin_rel.py</i></b>
- purpose: determine HRU-subbasin relationship
- input: E_SWATPLUS_OUTPUT/<project>.sqlite
- output: new database F_STATISTICS_INPUT/swatplus_smap_merge.sqlite, table 'hru_subbasin_rel'

<b><i>06_merge_hru_daily_values.py</i></b>
- purpose: merge HRU daily values with raster band data
- input: folder D_RASTER_RESULT + SHP-file E_SWATPLUS_OUTPUT/HRU_SHAPEFILE/hru_points.shp + SWAT+ model output "result" database (E_SWATPLUS_OUTPUT/swatplus_output.sqlite)
- output: database F_STATISTICS_INPUT/swatplus_smap_merge.sqlite, table 'hru_day_values'

<b><i>07_write_monthly_means.py</i></b>
- purpose: write monthly means: by HRU and by subbasin
- input: database F_STATISTICS_INPUT/swatplus_smap_merge.sqlite, table 'hru_day_values'
- output: database F_STATISTICS_INPUT/swatplus_smap_merge.sqlite, tables 'hru_sw_final_mon' and 'hru_soil_moisture_mon' (idem for subbasin)

<b><i>08_compute_results_by_subbasin.py</i></b>
- purpose: compute results by subbasin
- input: database F_STATISTICS_INPUT/swatplus_smap_merge.sqlite, tables 'subbasin_sw_final_mon' and 'subbasin_soil_moisture_mon'
- output: plot of time series

<b><i>09_build_hru_shape_with_pearson.py</i></b>,
<b><i>10_build_hru_shape_with_NSE.py</i></b>,
<b><i>13_build_hru_shape_with_R2.py</i></b>
- purpose: build HRU shapefiles showing SWAT+/SMAP correlations using color code as attributes (for visualization in QGIS)
- input: database F_STATISTICS_INPUT/swatplus_smap_merge.sqlite, tables 'hru_sw_final_mon' and 'hru_soil_moisture_mon'
- output: SHP-files in F_STATISTICS_INPUT

<b><i>11_raster_extract_mask.py</i></b>
- purpose: apply mask extraction to rasters
- input: folder D_RASTER_RESULT
- output: folder G_RASTER_MASKS

<b><i>12_get_raster_mean_value.py</i></b>
- purpose: get raster mean by month; rasters with only partial coverage of bounding box (under a defined threshold) are rejected: they are not part of monthly mean
- input: folder G_RASTER_MASKS
- output: folder H_RASTER_MEANS

<b><i>16_build_map_grid_svg.py</i></b>
- purpose: build map grid in SVG format
- input: folder H_RASTER_MEANS
- output: folder I_SVG_FILES

<b><i>90_reset_all.py</i></b>
- purpose: delete selected directories
