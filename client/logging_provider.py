import logging

from client import event
from client.provider import Provider

logger = logging.getLogger(__name__)


class LoggingProvider(Provider):
    def __init__(self, event_bus, config):
        Provider.__init__(self, event_bus, config, lock_on="session")

    def on_event(self, e):
        if type(e) == event.StartSessionEvent:
            logger.info("Start session %s" % e.session.result_dir.folder)
        elif type(e) == event.StartRunEvent:
            logger.info("Start run %d" % e.run.current)
        elif type(e) == event.StartViewEvent:
            logger.info("Start %s view " % ("first" if e.view.is_first else "repeate"))
        elif type(e) == event.StartStepEvent:
            logger.info("Start step %d - %s" % (e.step.index, e.step.name))