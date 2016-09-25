import ConfigParser
import io
import logging
import shutil
import sys
import tempfile

from time import sleep
from urllib import urlencode
from urllib2 import urlopen, URLError

from client.model import ResultDirectory

log = logging.getLogger(__name__)


class Agent:
    def __init__(self, url, location, job):
        self.url = url
        self.location = location
        self.job = job
        self.poll_interval = 10
        log.info("Starting agent polling %s at interval %ds" % (self.url, self.poll_interval))

    def start(self):
        while True:
            log.info("Polling for job")
            try:
                query_string = urlencode({"location": self.location})
                url = "{}/{}?{}".format(self.url, "work/getwork.php", query_string)
                res = urlopen(url).read()
            except URLError:
                log.error("Error trying to poll for job, trying again later", exc_info=sys.exc_info())
                sleep(self.poll_interval)
                continue

            if res.strip() != "":
                self.spawn_job(res)
            else:
                log.info("No job found")
            sleep(self.poll_interval)

    def spawn_job(self, job_description):
        config = ConfigParser.ConfigParser()
        config.readfp(io.BytesIO("[Job]\n%s" % job_description))

        test_id = config.get("Job", "Test ID")
        log.info("Initiating job %s" % test_id)

        temp_directory = tempfile.mkdtemp(prefix='tmp_wpt_')
        log.debug("Using %s as result directory", temp_directory)
        try:
            result_dir = ResultDirectory(temp_directory)
            with result_dir.open_file("test.job") as job_file:
                job_file.write(job_description)

            self.job(test_id, result_dir)

        finally:
            shutil.rmtree(temp_directory)