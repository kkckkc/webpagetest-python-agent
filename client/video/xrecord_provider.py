import logging
from time import sleep

from client.provider import Provider, VideoRecordingProvider
from client.capability import VideoCapability
from client.process import launch
from argparse import ArgumentParser

logger = logging.getLogger(__name__)

XRECORD_WAIT_BEFORE_START = 1


class XRecordVideoCapture(VideoRecordingProvider):
    def __init__(self, event_bus, config):
        Provider.__init__(self, event_bus, config, lock_on="run")
        self.video_process = None

    @classmethod
    def argparser(cls):
        p = ArgumentParser(description=cls.__name__, prog=cls.__name__, add_help=False, parents=[Provider.argparser()])
        p.add_argument('--xrecord', dest='xrecord', default="xrecord", required=False)
        p.add_argument('--name', dest='device_name', required=True)
        return p

    # Needs to start at initialize phase, as it needs to run prior to ios_webkit_debug_proxy
    def on_start_run(self, event):
        super(XRecordVideoCapture, self).on_start_run(event)
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

    def on_stop_run(self, event):
        logger.info("Ending screen recording")
        if self.video_process:
            self.video_process.terminate()
            sleep(2)
        else:
            logger.debug("No active screen recording to end")
        super(XRecordVideoCapture, self).on_stop_run(event)

    def on_abort(self, event):
        logger.info("Aborting screen recording")
        self.on_stop_run(event)
