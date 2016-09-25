import logging
from time import sleep

from client.provider import Provider
from client.capability import VideoCapability
from client.process import launch

logger = logging.getLogger(__name__)


class FfmpegVideoCapture(Provider):
    def __init__(self, event_bus, config):
        Provider.__init__(self, event_bus, config)
        self.pixel_density = config['pixelDensity'] if "pixelDensity" in config else None
        self.video_process = None

    def on_setup_step(self, event):
        video_capability = VideoCapability(self.session)

        pixel_density = self.pixel_density if self.pixel_density else self.view.pixel_density
        logger.debug("Pixel density = %d" % pixel_density)

        crop = (self.view.window_size.width * pixel_density,
                self.view.window_size.height * pixel_density,
                self.view.window_position.x * pixel_density,
                self.view.window_position.y * pixel_density)

        logger.info("Starting screen recording viewport=%dx%d, position=%d:%d" % crop)

        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "avfoundation",
            "-capture_cursor", "0",
            "-i", "1:none",
            "-vcodec", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            "-filter:v", "crop=%d:%d:%d:%d" % crop,
            "-r", "25",
            video_capability.get_video_file(self.run, self.view, self.step)]

        self.video_process, stdout_reader, stderr_reader = launch(ffmpeg_cmd)

        # Wait for confirmation that recording has started
        interval = 0.01
        timeout = 2
        counter = timeout / interval
        while counter > 0 and not stdout_reader.contains('Press [q] to stop, [?] for help'):
            sleep(interval)
            counter -= 1

    def on_end_step(self, event):
        logger.info("Ending screen recording")
        if self.video_process:
            self.video_process.terminate()
        else:
            logger.debug("No active screen recording to end")

    def on_abort(self, event):
        logger.info("Aborting screen recording")
        self.on_end_step(event)
