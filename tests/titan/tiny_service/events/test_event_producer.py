import asyncio
import pytest
import random
import logging
from titan.tiny_service.async_helper import AsyncTaskRunner, AsyncTaskHelper
from titan.tiny_service.events import (
    EventProducer,
    EventProducerException,
    EventProducerSplitter
)
from tests.titan.tiny_service.events.sample_events import (
    DummyEvent
)

logger = logging.getLogger(__name__)



class DummyEventGenerator:
    @classmethod
    def generate_dummy_events(cls, event_count):
        for x in range(event_count):
            yield DummyEvent.create(x)


class DummyEventProducer(EventProducer):
    def __init__(self, event_generator):
        self._task_runner = None
        self._event_queue = asyncio.Queue(maxsize=1)
        self._event_generator = event_generator

    @classmethod
    async def produce_events_to_queue(cls, event_generator, event_queue):
        for event in event_generator:
            await event_queue.put(event)

    async def receive_event(self):
        return await self._event_queue.get()    

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        task = asyncio.create_task(self.produce_events_to_queue(self._event_generator, self._event_queue))
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


class FilteringEventProducer(EventProducer):
    def __init__(self, source_event_producer, filter_fn):
        self._source_event_producer = source_event_producer
        self._event_queue = asyncio.Queue(maxsize=1)
        self._filter_fn = filter_fn

    @classmethod
    async def filter_events(cls, event_producer, filter_fn, output_event_queue):
        while True:
            event = await event_producer.receive_event()
            if filter_fn(event):
                await output_event_queue.put(event)

    async def receive_event(self):
        return await self._event_queue.get()    

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        task = asyncio.create_task(self.filter_events(self._source_event_producer, self._filter_fn, self._event_queue))
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


class DummyEventTester:
    def __init__(self, event_producer, target_events):
        self._event_producer = event_producer
        self._target_events = target_events
        self._task_runner = None

    @classmethod
    async def test_event_producer_against_target(cls, event_producer, target_events):
        try:
            for target_event in target_events:
                event = await event_producer.receive_event()
                assert event == target_event, f"Received event {event} not the expected {target_event}"
                logger.info(f"{event} was received as expected")
        except AssertionError as e:
            logger.error(f"DummyEventTester.test_event_producer_against_target() stopping because of an event mismatch: {e}")
            raise
        except EventProducerException as e:
            logger.error(f"DummyEventTester.test_event_producer_against_target() stopping because of exception: {e}")
            raise

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        task = asyncio.create_task(self.test_event_producer_against_target(self._event_producer, self._target_events))
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




@pytest.mark.asyncio
async def test_event_producer():
    test_events = list(DummyEventGenerator.generate_dummy_events(100))
    async with DummyEventProducer(test_events) as event_producer:
        async with DummyEventTester(event_producer, test_events) as dummy_event_tester:
            tasks = [
                asyncio.create_task(dummy_event_tester.wait_closed()),
                asyncio.create_task(asyncio.sleep(1))
            ]
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()
                assert (not tasks[0].cancelled()), "Testing of event producer did not complete"





@pytest.mark.asyncio
async def test_single_event_splitter():
    test_events = list(DummyEventGenerator.generate_dummy_events(100))
    async with DummyEventProducer(test_events) as event_producer:
        async with EventProducerSplitter(event_producer) as event_producer_splitter:
            async with DummyEventTester(event_producer_splitter.clone(), test_events) as dummy_event_tester:
                tasks = [
                    asyncio.create_task(dummy_event_tester.wait_closed()),
                    asyncio.create_task(asyncio.sleep(5))
                ]
                async with AsyncTaskRunner(tasks) as task_runner:
                    await task_runner.wait_closed()
                    assert (not tasks[0].cancelled()), "Testing of event producer did not complete"



@pytest.mark.asyncio
async def test_multiple_event_splitter():
    test_events_a = list(DummyEventGenerator.generate_dummy_events(1000))
    test_events_b = list(DummyEventGenerator.generate_dummy_events(1000))
    async with DummyEventProducer(test_events_a) as event_producer_a:
        async with DummyEventProducer(test_events_b) as event_producer_b:           
            async with EventProducerSplitter(event_producer_a) as event_producer_splitter_a, EventProducerSplitter(event_producer_b) as event_producer_splitter_b:
                async with DummyEventTester(event_producer_splitter_a.clone(), test_events_a) as dummy_event_tester_a:
                    async with DummyEventTester(event_producer_splitter_b.clone(), test_events_b) as dummy_event_tester_b:
                        tasks = [
                            asyncio.create_task(dummy_event_tester_a.wait_closed()),
                            asyncio.create_task(dummy_event_tester_b.wait_closed()),
                            asyncio.create_task(asyncio.sleep(5))
                        ]
                        async with AsyncTaskRunner(tasks) as task_runner:
                            await task_runner.wait_closed()
                            assert (not tasks[0].cancelled()), "Testing of event producer-a did not complete"
                            assert (not tasks[1].cancelled()), "Testing of event producer-b did not complete"


@pytest.mark.asyncio
async def test_interdependant_event_splitter():
    def filter_event_fn(event):
        return event.seq() % 3 == 0

    test_events_a = list(DummyEventGenerator.generate_dummy_events(50000))
    test_events_b = list(filter(filter_event_fn, test_events_a))

    async with DummyEventProducer(test_events_a) as event_producer_a:
        async with EventProducerSplitter(event_producer_a) as event_producer_splitter_a:
            async with FilteringEventProducer(event_producer_splitter_a.clone(), filter_event_fn) as event_producer_b:
                async with EventProducerSplitter(event_producer_b) as event_producer_splitter_b:
                    async with DummyEventTester(event_producer_splitter_a.clone(), test_events_a) as dummy_event_tester_a:
                        async with DummyEventTester(event_producer_splitter_b.clone(), test_events_b) as dummy_event_tester_b:
                            async with DummyEventTester(event_producer_splitter_b.clone(), test_events_b) as dummy_event_tester_bb:
                                tasks = [
                                    asyncio.create_task(dummy_event_tester_a.wait_closed()),
                                    asyncio.create_task(dummy_event_tester_b.wait_closed()),
                                    asyncio.create_task(dummy_event_tester_bb.wait_closed())
                                ]
                                try:
                                    await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks, timeout=45)
                                except asyncio.TimeoutError:
                                    pytest.fail(f"Timeout occurred when testing events")
