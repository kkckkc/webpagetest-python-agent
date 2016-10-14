import logging
import os
import re
import shutil
import sys

from client.provider import Provider, PostProcessingProvider
from client.capability import VideoCapability
from client import process

logger = logging.getLogger(__name__)


class VisualMetrics(PostProcessingProvider):
    def __init__(self, event_bus, config):
        Provider.__init__(self, event_bus, config)

    def on_stop_session(self, event):
        video_capability = VideoCapability(self.session)

        self.lock()
        try:
            if len(video_capability.get_tmp_video_files()) > 0:
                self.split_tmp_videos(video_capability)

            self.process_videos(video_capability)
        finally:
            self.unlock()
        super(VisualMetrics, self).on_stop_session(event)

    def process_videos(self, video_capability):
        i = 1
        video_files = video_capability.get_video_files()
        for f in video_files:
            logger.info("Running visualmetrics.py script for video output %d of %d" % (i, len(video_files)))

            process.run([
                sys.executable,
                "lib/video/visualmetrics.py",
                "-i", os.path.join(self.session.result_dir.folder, f.file),
                "-m", os.path.join(self.session.result_dir.folder, video_capability.get_trace_file(f)),
                "--histogram", os.path.join(self.session.result_dir.folder, video_capability.get_histograms_file(f)),
                "-d", os.path.join(self.session.result_dir.folder, video_capability.get_video_directory(f)),
                "--forceblank",
                "-o",
                "-f",
                "-p"
            ])
            i += 1

    def split_tmp_videos(self, video_capability):
        def get_images(d): return [os.path.join(d, i) for i in os.listdir(d) if i.endswith(".png")]

        def get_folders(d): return [os.path.join(d, p) for p in os.listdir(d)
                                    if os.path.isdir(os.path.join(d, p)) and not p.startswith(".")]

        i = 1
        video_files = video_capability.get_tmp_video_files()
        for tmp_video_file in video_files:
            logger.info("Running visualmetrics.py to split tmp video %d of %d" % (i, len(video_files)))

            # Split video
            process.run([sys.executable,
                 "lib/video/visualmetrics.py",
                 "--multiple",
                 "-l",
                 "-q", "100",
                 "-i", os.path.join(self.session.result_dir.folder, tmp_video_file.file),
                 "-d", os.path.join(self.session.result_dir.folder, "video"),
                 "-o"], ignore_return_code=True)

            # Rebuild videos
            video_dir = os.path.join(self.session.result_dir.folder, "video")
            for f in get_folders(video_dir):
                images = get_images(f)
                if len(images) == 0:
                    break

                logger.info("Joining video %s" % (os.path.basename(f)))

                images.sort()
                images.reverse()

                fps, duration = 60, 100
                p = process.launch(['ffmpeg',
                           '-y',
                           '-f', 'image2pipe',
                           '-r', str(fps),
                           '-vcodec', 'png',
                           '-i', '-',
                           '-an',
                           '-vcodec', 'libx264',
                           '-preset', 'ultrafast',
                           '-tune', 'zerolatency',
                           '-pix_fmt', 'yuv420p',
                           os.path.join(f, "video.mp4")], pipe_stdin=True)[0]

                current_file = images.pop()
                ts = 0
                while len(images) > 0:
                    ts_of_current_file = int(re.sub(".*/ms_([0-9]+)\\.png", "\\1", current_file))
                    if ts > ts_of_current_file:
                        current_file = images.pop()
                    with open(current_file, "rb") as file:
                        p.stdin.write(file.read())
                    ts += (1000 / fps)
                p.stdin.close()
                p.wait()

                # Clean video directory
                logger.debug("Cleaning directory %s for png-images" % f)
                for png_file in get_images(f):
                    os.remove(png_file)

                # Move merged video file to correct file name
                if tmp_video_file.view is not None:
                    # One file per view
                    run = tmp_video_file.run.current - 1
                    view = 0 if tmp_video_file.view.is_first else 1
                    step = int(os.path.basename(f)) - 1

                    logger.debug("Video %s is run=%d, view=%d, step=%d" % (os.path.basename(f), run, view, step))
                    os.rename(os.path.join(f, "video.mp4"),
                              video_capability.get_video_file(tmp_video_file.run, tmp_video_file.view,
                                                              self.session.runs[run].views[view].steps[step]))
                elif tmp_video_file.run is not None:
                    # One file per run
                    run = tmp_video_file.run.current - 1
                    step = int(os.path.basename(f)) - 1
                    view = 0
                    if step > len(self.session.runs[run].views[0].steps):
                        view = 1
                        step -= len(self.session.runs[run].views[0].steps)

                    logger.debug("Video %s is run=%d, view=%d, step=%d" % (os.path.basename(f), run, view, step))
                    os.rename(os.path.join(f, "video.mp4"),
                              video_capability.get_video_file(tmp_video_file.run,
                                                              self.session.runs[run].views[view],
                                                              self.session.runs[run].views[view].steps[step]))
                else:
                    # One file per session
                    steps_per_view = len(self.session.runs[0].views[0].steps)
                    views_per_run = len(self.session.runs[0].views)

                    num = int(os.path.basename(f)) - 1

                    run = num / (steps_per_view * views_per_run)
                    view = (num - (run * views_per_run * steps_per_view)) / steps_per_view
                    step = num - (run * views_per_run * steps_per_view) - (view * steps_per_view)

                    logger.debug("Video %s is run=%d, view=%d, step=%d" % (os.path.basename(f), run, view, step))
                    os.rename(os.path.join(f, "video.mp4"),
                              video_capability.get_video_file(self.session.runs[run],
                                                              self.session.runs[run].views[view],
                                                              self.session.runs[run].views[view].steps[step]))

            i += 1

            shutil.rmtree(video_dir)

        os.remove(os.path.join(self.session.result_dir.folder, tmp_video_file.file))