#!/usr/bin/env python3
"""Pulls BETYdb data
"""

import argparse
import os
import json
import logging
import sys

from pyclowder.utils import setup_logging as do_setup_logging
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

    parser.add_argument('--logging', '-l', nargs='?', default=os.getenv("LOGGING"),
                        help='file or url or logging configuration (default=None)')

    parser.add_argument('--debug', '-d', action='store_const',
                        default=logging.WARN, const=logging.DEBUG,
                        help='enable debug logging (default=WARN)')

    parser.add_argument('--info', '-i', action='store_const',
                        default=logging.WARN, const=logging.INFO,
                        help='enable info logging (default=WARN)')

    parser.add_argument('--options', '-o', default=None,
                        help='optional comma separated list of name/value pairs to pass (eg: "name=value,name2=value2")')

    parser.add_argument('datatype', type=str, help='type of data to retrieve: cultivars, experiments, sites, traits')
    parser.add_argument('date', type=str, nargs='?',help='date needed by the "sites" datatype parameter in YYYY-MM-DD format')

    args = parser.parse_args()

    # start logging system
    do_setup_logging(args.logging)
    logging.getLogger().setLevel(args.debug if args.debug == logging.DEBUG else args.info)

    if args.datatype == 'sites' and not args.date:
        result['error'] = "A date must be specified with the datatype parameter of \"sites\""
        result['code'] = -1
        logging.error(result['error'])
        logging.error("    Stopping processing")
        return result['code']

    os.environ['BETYDB_URL'] = BETYDB_URL
    os.environ['BETYDB_KEY'] = BETYDB_KEY
    logging.debug("Calling BETYdb at location: %s", BETYDB_URL)

    opts = {}
    if args.options:
        options = args.options.split(',')
        for one_option in options:
            if '=' in one_option:
                opt_name, opt_value = one_option.split('=')
                if opt_name:
                    opts[opt_name] = opt_value
            else:
                opts[one_option] = ''
    if opts:
        logging.debug("Calling BETYdb with options: %s", str(opts))

    type_map = {
        'cultivars': lambda: do_get_cultivars(limit='none', **opts),
        'experiments': lambda: do_get_experiments(associations_mode='full_info', limit='none', **opts),
        'sites': lambda: do_get_sites(args.date, **opts),
        'traits': lambda: do_get_traits(limit='none', **opts),
        }

    if args.datatype in type_map:
        data = type_map[args.datatype]()
        print(json.dumps(data, indent=2))
    else:
        result['error'] = "Invalid datatype parameter specifed: '%s'. Stopping processing" % str(args.datatype)
        result['code'] = -2

    if 'error' in result:
        logging.error(result['error'])
        logging.error("    Stopping processing")
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
