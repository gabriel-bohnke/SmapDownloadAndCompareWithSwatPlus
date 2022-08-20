"""
Author........... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... compute results by subbasin
Version.......... 1.00
Last changed on.. 02.05.2022
"""

from util.sqlite_util import read_sqlite_table
import matplotlib.pyplot as plt


def plot_subbasin_data(series1_df, series2_df, subbasin_index):

    # How To Filter Pandas Dataframe By Values of Column?
    # https://cmdlinetips.com/2018/02/how-to-subset-pandas-dataframe-based-on-values-of-a-column/

    # filter dataframes by subbasin ID, e.g. 15
    series1_filter = series1_df['subbasin'] == subbasin_index
    series1_df = series1_df[series1_filter]

    series2_filter = series2_df['subbasin'] == subbasin_index
    series2_df = series2_df[series2_filter]

    # How to Plot a Time Series in Matplotlib
    # https://www.statology.org/matplotlib-time-series/

    # How to plot single data with two Y-axes (two units) in Matplotlib?
    # https://www.tutorialspoint.com/how-to-plot-single-data-with-two-y-axes-two-units-in-matplotlib

    ax1 = plt.subplot()
    l1, = ax1.plot(series1_df['period'], series1_df['sw_final'],
                   linewidth=3, color='red')
    ax2 = ax1.twinx()
    l2, = ax2.plot(series2_df['period'], series2_df['soil_moisture_1km'],
                   linewidth=3, color='blue')
    plt.legend([l1, l2], ["sw_final", "soil_moisture_1km"])
    plt.show()


def main():

    # F_STATISTICS_INPUT directory is expected to have been created in a previous step
    sw_final_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'subbasin_sw_final_mon',
                                         ['period', 'subbasin', 'sw_final'])

    soil_moisture_mean_df = read_sqlite_table('F_STATISTICS_INPUT/swatplus_smap_merge.sqlite', 'subbasin_soil_moisture_mon',
                                         ['period', 'subbasin', 'soil_moisture_1km'])

    for index in range(19):  # could be dynamic

        # plot
        plot_subbasin_data(sw_final_mean_df, soil_moisture_mean_df, index)


if __name__ == '__main__':

    main()
