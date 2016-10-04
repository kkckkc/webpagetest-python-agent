import argparse
import logging
from time import sleep

from client.provider import Provider
from client.capability import VideoCapability
from client.process import launch

logger = logging.getLogger(__name__)

XRECORD_WAIT_BEFORE_START = 1


class XRecordVideoCapture(Provider):
    def __init__(self, event_bus, config):
        Provider.__init__(self, event_bus, config)
        self.video_process = None

    @classmethod
    def argparser(cls):
        parser = argparse.ArgumentParser(description=cls.__name__, prog=cls.__name__, add_help=False)
        parser.add_argument('-v', '--verbose', dest='log_level', action='count',
                            help="Increase verbosity (specify multiple times for more). -vv for full debug output.")
        parser.add_argument('--xrecord', dest='xrecord', default="xrecord", required=False)
        parser.add_argument('--name', dest='device_name', required=True)
        return parser

    def on_setup_run(self, event):
        video_capability = VideoCapability(self.session)

        logger.info("Starting screen recording")

        cmd = [
            self.config['xrecord'],
            "--name", self.config['device_name'],
            "--quicktime",
            "--force",
            "--debug",
            "--out", video_capability.get_tmp_video_file(self.run, None)]

        self.video_process, stdout_reader, stderr_reader = launch(cmd)

        # Wait for confirmation that recording has started
        interval = 0.1
        timeout = 10
        counter = timeout / interval
        while counter > 0 and not stderr_reader.contains('Recording started.'):
            sleep(interval)
            counter -= 1
        if counter == 0:
            raise RuntimeError("Timed out starting xrecord")

        # Wait some additional time as recording doesn't start immediately
        sleep(XRECORD_WAIT_BEFORE_START)

    def on_tear_down_run(self, event):
        logger.info("Ending screen recording")
        if self.video_process:
            self.video_process.terminate()
            sleep(2)
        else:
            logger.debug("No active screen recording to end")

    def on_abort(self, event):
        logger.info("Aborting screen recording")
        self.on_tear_down_run(event)
