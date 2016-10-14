import inspect
import traceback
from argparse import ArgumentParser
import logging
import re

from fasteners import InterProcessLock

from client.model import Run
from client.model import View

LOCK_TIMEOUT = 60
LOCK_MAX_DELAY = 0.5
LOCK_DELAY = 0.1

logger = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self):
        self.listeners = []
        self.event_queue = []
        self.current_event = None

    def add(self, listener):
        self.listeners.append(listener)

    def emit(self, event):
        self.event_queue.append(event)

        if not self.current_event:
            while len(self.event_queue) > 0:
                self.process_next_event()

    def process_next_event(self):
        if len(self.event_queue) == 0:
            return

        self.current_event = self.event_queue.pop(0)
        try:
            method_name = self._event_to_method_name(self.current_event)
            methods = [getattr(c, method_name) for c in self.listeners if hasattr(c, method_name)]
            for m in self._order_event_listeners(methods, event_order[method_name]):
                m(self.current_event)
        finally:
            self.current_event = None

    def _order_event_listeners(self, methods, order):
        method_order = {}
        for m in methods:
            found = False
            for type in inspect.getmro(m.im_self.__class__):
                for idx, val in enumerate(order):
                    if val == type:
                        method_order[m] = idx
                        found = True
                        break
                if found:
                    break
            if not found:
                method_order[m] = 100

        return sorted(methods, key=lambda i: method_order[i])

    def _event_to_method_name(self, event):
        return "on" + re.sub(r'([A-Z])', r'_\1', event.name, flags=re.DOTALL).lower()


class Event:
    def __init__(self, name, **kwargs):
        self.name = name
        for k, v in kwargs.iteritems():
            self.__dict__[k] = v


def start_session(event_bus, session):
    try:
        event_bus.emit(Event("StartSession", session=session))

        for i in range(0, session.run_count):
            run = Run(i + 1)

            event_bus.emit(Event("StartRun", run=run))

            view = View(is_first=True, is_repeat=False)

            event_bus.emit(Event("StartView", view=view))
            event_bus.emit(Event("StopView", view=view))

            event_bus.emit(Event("StopRun", run=run))

        event_bus.emit(Event("StopSession", session=session))

    except:
        traceback.print_exc()
        event_bus.emit(Event("Abort"))
        raise


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

    def lock(self, lock_name=None):
        if self.config['lockfile']:
            if self.lock_on and lock_name and self.lock_on != lock_name:
                return
            logger.info("Acquiring lock for %r using file %r" % (self.__class__.__name__, self.config['lockfile']))
            self.lock_file = InterProcessLock(self.config['lockfile'])
            self.lock_file.acquire(delay=LOCK_DELAY, max_delay=LOCK_MAX_DELAY, timeout=LOCK_TIMEOUT)

    def unlock(self, lock_name=None):
        if self.lock_file:
            if self.lock_on and lock_name and self.lock_on != lock_name:
                return
            logger.info("Releasing lock for %r using file %r" % (self.__class__.__name__, self.config['lockfile']))
            self.lock_file.release()
            self.lock_file = None

    def on_start_session(self, event):
        self.lock("session")
        self.session = event.session

    def on_start_run(self, event):
        self.lock("run")
        self.run = event.run
        self.session.add_run(event.run)

    def on_start_view(self, event):
        self.lock("view")
        self.view = event.view
        self.run.add_view(event.view)

    def on_start_step(self, event):
        self.lock("step")
        self.step = event.step
        self.view.add_step(event.step)

    def on_stop_session(self, event):
        self.session = None
        self.unlock("session")

    def on_stop_run(self, event):
        self.run = None
        self.unlock("run")

    def on_stop_view(self, event):
        self.view = None
        self.unlock("view")

    def on_stop_step(self, event):
        self.step = None
        self.unlock("step")

    def on_abort(self, event):
        self.unlock()


class PostProcessingProvider(Provider):
    pass


class VideoRecordingProvider(Provider):
    pass


class BrowserProvider(Provider):
    pass


class ConnectionProvider(Provider):
    pass


event_order = {
    "on_start_session": [ConnectionProvider, VideoRecordingProvider, BrowserProvider, PostProcessingProvider],
    "on_stop_session": [BrowserProvider, VideoRecordingProvider, ConnectionProvider, PostProcessingProvider],
    "on_start_run": [ConnectionProvider, VideoRecordingProvider, BrowserProvider, PostProcessingProvider],
    "on_stop_run": [BrowserProvider, VideoRecordingProvider, ConnectionProvider, PostProcessingProvider],
    "on_start_view": [ConnectionProvider, VideoRecordingProvider, BrowserProvider, PostProcessingProvider],
    "on_stop_view": [BrowserProvider, VideoRecordingProvider, ConnectionProvider, PostProcessingProvider],
    "on_start_step": [ConnectionProvider, VideoRecordingProvider, BrowserProvider, PostProcessingProvider],
    "on_stop_step": [BrowserProvider, VideoRecordingProvider, ConnectionProvider, PostProcessingProvider]
}
