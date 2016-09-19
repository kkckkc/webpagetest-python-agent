#!/usr/bin/python

from client.job import Launcher
from client.log import init_log

import argparse

#
# wpt_job.py [-h] [-v] [-c CONFIG] dir job
#

parser = argparse.ArgumentParser(description='WPT Job', prog='wpt_job.py')
parser.add_argument('-v', '--verbose', action='count',
                    help="Increase verbosity (specify multiple times for more). -vvvv for full debug output.")
parser.add_argument('-c', '--config', type=str, help="config file to use")
parser.add_argument('dir', help="result directory")
parser.add_argument('job', help="job_file")
options = parser.parse_args()

init_log(options.verbose, "client.job")

l = Launcher(options.config, options.job, options.dir)
l.launch()

