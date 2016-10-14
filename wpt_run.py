#!/usr/bin/python

#
# wpt_run.py [-h] [-v] -r [-p driver options]
#

import argparse
import logging

import sys
from collections import OrderedDict

from client import model
from client.browser.ios_webkit_debug_proxy import IOSWebkitDebugProxy
from client.browser.webdriver.chrome_webdriver import ChromeWebDriver, ChromeTraceParser
from client.browser.webdriver.remote_debug_webdriver import RemoteDebugWebDriver, IOSRemoteDebugWebDriver
from client.browser.webdriver.webdriver import FirefoxWebDriver
from client.log import init_log
from client.provider import start_session, EventDispatcher
from client.video.ffmpeg_video_capture import FfmpegVideoCapture
from client.video.visualmetrics import VisualMetrics
from client.logging_provider import LoggingProvider
from client.video.xrecord_provider import XRecordVideoCapture

logger = logging.getLogger("wpt_run")

providers = [ChromeWebDriver, FirefoxWebDriver, ChromeTraceParser, FfmpegVideoCapture, VisualMetrics, LoggingProvider,
             RemoteDebugWebDriver, IOSRemoteDebugWebDriver, XRecordVideoCapture, IOSWebkitDebugProxy]

parser = argparse.ArgumentParser(description='WPT Run', prog='wpt_run.py', add_help=False)
parser.add_argument('-h', '--help', action='store_true')
parser.add_argument('-v', '--verbose', action='count',
                    help="Increase verbosity (specify multiple times for more). -vvvv for full debug output.")
parser.add_argument('-r', dest='runs', type=int, help="number of runs", required=True)
parser.add_argument('-d', dest='dir', type=str, help="working directory", required=True)
parser.add_argument('-u', dest='url', type=str, help="url")
parser.add_argument('--script', dest='script', type=str, help="script")
parser.add_argument('-p', nargs=2, metavar=('provider', 'args...'), type=str, dest='provider', help="provider")


def get_script(options):
    if options.url:
        return "navigate %s" % options.url
    elif options.script:
        with open(options.script, "r") as script_file:
            return script_file.read()
    else:
        return sys.stdin.read()


def group_argv_by_provider(args):
    current_key = "default"
    tmp_dict = OrderedDict()
    for i in range(len(args)):
        if args[i] == '-p':
            current_key = args[i + 1]
        elif current_key not in tmp_dict:
            tmp_dict[current_key] = []
        else:
            tmp_dict[current_key].append(args[i])
    return tmp_dict


class ProviderHelpFormatter(argparse.HelpFormatter):
    def __init__(self, prog):
        super(ProviderHelpFormatter, self).__init__(prog)
        self._current_indent = 5

    def add_usage(self, usage, actions, groups, prefix=None):
        pass

groups = group_argv_by_provider(sys.argv)
options = parser.parse_args(groups.pop('default'))

if options.help:
    parser.print_help()
    print("")

    for provider in providers:
        p = provider.argparser()
        p.formatter_class = ProviderHelpFormatter
        print(p.format_help())

else:
    init_log(options.verbose, "wpt_run")

    event_dispatcher = EventDispatcher()
    for k, v in groups.iteritems():
        logger.debug("Attempting to find provider %s" % k)

        try:
            matching_provider_class, = [p for p in providers if p.__name__ == k]
        except ValueError:
            raise Exception("Cannot find provider %s" % k)

        config = matching_provider_class.argparser().parse_args(v).__dict__

        logger.debug("Initializing provider %s with %r" % (k, config))
        provider = matching_provider_class(event_dispatcher, config)

    start_session(event_dispatcher, model.Session(run_count=options.runs,
                                                  result_dir=model.ResultDirectory(options.dir),
                                                  script=get_script(options)))
