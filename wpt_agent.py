#!/usr/bin/python
import logging

from client.process import run
from client.agent import Agent
from client.log import init_log

import argparse

#
# wpt_agent.py [-h] [-v] [--cmd CMD] url location
#

logger = logging.getLogger("wpt_agent")

parser = argparse.ArgumentParser(description='WPT Agent', prog='wpt_agent.py')
parser.add_argument('-v', '--verbose', action='count',
                    help="Increase verbosity (specify multiple times for more). -vvvv for full debug output.")
parser.add_argument('url', help="base url")
parser.add_argument('location', help="location name")
parser.add_argument('--cmd')
options = parser.parse_args()

init_log(options.verbose, "client.agent", "wpt_agent")


def job(test_id, result_dir):
    cmd = "%s %s %s/%s" % (options.cmd, result_dir, result_dir, "test.job")
    logger.info("Executing cmd '%s'" % cmd)
    run(cmd)

agent = Agent(options.url, options.location, job)
agent.start()
