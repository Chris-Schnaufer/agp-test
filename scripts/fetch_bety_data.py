#!/usr/bin/env python3
"""Pulls BETYdb data
"""

import argparse
import os
import json
import logging
import sys

from terrautils.betydb import get_cultivars as do_get_cultivars, \
                              get_experiments as do_get_experiments, \
                              get_sites as do_get_sites, \
                              get_traits as do_get_traits

SELF_DESCRIPTION = "Fetches data from the TERRA REF BETYdb instance"

BETYDB_URL = "https://terraref.ncsa.illinois.edu/bety/"
BETYDB_KEY = "9999999999999999999999999999999999999999"

def do_work(parser) -> dict:
    """Fetch the data from BETYdb
    Arguments:
        parser: an instance of argparse.ArgumentParser
    """
    result = {}

    parser.add_argument('datatype', type=str, help='type of data to retrieve: cultivars, experiments, sites, traits')
    parser.add_argument('date', type=str, nargs='?',help='date needed by the "sites" datatype parameter in YYYY-MM-DD format')

    args = parser.parse_args()

    if args.datatype == 'sites' and not args.date:
        result['error'] = "A date must be specified with the datatype parameter of \"sites\""
        result['code'] = -1
        logging.error(result['error'])
        return result['code']

    os.environ['BETYDB_URL'] = BETYDB_URL
    os.environ['BETYDB_KEY'] = BETYDB_KEY

    type_map = {
        'cultivars': lambda: do_get_cultivars(limit='none'),
        'experiments': lambda: do_get_experiments(associations_mode='full_info', limit='none'),
        'sites': lambda: do_get_sites(args.date),
        'traits': lambda: do_get_traits(limit='none'),
        }

    if args.datatype in type_map:
        data = type_map[args.datatype]()
        print(json.dumps(data, indent=2))
    else:
        result['error'] = "Invalid datatype parameter specifed: '%s'. Stopping processing" % str(args.datatype)
        result['code'] = -2

    if 'error' in result:
        logging.error(result['error'])
    if 'warning' in result:
        logging.warning(result['warning'])

    return result['code'] if 'code' in result else 0

if __name__ == "__main__":
    try:
        PARSER = argparse.ArgumentParser(description=SELF_DESCRIPTION)
        RETURN_CODE = do_work(PARSER)
    except Exception as ex:
        logging.error("Top level exception handler caught an exception: %s", str(ex))
        raise

    sys.exit(RETURN_CODE)
