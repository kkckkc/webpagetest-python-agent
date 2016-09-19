import argparse
import json
import logging
import os
import subprocess
import sys
from string import join
from time import sleep

from selenium import webdriver

from client.browser.webdriver.webdriver import WebDriver
from client.capability import TraceCapability
from client.provider import Provider

LOG_COMPLETION_WAIT = 0.5

# TODO: Check what these should be
DEFAULT_TRACE_CATEGORIES = [
    "-*", "devtools.timeline"
]

logger = logging.getLogger(__name__)


class ChromeWebDriver(WebDriver):
    def init(self, config):
        logger.info("Creating ChromeWebDriver")
        WebDriver.init(self, config)

    @classmethod
    def argparser(cls):
        parser = argparse.ArgumentParser(description=cls.__name__, prog=cls.__name__, add_help=False)
        parser.add_argument('-v', '--verbose', dest='log_level', action='count',
                            help="Increase verbosity (specify multiple times for more). -vv for full debug output.")
        parser.add_argument('--chrome-driver-path', dest='chromedriver_path', required=True)
        parser.add_argument('--emulate', dest='mobile_emulation', default=argparse.SUPPRESS)
        return parser

    def _init_driver(self):
        caps = webdriver.DesiredCapabilities.CHROME
        caps['loggingPrefs'] = {'performance': 'DEBUG', 'browser': 'DEBUG'}
        opts = webdriver.ChromeOptions()
        if "mobile_emulation" in self.config:
            opts.add_experimental_option("mobileEmulation", self.config['mobile_emulation'])
        opts.add_experimental_option("perfLoggingPrefs", {
            "traceCategories": join(DEFAULT_TRACE_CATEGORIES, ",")})
        self.driver = webdriver.Chrome(executable_path=self.config['chromedriver_path'], chrome_options=opts)

    def on_tear_down_step(self, event):
        sleep(LOG_COMPLETION_WAIT)

        trace_capability = TraceCapability(self.session)
        f = trace_capability.open_trace_file(self.run, self.view, self.step)
        try:
            f.write("[\n")

            f.write(",\n".join(
                [json.dumps(json.loads(entry['message'])['message']['params']) for entry in
                 self.driver.get_log('performance')]
            ))

            f.write("\n]")
        finally:
            f.close()

    def _focus_window(self):
        window_handle = self.driver.current_window_handle
        self.driver.execute_async_script("alert('Focus');")
        self.driver.switch_to.alert.accept()
        self.driver.switch_to.window(window_handle)


class ChromeTraceParser(Provider):
    def on_tear_down_run(self, event):
        trace_capability = TraceCapability(self.session)

        i = 1
        trace_files = trace_capability.get_trace_files()
        for f in trace_files:
            logger.info("Parsing chrome trace files %d of %d" % (i, len(trace_files)))

            subprocess.check_output([
                sys.executable,
                "lib/trace/trace-parser.py",
                "-t", os.path.join(self.session.result_dir.folder, f.file),
                "-u", os.path.join(self.session.result_dir.folder, trace_capability.get_user_timing_file(f)),
                "-c", os.path.join(self.session.result_dir.folder, trace_capability.get_timeline_cpu_file(f)),
                "-f", os.path.join(self.session.result_dir.folder, trace_capability.get_feature_usage_file(f))
            ], stderr=subprocess.STDOUT, env=os.environ.copy())
            i += 1
