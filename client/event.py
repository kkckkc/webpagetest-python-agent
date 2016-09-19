import traceback

from model import Run, View
from collections import namedtuple


class EventDispatcher:
    def __init__(self):
        self.listeners = []

    def add(self, listener):
        self.listeners.append(listener)

    def emit(self, event):
        for c in self.listeners:
            c.on_event(event)


SetupSessionEvent = namedtuple('SetupSessionEvent', 'session')
StartSessionEvent = namedtuple('StartSessionEvent', 'session')
EndSessionEvent = namedtuple('EndSessionEvent', 'session')
TearDownSessionEvent = namedtuple('TearDownSessionEvent', 'session')

SetupRunEvent = namedtuple('SetupRunEvent', 'run')
StartRunEvent = namedtuple('StartRunEvent', 'run')
EndRunEvent = namedtuple('EndRunEvent', 'run')
TearDownRunEvent = namedtuple('TearDownRunEvent', 'run')

SetupViewEvent = namedtuple('SetupViewEvent', 'view')
StartViewEvent = namedtuple('StartViewEvent', 'view')
EndViewEvent = namedtuple('EndViewEvent', 'view')
TearDownViewEvent = namedtuple('TearDownViewEvent', 'view')

SetupStepEvent = namedtuple('SetupStepEvent', 'step')
StartStepEvent = namedtuple('StartStepEvent', 'step')
EndStepEvent = namedtuple('EndStepEvent', 'step')
TearDownStepEvent = namedtuple('TearDownStepEvent', 'step')

AbortEvent = namedtuple('AbortEvent', '')


def run(event_bus, session):
    try:
        event_bus.emit(SetupSessionEvent(session))
        event_bus.emit(StartSessionEvent(session))

        for i in range(0, session.run_count):
            run = Run(i + 1)

            event_bus.emit(SetupRunEvent(run))
            event_bus.emit(StartRunEvent(run))

            view = View(is_first=True, is_repeat=False)

            event_bus.emit(SetupViewEvent(view))
            event_bus.emit(StartViewEvent(view))
            event_bus.emit(EndViewEvent(view))
            event_bus.emit(TearDownViewEvent(view))

            event_bus.emit(EndRunEvent(run))
            event_bus.emit(TearDownRunEvent(run))

        event_bus.emit(EndSessionEvent(session))
        event_bus.emit(TearDownSessionEvent(session))

    except:
        traceback.print_exc()
        event_bus.emit(AbortEvent())
        raise


