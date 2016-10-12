from argparse import ArgumentParser
import logging
import re

from fasteners import InterProcessLock

import event

LOCK_TIMEOUT = 60
LOCK_MAX_DELAY = 0.5
LOCK_DELAY = 0.1

logger = logging.getLogger(__name__)


class Provider(object):
    def __init__(self, event_bus, config, lock_on=None):
        self.event_bus = event_bus
        self.event_bus.add(self)
        self.config = config
        if "log_level" in config:
            if config['log_level'] == 1:
                self._init_logging(logging.INFO)
            elif config['log_level'] >= 2:
                self._init_logging(logging.DEBUG)
        self.session = None
        self.run = None
        self.view = None
        self.step = None
        self.lock_file = None
        self.lock_on = lock_on

    @classmethod
    def argparser(cls):
        p = ArgumentParser(description=cls.__name__, prog=cls.__name__, add_help=False)
        p.add_argument('-v', '--verbose', dest='log_level', action='count',
                       help="Increase verbosity (specify multiple times for more). -vv for full debug output.")
        p.add_argument('--lockfile', dest='lockfile')
        return p

    def _init_logging(self, level):
        logging.getLogger(self.__class__.__module__).setLevel(level)

    def lock(self):
        if self.config['lockfile']:
            logger.info("Acquiring lock for %r using file %r" % (self.__class__.__name__, self.config['lockfile']))
            self.lock_file = InterProcessLock(self.config['lockfile'])
            self.lock_file.acquire(delay=LOCK_DELAY, max_delay=LOCK_MAX_DELAY, timeout=LOCK_TIMEOUT)

    def unlock(self):
        if self.lock_file:
            logger.info("Releasing lock for %r using file %r" % (self.__class__.__name__, self.config['lockfile']))
            self.lock_file.release()

    def on_event(self, e):
        if self.lock_on and self.config['lockfile']:
            if type(e).__name__ == ("Setup%sEvent" % self.lock_on.capitalize()):
                self.lock()

        if type(e) == event.SetupSessionEvent:
            self.session = e.session
        elif type(e) == event.SetupRunEvent:
            self.run = e.run
            self.session.add_run(e.run)
        elif type(e) == event.SetupViewEvent:
            self.view = e.view
            self.run.add_view(e.view)
        elif type(e) == event.SetupStepEvent:
            self.step = e.step
            self.view.add_step(e.step)

        method_name = "on" + re.sub(r'([A-Z])', r'_\1', type(e).__name__, flags=re.DOTALL).lower()[:-6]
        method = None
        try:
            method = getattr(self, method_name)
        except AttributeError:
            pass
        if method:
            method(e)

        if type(e) == event.TearDownSessionEvent:
            self.session = None
        elif type(e) == event.TearDownRunEvent:
            self.run = None
        elif type(e) == event.TearDownViewEvent:
            self.view = None
        elif type(e) == event.TearDownStepEvent:
            self.step = None

        if self.lock_on and self.lock_file:
            if type(e).__name__ == ("TearDown%sEvent" % self.lock_on.capitalize()) or type(e) == event.AbortEvent:
                self.unlock()
