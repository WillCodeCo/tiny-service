import logging
import asyncio
from titan.tiny_service.async_helper import AsyncTaskRunner
from titan.tiny_service import events


logger = logging.getLogger(__name__)



class EventStreamRecorderException(Exception):
    pass

class EventStreamRecorder:
    def __init__(self, event_producer, event_stream_writer):
        self._event_producer = event_producer
        self._event_stream_writer = event_stream_writer
        self._task_runner = None

    async def _event_monitor(self):
        try:
            while True:
                event = await self._event_producer.receive_event()
                self._event_stream_writer.write_event(event)
        except events.EventProducerException as e:
            logger.error(f"EventStreamRecorder._event_monitor() stopping because of exception: {e}")
            raise

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        task = asyncio.create_task(self._event_monitor())
        self._task_runner = AsyncTaskRunner([task])
        await self._task_runner.start()

    async def run(self):
        await self.start()
        await self.wait_closed()

    async def wait_closed(self):
        if self._task_runner:
            await self._task_runner.wait_closed()

    async def close(self):
        if self._task_runner:
            await self._task_runner.close()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        close_task = asyncio.create_task(self.close())
        try:
            await asyncio.shield(close_task)
        except asyncio.CancelledError:
            await close_task
            raise
        except Exception as e:
            logger.info(f"{self.__class__.__name__} is suppressing exception with type `{type(e)}` : {e}")
