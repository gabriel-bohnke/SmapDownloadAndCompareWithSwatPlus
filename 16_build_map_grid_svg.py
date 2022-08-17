"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... build map grid in SVG format
Version.......... 1.00
Last changed on.. 01.08.2022
"""


import glob, os
import matplotlib.pyplot as plt
import matplotlib as mpl
import rasterio
import numpy as np
import svgutils.transform as sg


def create_legend_svg(svg_file_directory, target_file):

    # create normalized legend
    fig = plt.figure()
    # ax = fig.add_axes([0.02, 0.9, 0.9, 0.02])
    ax = fig.add_axes([0.5, 0.01, 0.01, 0.5])

    cb = mpl.colorbar.ColorbarBase(ax, orientation='vertical',
                                   cmap='Blues',
                                   norm=mpl.colors.Normalize(3.12, 28.72),  # vmax and vmin
                                   # extend='both',
                                   label='Humidité du sol (vol %)',
                                   ticks=[4, 7, 10, 13, 16, 19, 22, 25, 28])

    # plt.tight_layout()  # <-- check impact @TODO
    plt.savefig(f'{svg_file_directory}/{target_file}', transparent=True)
    print(f'{svg_file_directory}/{target_file} saved successfully')


def create_grid_svg(raster_directory, svg_file_directory, target_file):

    raster_list = sorted(glob.glob(f'{raster_directory}/*.tif'))

    nrows, ncols = 6, 12  # array of sub-plots
    fig_size = [8, 10]  # figure size, inches

    # create figure (fig), and grid (axs)
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=fig_size)

    # normalize color palette
    norm = mpl.colors.Normalize(vmin=0, vmax=0.5)

    # plot raster image on each cell of the grid
    for i, axi in enumerate(axs.flat):

        try:
            fig_title = os.path.basename(raster_list[i])[:-4]
            raster = rasterio.open(raster_list[i])
            raster_data = raster.read()
            image = np.reshape(raster_data, (raster_data.shape[0] * raster_data.shape[1], raster_data.shape[2]))
            axi.imshow(image, norm=norm)
            axi.set_title(fig_title, size=8)
            # https://stackoverflow.com/questions/25862026/turn-off-axes-in-subplots
            # turn axes off on resulting grid plot
            axi.axis('off')

        except IndexError:
            # if more grid cells than rasters, leave grid cells blank
            axi.axis('off')

    plt.tight_layout()  # <-- check impact @TODO
    plt.savefig(f'{svg_file_directory}/{target_file}')
    print(f'{svg_file_directory}/{target_file} saved successfully')


def assemble_svg_files(svg_file_directory, grid_file, legend_file, target_file):

    grid_svg = sg.fromfile(f'{svg_file_directory}/{grid_file}')
    legend_svg = sg.fromfile(f'{svg_file_directory}/{legend_file}')

    # get root elements for positioning
    grid_re = grid_svg.getroot()
    legend_re = legend_svg.getroot()

    # position root elements
    grid_re.moveto(0, 0)  # x, y
    legend_re.moveto(450, 100)  # x, y

    # create new SVG figure showing composition of root elements
    width, height = "18cm", "18cm"
    composed_figure = sg.SVGFigure(width, height)

    composed_figure.append([grid_re, legend_re])
    composed_figure.save(f'{svg_file_directory}/{target_file}')
    print(f'{svg_file_directory}/{target_file} saved successfully')


def main():

    grid_filename = 'raster_grid.svg'
    legend_filename = 'colorbar_ver.svg'
    composition_filename = 'composition.svg'

    # check for existence of directory for RASTER results
    svg_file_directory = 'I_SVG_FILES'
    if not os.path.exists(svg_file_directory):
        os.makedirs(svg_file_directory)

    # create legend in SVG format
    create_legend_svg(svg_file_directory, legend_filename)

    # create raster grid in SVG format
    raster_directory = 'H_RASTER_MEANS'
    create_grid_svg(raster_directory, svg_file_directory, grid_filename)

    # assemble SVG files
    assemble_svg_files(svg_file_directory, grid_filename, legend_filename, composition_filename)


if __name__ == '__main__':

    main()
