#!/usr/bin/python

from client.agent import Agent
from client.log import init_log

import argparse

#
# wpt_agent.py [-h] [-v] [--cmd CMD] url location
#

parser = argparse.ArgumentParser(description='WPT Agent', prog='wpt_agent.py')
parser.add_argument('-v', '--verbose', action='count',
                    help="Increase verbosity (specify multiple times for more). -vvvv for full debug output.")
parser.add_argument('url', help="base url")
parser.add_argument('location', help="location name")
parser.add_argument('--cmd')
options = parser.parse_args()

init_log(options.verbose, "client.agent")


def job(result_dir):
    print(result_dir)

# TODO: Pass in cmd

agent = Agent(options.url, options.location, job)
agent.start()
