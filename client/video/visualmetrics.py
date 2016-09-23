import logging
import os
import sys

import client.provider
from client.capability import VideoCapability
from client.process import run

logger = logging.getLogger(__name__)


class VisualMetrics(client.provider.Provider):
    def on_tear_down_run(self, event):
        video_capability = VideoCapability(self.session)

        i = 1
        video_files = video_capability.get_video_files()
        for f in video_files:
            logger.info("Running visualmetrics.py script for video output %d of %d" % (i, len(video_files)))

            run([
                sys.executable,
                "lib/video/visualmetrics.py",
                "-i", os.path.join(self.session.result_dir.folder, f.file),
                "-m", os.path.join(self.session.result_dir.folder, video_capability.get_trace_file(f)),
                "--histogram", os.path.join(self.session.result_dir.folder, video_capability.get_histograms_file(f)),
                "-d", os.path.join(self.session.result_dir.folder, video_capability.get_video_directory(f)),
                "--forceblank",
                "-o",
    #            "-j",
                "-p"
            ])
            i += 1
