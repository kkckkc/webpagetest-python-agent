class WebClientCapability:
    pass


class ScreenshotCapability:
    pass


class VideoCapability:
    def __init__(self, session):
        self.session = session

    def get_tmp_video_file(self, run, view):
        return self.session.result_dir.get_file("tmp_video.mp4", run, view, None)

    def get_tmp_video_files(self):
        return self.session.result_dir.get_files("tmp_video.mp4")

    def get_video_file(self, run, view, step):
        return self.session.result_dir.get_file("video.mp4", run, view, step)

    def get_video_files(self):
        return self.session.result_dir.get_files("video.mp4")

    def get_video_directory(self, f):
        return self.session.result_dir.get_associated_file("video", f)

    def get_trace_file(self, f):
        return self.session.result_dir.get_associated_file("trace.json", f)

    def get_histograms_file(self, f):
        return self.session.result_dir.get_associated_file("histograms.json.gz", f)


class TraceCapability:
    def __init__(self, session):
        self.session = session

    def open_trace_file(self, run, view, step):
        return self.session.result_dir.open_file("trace.json", run, view, step)

    def get_trace_files(self):
        return self.session.result_dir.get_files("trace.json")

    def get_user_timing_file(self, f):
        return self.session.result_dir.get_associated_file("user_timing.json.gz", f)

    def get_timeline_cpu_file(self, f):
        return self.session.result_dir.get_associated_file("timeline_cpu.json.gz", f)

    def get_feature_usage_file(self, f):
        return self.session.result_dir.get_associated_file("feature_usage.json.gz", f)
