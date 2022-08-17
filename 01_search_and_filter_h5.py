"""
Author........... Marnik Vanclooster
Modified by...... Gabriel Böhnke
University....... UCLouvain, Faculty of bioscience engineering
Email............ gabriel.bohnke@student.uclouvain.be

Description...... SMAP granules: search and filter
Version.......... 1.00
Last changed on.. 02.05.2022
"""

# !/usr/bin/env python
# ------------------------------------------------------------------------------
# NSIDC Data Download Script
# Tested in Python 2.7 and Python 3.4, 3.6, 3.7
#
# To run the script at a Linux, macOS, or Cygwin command-line terminal:
#   $ python nsidc-data-draw.py
#
# On Windows, open Start menu -> Run and type cmd. Then type:
#     python nsidc-data-draw.py
#
# The script will first search Earthdata for all matching files.
# You will then be prompted for your Earthdata username/password
# and the script will download the matching files.
#
# If you wish, you may store your Earthdata username/password in a .netrc
# file in your $HOME directory and the script will automatically attempt to
# read this file. The .netrc file should have the following format:
#    machine urs.earthdata.nasa.gov login myusername password mypassword
# where 'myusername' and 'mypassword' are your Earthdata credentials.

from __future__ import print_function

import base64
import json
import netrc
import ssl
import sys
from getpass import getpass
import datetime
from shapely.geometry import Polygon
from shapely.ops import unary_union
from itertools import combinations
import pandas as pd
import copy
import os
from util.performance_util import start_time_measure, end_time_measure
from util.gis_util import get_bounding_box_from_shp

try:
    from urllib.parse import urlparse
    from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor
    from urllib.error import HTTPError, URLError
except ImportError:
    from urlparse import urlparse
    from urllib2 import urlopen, Request, HTTPError, URLError, build_opener, HTTPCookieProcessor

def get_username():
    username = ''

    # For Python 2/3 compatibility:
    try:
        do_input = raw_input  # noqa
    except NameError:
        do_input = input

    while not username:
        try:
            username = do_input('Earthdata username: ')
        except KeyboardInterrupt:
            quit()
    return username


def get_password():
    password = ''
    while not password:
        try:
            password = getpass('password: ')
        except KeyboardInterrupt:
            quit()
    return password


def get_credentials(url):
    """Get user credentials from .netrc or prompt for input."""
    credentials = None
    errprefix = ''
    try:
        info = netrc.netrc()
        username, account, password = info.authenticators(urlparse(URS_URL).hostname)
        errprefix = 'netrc error: '
    except Exception as e:
        if (not ('No such file' in str(e))):
            print('netrc error: {0}'.format(str(e)))
        username = None
        password = None

    while not credentials:
        if not username:
            username = get_username()
            password = get_password()
        credentials = '{0}:{1}'.format(username, password)
        credentials = base64.b64encode(credentials.encode('ascii')).decode('ascii')

        if url:
            try:
                req = Request(url)
                req.add_header('Authorization', 'Basic {0}'.format(credentials))
                opener = build_opener(HTTPCookieProcessor())
                opener.open(req)
            except HTTPError:
                print(errprefix + 'Incorrect username or password')
                errprefix = ''
                credentials = None
                username = None
                password = None

    return credentials


def build_version_query_params(version):
    desired_pad_length = 3
    if len(version) > desired_pad_length:
        print('Version string too long: "{0}"'.format(version))
        quit()

    version = str(int(version))  # Strip off any leading zeros
    query_params = ''

    while len(version) <= desired_pad_length:
        padded_version = version.zfill(desired_pad_length)
        query_params += '&version={0}'.format(padded_version)
        desired_pad_length -= 1
    return query_params


def build_cmr_query_url(short_name, version, time_start, time_end,
                        bounding_box=None, polygon=None,
                        filename_filter=None):
    params = '&short_name={0}'.format(short_name)
    params += build_version_query_params(version)
    params += '&temporal[]={0},{1}'.format(time_start, time_end)
    if polygon:
        params += '&polygon={0}'.format(polygon)
    elif bounding_box:
        params += '&bounding_box={0}'.format(bounding_box)
    if filename_filter:
        option = '&options[producer_granule_id][pattern]=true'
        params += '&producer_granule_id[]={0}{1}'.format(filename_filter, option)
    return CMR_FILE_URL + params


def cmr_download(urls):
    """Download files from list of urls."""
    if not urls:
        return

    url_count = len(urls)
    print('Downloading {0} files...'.format(url_count))
    credentials = None

    for index, url in enumerate(urls, start=1):
        if not credentials and urlparse(url).scheme == 'https':
            credentials = get_credentials(url)

        filename = url.split('/')[-1]
        print('{0}/{1}: {2}'.format(str(index).zfill(len(str(url_count))),
                                    url_count,
                                    filename))

        try:
            # In Python 3 we could eliminate the opener and just do 2 lines:
            # resp = requests.get(url, auth=(username, password))
            # open(filename, 'wb').write(resp.content)
            req = Request(url)
            if credentials:
                req.add_header('Authorization', 'Basic {0}'.format(credentials))
            opener = build_opener(HTTPCookieProcessor())
            data = opener.open(req).read()
            open(filename, 'wb').write(data)
        except HTTPError as e:
            print('HTTP error {0}, {1}'.format(e.code, e.reason))
        except URLError as e:
            print('URL error: {0}'.format(e.reason))
        except IOError:
            raise
        except KeyboardInterrupt:
            quit()


########################################################################################################################

# initial search url
# https://cmr.earthdata.nasa.gov/search/granules.json?provider=NSIDC_ECS&sort_key[]=start_date&sort_key[]=producer_granule_id&scroll=true&page_size=2000&short_name=SPL2SMAP_S&version=003&version=03&version=3&temporal[]=2021-03-01T00:00:00Z,2021-03-31T00:00:00Z&bounding_box=9.0,35.7,9.8,36.6

# url of one h5 file:
# https://n5eil01u.ecs.nsidc.org/DP4/SMAP/SPL2SMAP_S.003/2021.03.01/SMAP_L2_SM_SP_1BIWDV_20210301T053807_20210302T172013_009E36N_R17000_001.h5

# display KML file as follows:
#
# open https://www.google.com/maps in Chrome
# open menu (left top corner) > Your places > click on "Maps" header > "Create Map" (bottom of page)
# Click on "Import" > drag your KML file onto import area (works directly from PyCharm)
# On Settings popup (top left) click on "Individual styles" > Set labels > name > click on any polygon icon to highlight corresponding polygon


def filter_polygons(search_results):
    if 'feed' not in search_results or 'entry' not in search_results['feed']:
        return []

    time_start_entries = [e['time_start']
                          for e in search_results['feed']['entry']
                          if 'time_start' in e]

    # assumption: only 1 polygon per feed entry
    polygon_entries = [e['polygons'][0][0]  # note: each polygon entry is surrounded by square brackets
                       for e in search_results['feed']['entry']
                       if 'polygons' in e]

    # assumption: h5 file come as first link
    link_entries = [e['links'][0]
                    for e in search_results['feed']['entry']
                    if 'links' in e]

    # combine n flat lists into an array: zip
    polygon_infos = list(zip(time_start_entries, polygon_entries, link_entries))

    return polygon_infos


def split_polygon_infos_by_date(polygon_infos):
    last_date = None
    date_polygon_infos = []
    polygon_infos_by_date = []

    for item in polygon_infos:

        date = datetime.datetime.strptime(item[0], '%Y-%m-%dT%H:%M:%S.%fZ').strftime("%Y-%m-%d")

        # all date changes, before last date
        if last_date is not None and date != last_date:
            filename = last_date + '.kml'
            polygon_infos_by_date.append([last_date, filename, date_polygon_infos])
            date_polygon_infos = []

        date_polygon_infos.append(item)

        last_date = date

    # process last date
    filename = last_date + '.kml'
    polygon_infos_by_date.append([last_date, filename, date_polygon_infos])

    return polygon_infos_by_date


def get_all_polygon_combinations(list_of_polygons):
    # get a list of discrete ascending numbers, e.g. [0, 1, 2, 3, 4] for a list of 5 polygons
    elements = list(range(len(list_of_polygons)))
    # get all possible combinations, e.g. [[], [0], [1], [2], [3], [4], [0, 1], [0, 2], [0, 3],...]
    result = sum([list(map(list, combinations(elements, i))) for i in range(len(elements) + 1)], [])
    # remove first element, because empty: []
    result.pop(0)

    return result


def get_polygon(coordinate_string):
    # lat/long NSIDC format
    n_coords = coordinate_string.split()

    # create polygon (coordinates in lon/lat GIS format)
    g_coords = [(float(n_coords[1]), float(n_coords[0])), (float(n_coords[3]), float(n_coords[2])),
                (float(n_coords[5]), float(n_coords[4])),
                (float(n_coords[7]), float(n_coords[6]))]

    result = Polygon(g_coords)
    return result


def get_bounding_box_coverage_info(bounding_box, polygon_infos_by_date, kml_file_generation):
    date_set = []

    # bounding box
    coordinate_string = convert_bounding_box_to_coordinate_string(bounding_box)
    bb_polygon = get_polygon(coordinate_string)

    for single_date in polygon_infos_by_date:

        list_of_polygons = single_date[2]

        polygon_combinations = get_all_polygon_combinations(list_of_polygons)

        including_combination = []
        for combination in polygon_combinations:

            if len(combination) == 1:
                # check if bounding box is included in primary polygon
                combination_index = combination[0]
                coordinate_string = list_of_polygons[combination_index][1]
                primary_polygon = get_polygon(coordinate_string)
                bb_is_included = bb_polygon.within(primary_polygon)
                if bb_is_included:
                    including_combination = combination
                    break
            else:
                # check if bounding box is included in union of polygons
                polygons = []
                polygon_union = None  # necessary?
                for combination_index in combination:
                    coordinate_string = list_of_polygons[combination_index][1]
                    participating_polygon = get_polygon(coordinate_string)
                    polygons.append(participating_polygon)
                polygon_union = unary_union(polygons)
                bb_is_included = bb_polygon.within(polygon_union)
                if bb_is_included:
                    including_combination = combination
                    break

        # add include info to filename, for human readability
        # old: 2021-09-04.kml
        # new: 2021-09-04 ~ 2 from 5 polygons.kml
        filename_parts = single_date[1].split('.')

        item_with_include_info = [single_date[0],
                                  filename_parts[0] + ' ~ ' + str(len(including_combination)) + ' from ' +
                                  str(len(single_date[2])) + ' polygons.' + filename_parts[1], single_date[2],
                                  including_combination]

        date_set.append(item_with_include_info)

    # data structures are ready for KML file generation
    if kml_file_generation is True:
        generate_kml_files(date_set)

    # flatten date_set for export to Excel: 1 row per date, even if multiple polygons
    if date_set is not None:

        flattened_entries = []
        for date_entry in date_set:
            flattened_entry = [date_entry[0],  # date
                               date_entry[1],  # KML filename
                               len(date_entry[3]),  # number of required polygons for coverage
                               len(date_entry[2]),  # total number of polygons for this date
                               '|'.join(str(item) for item in date_entry[3]),  # coverage items separated by |
                               '|'.join(str(item[2]['href']) for item in date_entry[2])]  # coverage urls separated by |
            flattened_entries.append(flattened_entry)

        # create dataframe
        flattened_date_set = pd.DataFrame(flattened_entries,
                                          columns=['date', 'KML filename', 'nb_required_polygons', 'nb_total_polygons',
                                                   'coverage_item_list', 'coverage_url_list'])

    else:
        flattened_date_set = None

    return flattened_date_set


def convert_bounding_box_to_coordinate_string(bounding_box):
    bb_coordinates = bounding_box.split(',')

    # 1) coordinates of requested bounding box
    # nodes are defined in following sequence (lon, lat) : SW > NE
    # example: 9.0,35.7,9.8,36.6
    # bb_coordinates array indexes:
    # [0]   9.0   lon SW node (= lon NW)
    # [1]   35.7  lat SW node (= lat SE)
    # [2]   9.8   lon NE node (= lon SE)
    # [3]   36.6  lat NE node (= lat NW)

    # 2) NSIDC polygon coordinates
    # nodes are defined in following sequence (lat, lon): NW > SW > SE > NE > NW
    # example:
    # lat        lon       lat        lon       lat        lon        lat        lon        lat        lon
    # 0          1         2          3         4          5          6          7          8          9
    # 37.8691406 7.8475103 35.8586655 7.8475103 35.8586655 11.1981325 37.8691406 11.1981325 37.8691406 7.8475103

    polygon_ref_string = bb_coordinates[3] + " "  # lat NW node
    polygon_ref_string += bb_coordinates[0] + " "  # lon NW node
    polygon_ref_string += bb_coordinates[1] + " "  # lat SW node
    polygon_ref_string += bb_coordinates[0] + " "  # lon SW node
    polygon_ref_string += bb_coordinates[1] + " "  # lat SE node
    polygon_ref_string += bb_coordinates[2] + " "  # lon SE node
    polygon_ref_string += bb_coordinates[3] + " "  # lat NE node
    polygon_ref_string += bb_coordinates[2] + " "  # lon NE node
    polygon_ref_string += bb_coordinates[3] + " "  # lat NW node
    polygon_ref_string += bb_coordinates[0]  # lon NW node

    return polygon_ref_string


def generate_kml_files(date_items):
    # links = []
    #
    # total_days_with_images = 0
    # days_with_valid_images = 0
    #
    # polygon_infos = filter_polygons(search_results)
    #
    # if polygon_infos:
    #
    #     # split polygon list by date
    #     date_items = split_polygon_infos_by_date(polygon_infos)
    #
    #     # add bounding box coverage info
    #     date_items = get_bounding_box_coverage_info(bounding_box, date_items)  # <--

    # check for existence of directory for filter results / KML files
    kml_file_directory = 'B_FILTER_RESULT/B1_KML_FILES'

    if not os.path.exists(kml_file_directory):
        os.makedirs(kml_file_directory)

    # copy variable value (not its reference), because we are going to add requested bounding box to polygon list
    date_items_deep_copy = copy.deepcopy(date_items)

    for date_item in date_items_deep_copy:

        filename = date_item[1]
        polygons = date_item[2]
        # coverage_info = date_item[3]

        xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_string += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        xml_string += '\t<Document id="smap_data">\n'

        # transparent polygon colors in ABGR format: alpha = opacity (%age of 255 in hex) + BGR
        # red     7d0000ff
        # yellow  7d00ffff
        # blue    7dff0000 (opacity 7d = 125 = 50% of 255)
        # green   bf00ff00 (opacity bf = 191 = 75% of 255)
        # etc...

        # style to color requested bounding box
        xml_string += '\t\t<Style id="transBluePoly">\n'
        xml_string += '\t\t\t<LineStyle>\n'
        xml_string += '\t\t\t\t<width>1.5</width>\n'
        xml_string += '\t\t\t</LineStyle>\n'
        xml_string += '\t\t\t<PolyStyle>\n'
        xml_string += '\t\t\t\t<color>bf994c00</color>\n'  # opacity 75%, dark blue
        xml_string += '\t\t\t</PolyStyle>\n'
        xml_string += '\t\t</Style>\n'

        # style to color list of polygons that fully cover requested bounding box
        xml_string += '\t\t<Style id="transOrangePoly">\n'
        xml_string += '\t\t\t<LineStyle>\n'
        xml_string += '\t\t\t\t<width>1.5</width>\n'
        xml_string += '\t\t\t</LineStyle>\n'
        xml_string += '\t\t\t<PolyStyle>\n'
        xml_string += '\t\t\t\t<color>7d3399ff</color>\n'  # opacity 50%, orange
        xml_string += '\t\t\t</PolyStyle>\n'
        xml_string += '\t\t</Style>\n'

        # prepare coordinates of requested bounding box for KML file
        coordinate_string = convert_bounding_box_to_coordinate_string(bounding_box)

        requested_bounding_box = ['Requested bounding box', coordinate_string]

        # requested bounding box comes last
        polygons.insert(len(polygons), requested_bounding_box)

        length = len(polygons)

        for i in range(length):

            if i == length - 1:
                # requested bounding box
                polygon_description = polygons[i][0]
            else:
                # NSIDC polygons: convert JSON date into datetime
                polygon_description = str(datetime.datetime.strptime(polygons[i][0], '%Y-%m-%dT%H:%M:%S.%fZ'))

            xml_string += '\t\t<Placemark id="' + str(i) + '">\n'

            # polygon corresponding to requested bounding box is colored in red
            if i == length - 1:
                xml_string += '\t\t\t<styleUrl>#transBluePoly</styleUrl>\n'
            # list of polygons that fully overlap requested bounding box  are colored in yellow
            elif i in date_item[2]:
                xml_string += '\t\t\t<styleUrl>#transOrangePoly</styleUrl>\n'

            xml_string += '\t\t\t<name>' + str(i) + '</name>\n'
            xml_string += '\t\t\t<description>' + polygon_description + '</description>\n'
            xml_string += '\t\t\t<Polygon>\n'
            xml_string += '\t\t\t\t<outerBoundaryIs>\n'
            xml_string += '\t\t\t\t\t<LinearRing>\n'
            xml_string += '\t\t\t\t\t\t<coordinates>\n'

            # xml_string += '\t\t\t\t\t\t\t5.7935686, 37.8691406, 100\n'
            # xml_string += '\t\t\t\t\t\t\t5.7935686, 35.9454346, 100\n'
            # xml_string += '\t\t\t\t\t\t\t9.0508299, 35.9454346, 100\n'
            # xml_string += '\t\t\t\t\t\t\t9.0508299, 37.8691406, 100\n'
            # xml_string += '\t\t\t\t\t\t\t5.7935686, 37.8691406, 100\n'

            coordinates = polygons[i][1].split()

            # lat        lon       lat        lon       lat        lon        lat        lon        lat        lon
            # 0          1         2          3         4          5          6          7          8          9
            # 37.8691406 7.8475103 35.8586655 7.8475103 35.8586655 11.1981325 37.8691406 11.1981325 37.8691406 7.8475103

            #                                lon                     lat
            xml_string += '\t\t\t\t\t\t\t' + coordinates[1] + ', ' + coordinates[0] + ', 100\n'
            xml_string += '\t\t\t\t\t\t\t' + coordinates[3] + ', ' + coordinates[2] + ', 100\n'
            xml_string += '\t\t\t\t\t\t\t' + coordinates[5] + ', ' + coordinates[4] + ', 100\n'
            xml_string += '\t\t\t\t\t\t\t' + coordinates[7] + ', ' + coordinates[6] + ', 100\n'
            xml_string += '\t\t\t\t\t\t\t' + coordinates[9] + ', ' + coordinates[8] + ', 100\n'

            xml_string += '\t\t\t\t\t\t</coordinates>\n'
            xml_string += '\t\t\t\t\t</LinearRing>\n'
            xml_string += '\t\t\t\t</outerBoundaryIs>\n'
            xml_string += '\t\t\t</Polygon>\n'
            xml_string += '\t\t</Placemark>\n'

        xml_string += '\t</Document>\n'
        xml_string += '</kml>\n'

        # save KML file
        filepath = kml_file_directory + '/' + filename
        with open(filepath, 'w') as f:
            f.write(xml_string)

            # # bounding box coverage info
            # if len(date_item[2]) > 0:
            #     days_with_valid_images += 1
            #
            # total_days_with_images += 1
            #
            # # get link if coverage = True
            # if coverage_info:
            #     for polygon in polygons:
            #         try:
            #             link_info = polygon[2]
            #             links.append(link_info['href'])
            #         except:
            #             # do nothing
            #             None

        # # finally, some metrics about image availability
        # start_date = datetime.datetime.strptime(time_start, '%Y-%m-%dT%H:%M:%SZ')
        # end_date = datetime.datetime.strptime(time_end, '%Y-%m-%dT%H:%M:%SZ')
        # duration = end_date - start_date
        # difference_in_years = relativedelta.relativedelta(end_date, start_date).years
        # percentage_valid = days_with_valid_images / duration.days
        #
        # # case not handled: hits > CMR_PAGE_SIZE (2000)
        # print(str(duration.days) + ' calendar days (' + str(difference_in_years) + ' years) - ' + str(
        #     total_days_with_images) + ' days with images - ' + str(
        #     days_with_valid_images) + ' days with images fully covering bounding box (' + f"{percentage_valid:.0%}"
        #     + ')')
        #
        # return links


########################################################################################################################

# following standard code NOT USED!
########################################################################################################################
# def cmr_filter_urls(search_results):
#     """Select only the desired data files from CMR response."""
#     if 'feed' not in search_results or 'entry' not in search_results['feed']:
#         return []
#
#     entries = [e['links']
#                for e in search_results['feed']['entry']
#                if 'links' in e]
#     # Flatten "entries" to a simple list of links
#     links = list(itertools.chain(*entries))
#
#     urls = []
#     unique_filenames = set()
#     for link in links:
#         if 'href' not in link:
#             # Exclude links with nothing to download
#             continue
#         if 'inherited' in link and link['inherited'] is True:
#             # Why are we excluding these links?
#             continue
#         if 'rel' in link and 'data#' not in link['rel']:
#             # Exclude links which are not classified by CMR as "data" or "metadata"
#             continue
#
#         if 'title' in link and 'opendap' in link['title'].lower():
#             # Exclude OPeNDAP links--they are responsible for many duplicates
#             # This is a hack; when the metadata is updated to properly identify
#             # non-datapool links, we should be able to do this in a non-hack way
#             continue
#
#         filename = link['href'].split('/')[-1]
#         if filename in unique_filenames:
#             # Exclude links with duplicate filenames (they would overwrite)
#             continue
#         unique_filenames.add(filename)
#
#         urls.append(link['href'])
#
#     return urls
########################################################################################################################

def cmr_search(short_name, version, time_start, time_end,
               bounding_box='', polygon='', filename_filter=''):
    """Perform a scrolling CMR query for files matching input criteria."""
    cmr_query_url = build_cmr_query_url(short_name=short_name, version=version,
                                        time_start=time_start, time_end=time_end,
                                        bounding_box=bounding_box,
                                        polygon=polygon, filename_filter=filename_filter)
    print('Querying for data:\n\t{0}\n'.format(cmr_query_url))

    cmr_scroll_id = None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    assembled_date_items = None

    try:
        urls = []
        while True:
            req = Request(cmr_query_url)
            if cmr_scroll_id:
                req.add_header('cmr-scroll-id', cmr_scroll_id)
            response = urlopen(req, context=ctx)
            if not cmr_scroll_id:
                # Python 2 and 3 have different case for the http headers
                headers = {k.lower(): v for k, v in dict(response.info()).items()}
                cmr_scroll_id = headers['cmr-scroll-id']
                hits = int(headers['cmr-hits'])
                if hits > 0:
                    print('Found {0} matches.'.format(hits))
                else:
                    print('Found no matches.')
            search_page = response.read()
            search_page = json.loads(search_page.decode('utf-8'))

            ############################################################################################################
            # url_scroll_results = cmr_filter_urls(search_page)

            # case not handled: hits > CMR_PAGE_SIZE (2000)
            # url_scroll_results = generate_kml_file(search_page)

            polygon_infos = filter_polygons(search_page)
            if polygon_infos:

                # split polygon list by date
                date_items = split_polygon_infos_by_date(polygon_infos)

                # add bounding box coverage info
                kml_file_generation = True
                chunk_of_date_items = get_bounding_box_coverage_info(bounding_box, date_items, kml_file_generation)

            else:
                chunk_of_date_items = None

            ############################################################################################################

            # if not url_scroll_results:
            if chunk_of_date_items is None:
                break
            if hits > CMR_PAGE_SIZE:
                print('..', end='')
                sys.stdout.flush()

            # urls += url_scroll_results

            if assembled_date_items is not None:
                print(
                    "assembling DataFrame chunks: " + str(assembled_date_items.shape[0]) + " date entries with " + str(
                        chunk_of_date_items.shape[0]) + " other date entries")
                # axis=0: concatenate along rows
                # ignore_index=True: a continuous index value is maintained across the rows in the concatenated data frame
                assembled_date_items = pd.concat([assembled_date_items, chunk_of_date_items], axis=0, ignore_index=True)
            else:
                assembled_date_items = chunk_of_date_items

        if hits > CMR_PAGE_SIZE:
            print()

        # return urls
        return assembled_date_items

    except KeyboardInterrupt:
        quit()


def main():

    global short_name, version, time_start, time_end, bounding_box, \
        polygon, filename_filter, url_list

    # if bounding box was not specified, determine it based on SHP file
    if bounding_box == '':
        # bounding box input directory is expected to have been created manually and to contain an SHP file (network)
        bounding_box_input_directory = 'A_BOUNDING_BOX_INPUT'
        bounding_box = get_bounding_box_from_shp(bounding_box_input_directory)

    # check for existence of directory for filter results
    filter_result_directory = 'B_FILTER_RESULT'
    if not os.path.exists(filter_result_directory):
        os.makedirs(filter_result_directory)

    cmr_search_and_filter_time = start_time_measure(">>> starting CMR search and filter...")
    date_items_found = cmr_search(short_name, version, time_start, time_end,
                                  bounding_box=bounding_box,
                                  polygon=polygon, filename_filter=filename_filter)
    end_time_measure(cmr_search_and_filter_time, '>>> CMR search and filter time: ')

    if date_items_found is not None:
        filename = 'selection_from_' + time_start.split('T')[0] + '_to_' + time_end.split('T')[0] + '.xlsx'

        ready_for_download_directory = 'B_FILTER_RESULT/B2_READY_FOR_DOWNLOAD'
        if not os.path.exists(ready_for_download_directory):
            os.makedirs(ready_for_download_directory)

        downloaded_directory = 'B_FILTER_RESULT/B3_DOWNLOADED'
        if not os.path.exists(downloaded_directory):
            os.makedirs(downloaded_directory)

        rasterized_directory = 'B_FILTER_RESULT/B4_RASTERIZED'
        if not os.path.exists(rasterized_directory):
            os.makedirs(rasterized_directory)

        filepath = ready_for_download_directory + '/' + filename

        date_items_found.to_excel(filepath, index=False)  # requires openpyxl


if __name__ == '__main__':

    short_name = 'SPL2SMAP_S'
    version = '003'
    time_start = '2020-04-07T00:00:00Z'  # 2020
    time_end = '2020-04-08T00:00:00Z'
    bounding_box = '9.075181780910482,35.789381002622484,9.648289096658775,36.539747306557665'  # original
    # bounding_box = '8.15,34.25,11.35,37.35'
    polygon = ''
    filename_filter = ''
    url_list = []

    CMR_URL = 'https://cmr.earthdata.nasa.gov'
    URS_URL = 'https://urs.earthdata.nasa.gov'
    CMR_PAGE_SIZE = 2000
    CMR_FILE_URL = ('{0}/search/granules.json?provider=NSIDC_ECS'
                    '&sort_key[]=start_date&sort_key[]=producer_granule_id'
                    '&scroll=true&page_size={1}'.format(CMR_URL, CMR_PAGE_SIZE))

    main()
