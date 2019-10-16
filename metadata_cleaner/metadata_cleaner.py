#!/usr/bin/env python3
"""Cleans up metadata from sensors
"""
import argparse
import os
import json
import logging

from pyclowder.utils import setup_logging as do_setup_logging
from terrautils.extractors import load_json_file as do_load_json_file
from terrautils.metadata import clean_metadata as do_clean_metadata
import terrautils.lemnatec

terrautils.lemnatec.SENSOR_METADATA_CACHE = os.path.dirname(os.path.realpath(__file__))

SELF_DESCRIPTION = "Maricopa agricultural gantry metadata cleaner"

# List of sensors that cannot be cleaned
SKIP_SENSORS = ['Full Field']

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
    found['sensor'] = args.sensor
    found['filename'] = args.filename
    found['working_space'] = args.working_space
    if args.userid:
        found['userid'] = args.userid

    # Note: Return an empty dict if we're missing mandatory parameters
    return found

def clean_metadata(sensor: str, filename: str, working_space: str, userid: str = None) -> dict:
    """Cleans the metadata from the file passed in and adds context.
    Arguments:
        sensor: the name of the sensor the metadata is assciated with
        filename: the path to the metadata file to clean
        working_space: the path to our working space
        userid: optional user identification string to add to metadata
    Return:
        Returns the file location of the converted metadata
    """
    result = {}

    if sensor in SKIP_SENSORS:
        logging.info("Sensor '%s' does not have metadata that can be cleaned. Returning success")
        result['code'] = 0
        result['message'] = "Sensor '" + sensor + "' does not have metadata that can be cleaned"
        return result

#        # For these datasets, we must get TERRA md from raw_data source
#        lv1_types = {"RGB GeoTIFFs": "stereoTop",
#                     "Thermal IR GeoTIFFs": "flirIrCamera"}
#        if sensor_type in lv1_types:
#            raw_equiv = resource['name'].replace(sensor_type, lv1_types[sensor_type])
#            source_dir = os.path.dirname(self.sensors.get_sensor_path_by_dataset(raw_equiv))
#        else:
#            # Search for metadata.json source file
#            source_dir = os.path.dirname(self.sensors.get_sensor_path_by_dataset(resource['name']))
#        source_dir = self.remapMountPath(connector, source_dir)

#        if self.delete:
#            # Delete all existing metadata from this dataset
#            self.log_info(resource, "Deleting existing metadata")
#            delete_dataset_metadata(host, self.clowder_user, self.clowder_pass, resource['id'])

#        # TODO: split between the PLY files (in Level_1) and metadata.json files - unique to this sensor
#        if sensor_type == "scanner3DTop":
#            source_dir = source_dir.replace("Level_1", "raw_data").replace("laser3d_las", "scanner3DTop")

    # Load our base metadata
    loaded_json = do_load_json_file(filename)
    if not loaded_json:
        logging.error("Unable to load JSON from file '%s'", filename)
        logging.error("    JSON may be missing or invalid. Returning an error")
        result['error'] = {'message': "Unable to load JSON from specified file: '" + filename + "'"}
        result['code'] = -1
        return result

    # Check if we are cleaning already cleaned metadata
    if '@context' in loaded_json and 'content' in loaded_json:
        md_json = loaded_json['content']
    else:
        md_json = loaded_json

    # Clean the metadata and format it into JSONLD
    md_json = do_clean_metadata(md_json, sensor)
    format_md = {
        '@context': ['https://clowder.ncsa.illinois.edu/contexts/metadata.jsonld',
                     {'@vocab': 'https://terraref.ncsa.illinois.edu/metadata/uamac#'}],
        'content': md_json,
        'agent': {
            '@type': 'cat:user'
        }
    }

    if userid:
        format_md['agent']['user_id'] = userid
    
    # Create the output file and write the metadata to it
    filename_parts = os.path.splitext(os.path.basename(filename))
    new_filename = filename_parts[0] + '_cleaned' + filename_parts[1]
    new_path = os.path.join(working_space, new_filename)
    logging.info("Saving cleaned metadata to file '%s'", new_path)
    logging.debug("Cleaned metadata '%s'", str(format_md))

    with open(new_path, 'w') as out_file:
        logging.warning("HACK: format_md: %s", format_md)
        json.dump(format_md, out_file, indent=2, skipkeys=True)

    result['file'] = [{
        'path': new_path,
        'key': sensor
        }]
    result['code'] = 0

    return result

def do_work(parser) -> None:
    """Function to prepare and execute work unit
    """
    parser.add_argument('--logging', '-l', nargs='?', default=os.getenv("LOGGING"),
                        help='file or url or logging configuration (default=None)')

    parser.add_argument('--debug', '-d', action='store_const',
                        default=logging.WARN, const=logging.DEBUG,
                        help='enable debug logging (default=WARN)')

    parser.add_argument('--info', '-i', action='store_const',
                        default=logging.WARN, const=logging.INFO,
                        help='enable info logging (default=WARN)')

    parser.add_argument('sensor', type=str, help='the name of the sensor')

    parser.add_argument('filename', type=str, help='full file path to the metadata')

    parser.add_argument('working_space', type=str, help='the folder to use use as a workspace and for storing results')

    parser.add_argument('userid', type=str, nargs='?',
                        help='an optional user identification string to be added to the metadata')

    args = parser.parse_args()

    # start logging system
    do_setup_logging(args.logging)
    logging.getLogger().setLevel(args.debug if args.debug == logging.DEBUG else args.info)

    params_dict = args_to_params(args)
    logging.debug("Calling clean_metadata() with the following parameters: %s", str(params_dict))
    result = clean_metadata(**params_dict)

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
