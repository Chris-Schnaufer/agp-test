#!/usr/bin/env python3
"""Converts .bin files to geotiff
"""

import argparse
import os
import json
import logging

from pyclowder.utils import setup_logging as do_setup_logging
from terrautils.extractors import load_json_file as do_load_json_file
from terrautils.formats import create_geotiff as do_create_geotiff
from terrautils.metadata import get_terraref_metadata as do_get_terraref_metadata, \
    get_season_and_experiment as do_get_season_and_experiment
from terrautils.spatial import geojson_to_tuples as do_geojson_to_tuples
from terrautils.sensors import Sensors
import terraref.stereo_rgb
import terrautils.lemnatec

terrautils.lemnatec.SENSOR_METADATA_CACHE = os.path.dirname(os.path.realpath(__file__))

SELF_DESCRIPTION = "Maricopa agricultural gantry bin to geotiff converter"

EXTRACTOR_NAME = 'stereoTop'
EXTRCTOR_VERSION = "1.0"

def get_metadata_timestamp(metadata: dict) -> str:
    """Looks up the timestamp in the metadata
    Arguments:
        metadata: the metadata to find the timestamp in
    """
    if 'content' in metadata:
        check_md = metadata['content']
    else:
        check_md = metadata

    timestamp = None
    if not 'timestamp' in check_md:
        if 'gantry_variable_metadata' in check_md:
            if 'datetime' in check_md['gantry_variable_metadata']:
                timestamp = check_md['gantry_variable_metadata']['datetime']
    else:
        timestamp = check_md['timestamp']

    return timestamp

def save_result(working_space: str, result: dict) -> None:
    """Saves the result dictionary as JSON to a well known location in the
       working space folder. Relative to the working space folder, the JSON
       is stored in 'output/results.json'. Folders are created as needed.
    Arguments:
        working_space: path to our working space
        result: dictionary containing the results of a run
    """
    result_path = os.path.join(working_space, 'output')
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    result_path = os.path.join(result_path, 'result.json')
    logging.info("Storing result at location: '%s'", result_path)
    logging.debug("Result: %s", str(result))

    with open(result_path, 'w') as out_file:
        json.dump(result, out_file, indent=2)


def args_to_params(args: list) -> dict:
    """Looks through the arguments and returns a dict with the found values.
    Arguments:
        args: command line arguments as provided by argparse
    """
    found = {}

    # Setup the dictionary identifying the parameters
    found['filename'] = args.bin_file
    found['metadata'] = args.metadata_file
    found['working_space'] = args.working_space

    # Note: Return an empty dict if we're missing mandatory parameters
    return found

def bin2tif(filename: str, metadata: str, working_space: str) -> dict:
    """Converts the bin file to a geotiff file
    ArgumentsL
        filename: the path to the .bin file
        metadata: the path to the cleaned metadata file
        working_space: the path to our working space
    """
    result = {}

    loaded_json = do_load_json_file(metadata)
    if not loaded_json:
        msg = "Unable to load JSON from file '%s'" % metadata
        logging.error(msg)
        logging.error("    JSON may be missing or invalid. Returning an error")
        result['error'] = {'message': msg}
        result['code'] = -1
        return result

    if 'content' in loaded_json:
        parse_json = loaded_json['content']
    else:
        parse_json = loaded_json
    terra_md_full = do_get_terraref_metadata(parse_json, EXTRACTOR_NAME)
    if not terra_md_full:
        msg = "Unable to find %s metadata in JSON file '%s'" % (EXTRACTOR_NAME, metadata)
        logging.error(msg)
        logging.error("    JSON may be missing or invalid. Returning an error")
        result['error'] = {'message': msg}
        result['code'] = -2
        return result

    timestamp = get_metadata_timestamp(terra_md_full)
    if not timestamp:
        msg = "Unable to find timestamp in JSON file '%s'" % filename
        logging.error(msg)
        logging.error("    JSON may be missing or invalid. Returning an error")
        result['error'] = {'message': msg}
        result['code'] = -3
        return result

        # Fetch experiment name from terra metadata
    _, _, updated_experiment = do_get_season_and_experiment(timestamp, 'stereoTop', terra_md_full)
#        if None in [season_name, experiment_name]:
#            raise ValueError("season and experiment could not be determined")
#
#        # Determine output directory
#        self.log_info(resource, "Hierarchy: %s / %s / %s / %s / %s / %s / %s" % (season_name, experiment_name, self.sensors.get_display_name(),
#                                                                                 timestamp[:4], timestamp[5:7], timestamp[8:10], timestamp))
#        target_dsid = build_dataset_hierarchy_crawl(host, secret_key, self.clowder_user, self.clowder_pass, self.clowderspace,
#                                              season_name, experiment_name, self.sensors.get_display_name(),
#                                              timestamp[:4], timestamp[5:7], timestamp[8:10],
#                                              leaf_ds_name=self.sensors.get_display_name() + ' - ' + timestamp)

    sensor = Sensors(base='', station='ua-mac', sensor='rgb_geotiff')
    leaf_name = sensor.get_display_name()

    bin_type = 'left' if filename.endswith('_left.bin') else 'right' if filename.endswith('_right.bin') else None
    if not bin_type:
        msg = "Bin file must be a left or right file: '%s'" % filename
        logging.error(msg)
        logging.error("    Returning an error")
        result['error'] = {'message': msg}
        result['code'] = -4
        return result

    terra_md_trim = do_get_terraref_metadata(parse_json)
    if updated_experiment is not None:
        terra_md_trim['experiment_metadata'] = updated_experiment
    terra_md_trim['raw_data_source'] = filename

    tiff_filename = os.path.splitext(os.path.basename(filename))[0] + '.tif'
    tiff_path = os.path.join(working_space, tiff_filename)

    try:
        bin_shape = terraref.stereo_rgb.get_image_shape(terra_md_full, bin_type)
        gps_bounds_bin = do_geojson_to_tuples(terra_md_full['spatial_metadata'][bin_type]['bounding_box'])
    except KeyError:
        msg = "Spatial metadata is not properly identified. Unable to continue"
        logging.error(msg)
        logging.error("    Returning an error")
        result['error'] = {'message': msg}
        result['code'] = -5
        return result

    # Extractor info
    extractor_info = {
        'name': EXTRACTOR_NAME,
        'version': EXTRCTOR_VERSION,
        'author': "extractor@extractor.com",
        'description': "Maricopa agricultural gantry bin to geotiff converter",
        'repository': [{"repType": "git", "repUrl": "https://github.com/terraref/extractors-stereo-rgb.git"}]
    }

    # Perform actual processing
    new_image = terraref.stereo_rgb.process_raw(bin_shape, filename, None)
    do_create_geotiff(new_image, gps_bounds_bin, tiff_path, None, True,
                      extractor_info, terra_md_full, compress=True)

#        level1_md = build_metadata(host, self.extractor_info, target_dsid, terra_md_trim, 'dataset')
    context = ['https://clowder.ncsa.illinois.edu/contexts/metadata.jsonld']
    terra_md_trim['extractor_version'] = EXTRCTOR_VERSION
    new_md = {
        '@context': context,
        'content': terra_md_trim,
        'filename': tiff_filename,
        'agent': {
            '@type': 'cat:extractor',
            'version': EXTRCTOR_VERSION,
            'name': EXTRACTOR_NAME
        }
    }

    # Setup the result
    result['container'] = [{
        'name': leaf_name,
        'exists': False,
        'metadata' : {
            'replace': True,
            'data': new_md
        },
        'file': [{
            'path': tiff_path,
            'key': sensor.sensor
        }]
    }]
    result['code'] = 0
    return result

def do_work(parser) -> None:
    """Function to prepare and execute work unit
    Arguments:
        parser: an instance of argparse.ArgumentParser
    """
    parser.add_argument('--logging', '-l', nargs='?', default=os.getenv("LOGGING"),
                        help='file or url or logging configuration (default=None)')

    parser.add_argument('--debug', '-d', action='store_const',
                        default=logging.WARN, const=logging.DEBUG,
                        help='enable debug logging (default=WARN)')

    parser.add_argument('--info', '-i', action='store_const',
                        default=logging.WARN, const=logging.INFO,
                        help='enable info logging (default=WARN)')

    parser.add_argument('bin_file', type=str, help='full path to the bin file to convert')

    parser.add_argument('metadata_file', type=str, help='full path to the cleaned metadata')

    parser.add_argument('working_space', type=str, help='the folder to use use as a workspace and for storing results')

    args = parser.parse_args()

    # start logging system
    do_setup_logging(args.logging)
    logging.getLogger().setLevel(args.debug if args.debug == logging.DEBUG else args.info)

    params_dict = args_to_params(args)
    logging.debug("Calling bin2tif() with the following parameters: %s", str(params_dict))
    result = bin2tif(**params_dict)

    # Save the result to a well known location
    logging.debug("Saving the result to the working space: '%s'", params_dict['working_space'])
    save_result(params_dict['working_space'], result)


if __name__ == "__main__":
    try:
        PARSER = argparse.ArgumentParser(description=SELF_DESCRIPTION,
                                         epilog="The cleaned metadata is written to the working space, and " +
                                         "the results are written off the working space in 'output/result.json'")
        do_work(PARSER)
    except Exception as ex:
        logging.error("Top level exception handler caught an exception: %s", str(ex))
        raise
