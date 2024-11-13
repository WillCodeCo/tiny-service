import logging
import asyncio
from titan.tiny_service import events
from titan.tiny_service.time_source import InterpolatingDiscreteTimeSource

logger = logging.getLogger(__name__)



class EventStreamReplayerException(events.EventProducerException):
    pass

class EventStreamReplayer(events.EventProducer):
    def __init__(self, event_stream, replay_speed, focus_timestamp=None):
        events.EventProducer.__init__(self)
        self._time_source = InterpolatingDiscreteTimeSource(
            discrete_timestamp_generator=(event.timestamp() for event in event_stream.events()),
            multiplier=replay_speed,
            focus_timestamp=focus_timestamp
        )
        self._event_stream = event_stream
        self._event_generator = None
        self._last_event = None
        self._resume_future = None

    def start(self):
        self._time_source.start()
        self._last_event = None
        self._event_generator = self._event_stream.events()

    def active(self):
        return (self._event_generator is not None)

    async def pause(self):
        self._resume_future = asyncio.get_running_loop().create_future()
        await self._resume_future

    def time_source(self):
        return self._time_source
        
    def resume(self):
        self._resume_future.set_result(True)
        self._resume_future = None

    def pause_for_event(self, event):
        return False

    def is_paused(self):
        return (self._resume_future is not None) and (not self._resume_future.done())

    async def receive_event(self):
        try:
            event = next(self._event_generator)
            if self._last_event and event.timestamp() < self._last_event.timestamp():
                raise EventStreamReplayerException(f"Cannot replay event stream, because event {event.event_id()} has time travelled")   
            # event specific pause ?
            if self.pause_for_event(event):
                await self.pause()
            # wait for appropriate time for event
            await self._time_source.sleep_until(event.timestamp())
            self._time_source.resume_next_period()
            # remember last event
            self._last_event = event
            return event
        except StopIteration:
            self._event_generator = None
            raise events.EventProducerException(f"No more events in the stream.")

    @staticmethod
    def create_dumping_replayer(service_bus_server, event_stream):
        return EventStreamReplayer(event_stream, 99999)

