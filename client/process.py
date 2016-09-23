import collections
import logging
import os
import subprocess
import threading

logger = logging.getLogger(__name__)


class ReaderThread(threading.Thread):
    def __init__(self, process, stream, name):
        super(ReaderThread, self).__init__()
        self.stream = stream
        self.process = process
        self.name = name
        self.buffer = collections.deque(maxlen=1024)

    def run(self):
        while self.process.poll() is None:
            output = self.stream.readline(100)
            if output != '':
                logger.debug("%s> %s" % (self.name, output.strip()))
                self.buffer.append(output)
        logger.debug("%s closed" % self.name)
        return

    def contains(self, s):
        for row in self.buffer:
            if s in row:
                return True
        return False


def run(cmd, shell=False):
    logger.info("About to run cmd '%s'" % (cmd if type(cmd) == str else " ".join(cmd)))
    process, stdout_reader, stderr_reader = _launch(cmd, shell)

    # Wait for process to complete
    return_code = process.wait()

    # and then wait for reader threads to complete
    stdout_reader.join()
    stderr_reader.join()

    output = "".join(stdout_reader.buffer)
    if return_code != 0:
        logger.warn("Process return non-zero return code, output = %s" % output)
        raise subprocess.CalledProcessError(return_code, cmd, output=output)
    else:
        return output


def launch(cmd, shell=False, wait_for=None):
    logger.info("About to launch cmd '%s'" % (cmd if type(cmd) == str else " ".join(cmd)))
    return _launch(cmd, shell)


def _launch(cmd, shell=False):
    process = subprocess.Popen(cmd, shell=shell, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=os.environ.copy())

    stdout_reader = ReaderThread(process, process.stdout, "STDOUT")
    stdout_reader.start()

    stderr_reader = ReaderThread(process, process.stderr, "STDERR")
    stderr_reader.start()

    return process, stdout_reader, stderr_reader
