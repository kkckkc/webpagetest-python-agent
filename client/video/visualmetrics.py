import logging
import os
import subprocess
import sys

import client.provider
from client.capability import VideoCapability

logger = logging.getLogger(__name__)


class VisualMetrics(client.provider.Provider):
    def on_tear_down_run(self, event):
        video_capability = VideoCapability(self.session)

        i = 1
        video_files = video_capability.get_video_files()
        for f in video_files:
            logger.info("Running visualmetrics.py script for video output %d of %d" % (i, len(video_files)))

            try:
                subprocess.check_output([
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
                ], stderr=subprocess.STDOUT, env=os.environ.copy())
            except subprocess.CalledProcessError as e:
                print(e.output)
                raise
            i += 1
