import logging

from client.provider import Provider, event_order

logger = logging.getLogger(__name__)


class LoggingProvider(Provider):
    def __init__(self, event_bus, config):
        Provider.__init__(self, event_bus, config, lock_on="session")

    def on_start_session(self, e):
        super(LoggingProvider, self).on_start_session(e)
        logger.info("Start session %s" % e.session.result_dir.folder)

    def on_start_run(self, e):
        super(LoggingProvider, self).on_start_run(e)
        logger.info("Start run %d" % e.run.current)

    def on_start_view(self, e):
        super(LoggingProvider, self).on_start_view(e)
        logger.info("Start %s view " % ("first" if e.view.is_first else "repeate"))

    def on_start_step(self, e):
        super(LoggingProvider, self).on_start_step(e)
        logger.info("Start step %d - %s" % (e.step.index, e.step.name))


event_order["on_start_session"].insert(0, LoggingProvider)
event_order["on_start_run"].insert(0, LoggingProvider)
event_order["on_start_view"].insert(0, LoggingProvider)
event_order["on_start_step"].insert(0, LoggingProvider)