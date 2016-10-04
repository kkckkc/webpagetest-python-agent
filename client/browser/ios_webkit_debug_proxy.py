import logging
import urllib2
from time import sleep

from client.provider import Provider
from client.process import launch
from argparse import ArgumentParser

logger = logging.getLogger(__name__)

NUMBER_OF_STARTS_ATTEMPTS = 5


class IOSWebkitDebugProxy(Provider):
    def __init__(self, event_bus, config):
        Provider.__init__(self, event_bus, config)
        self.video_process = None

    @classmethod
    def argparser(cls):
        p = ArgumentParser(description=cls.__name__, prog=cls.__name__, add_help=False, parents=[Provider.argparser()])
        p.add_argument('--proxy', dest='proxy', default="ios_webkit_debug_proxy", required=False)
        return p

    def on_setup_run(self, event):
        logger.info("Starting ios proxy")

        number_of_attempts = NUMBER_OF_STARTS_ATTEMPTS
        while number_of_attempts > 0:
            number_of_attempts -= 1
            try:
                self.video_process, stdout_reader, stderr_reader = launch([self.config['proxy']])
                sleep(1 + abs(number_of_attempts - (NUMBER_OF_STARTS_ATTEMPTS - 1)))
                urllib2.urlopen("http://localhost:9222/json")
                break
            except urllib2.URLError:
                self.video_process.terminate()
                logger.warn("Unable to start ios_webkit_debug_proxy, retrying with longer timeout")
                pass

    def on_tear_down_run(self, event):
        logger.info("Ending ios proxy")
        if self.video_process:
            try:
                self.video_process.terminate()
            except:
                pass
        else:
            logger.debug("No active ios proxy to end")

    def on_abort(self, event):
        logger.info("Aborting ios proxy")
        self.on_tear_down_run(event)
