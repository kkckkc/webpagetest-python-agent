import unittest
import os

from client.agent import Agent
from client.log import init_log

init_log(4)


class TestAgent(unittest.TestCase):
    def test_writes_job_file(self):
        s = "Test ID=160912_AD_1\nurl=http://www.ikea.com/ie/en/"

        def run_job(job_id, result_dir):
            self.assertEqual("160912_AD_1", job_id)
            self.assertEqual(len(s), os.stat(os.path.join(result_dir.folder, "test.job")).st_size)

        agent = Agent("http://localhost", "Location", run_job)
        agent.spawn_job(s)

    def test_poll(self):
        agent = Agent("http://localhost", "Location", run_job)

