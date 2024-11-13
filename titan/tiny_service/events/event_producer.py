import asyncio
import collections
from titan.tiny_service.async_helper import AsyncTaskRunner, AsyncQueue, AsyncPubSub


class EventProducerException(Exception):
    pass

class EventProducer:
    async def receive_event(self):
        raise NotImplementedError


class EventProducerClone:
    __slots__= ("_event_subscriber",)
    
    def __init__(self, event_subscriber):
        self._event_subscriber = event_subscriber

    async def receive_event(self):
        return await self._event_subscriber.get()


class EventProducerSplitter:
    def __init__(self, event_producer):
        self._source_event_producer = event_producer
        self._event_pub_sub = AsyncPubSub()

    @classmethod
    async def event_publisher(cls, event_producer, event_pub_sub):
        try:
            while True:
                event = await event_producer.receive_event()
                await event_pub_sub.publish(event)
        except asyncio.CancelledError:
            event_pub_sub.cancel()
        except EventProducerException as e:
            event_pub_sub.set_exception(e)

    def clone(self):
        return EventProducerClone(event_subscriber=self._event_pub_sub.create_subscriber())

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        tasks = [
            asyncio.create_task(EventProducerSplitter.event_publisher(self._source_event_producer, self._event_pub_sub))
        ]
        self._task_runner = AsyncTaskRunner(tasks)
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

