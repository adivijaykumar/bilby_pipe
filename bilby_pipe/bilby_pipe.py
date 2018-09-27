#!/usr/bin/env python
"""
"""
import os
import json
import urllib3
import argparse
from .gw_data_find import gw_data_find
from .utils import logger


def get_output_directory(gracedb, label):
    outdir = 'PE_{}_{}'.format(gracedb, label)
    if os.path.isdir(outdir) is False:
        os.mkdir(outdir)
    return outdir


def set_up_argument_parsing():
    parser = argparse.ArgumentParser(
        usage='Query GraceDB and write results to json')
    parser.add_argument('--gracedb', type=str, required=True,
                        help='The gracedb event UID')
    parser.add_argument('--detectors', nargs='+', default=['H1', 'L1'],
                        help='The detector names, {H1, L1}')
    parser.add_argument('--calibration', type=int, default=2,
                        help='Which calibration to use')
    parser.add_argument('--duration', type=int, default=4,
                        help='The duration of data about the event to use')
    parser.add_argument('--label', type=str, required=True,
                        help='A unique label for the query')
    return parser.parse_args()


def gracedb_to_json(gracedb, outdir=None):
    """ Script to download a GraceDB candidate

    Parameters
    ----------
    gracedb: str
        The UID of the GraceDB candidate
    outdir: str, optional
        If given, a string identfying the location in which to store the json
    """
    logger.info(
        'Starting routine to download GraceDb candidate {}'.format(gracedb))
    from ligo.gracedb.rest import GraceDb

    logger.info('Initialise client and attempt to download')
    client = GraceDb()
    try:
        candidate = client.event(gracedb)
        logger.info('Successfully downloaded candidate')
    except urllib3.HTTPError:
        raise ValueError("No candidate found")


    json_output = candidate.json()

    if outdir is not None:
        outfilepath = os.path.join(outdir, '{}.json'.format(gracedb))
        logger.info('Writing candidate to {}'.format(outfilepath))
        with open(outfilepath, 'w') as outfile:
                json.dump(json_output, outfile, indent=2)

    return json_output


def main():
    args = set_up_argument_parsing()
    outdir = get_output_directory(args.gracedb, args.label)
    candidate = gracedb_to_json(args.gracedb, outdir)
    event_time = candidate['gpstime']
    gps_start_time = event_time - args.duration
    gps_end_time = event_time + args.duration
    for det in args.detectors:
        gw_data_find(det, gps_start_time, args.duration, args.calibration,
                     outdir=outdir)
