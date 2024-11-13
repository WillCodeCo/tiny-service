import asyncio
import random
import pytest
import os
import tempfile
from titan import tiny_service
import titan.tiny_service.events
import titan.tiny_service.event_stream
from tests.titan.tiny_service.event_stream.sample_events import (
    DummyStartedEvent,
    DummyNoStateChangeEvent,
    DummyStateXEvent,
    DummyStateYEvent,
    DummyStateZEvent,
    DummyFinishedEvent,
)


class DummyEventStreamFileReader(tiny_service.event_stream.EventStreamFileReader):
    @classmethod
    def deserialize_event(cls, event_type: str, event_bytes: bytes):
        if event_type == DummyStartedEvent.event_type():
            return DummyStartedEvent.create_from_bytes(event_bytes)
        elif event_type == DummyNoStateChangeEvent.event_type():
            return DummyNoStateChangeEvent.create_from_bytes(event_bytes)
        elif event_type == DummyStateXEvent.event_type():
            return DummyStateXEvent.create_from_bytes(event_bytes)
        elif event_type == DummyStateYEvent.event_type():
            return DummyStateYEvent.create_from_bytes(event_bytes)
        elif event_type == DummyStateZEvent.event_type():
            return DummyStateZEvent.create_from_bytes(event_bytes)
        elif event_type == DummyFinishedEvent.event_type():
            return DummyFinishedEvent.create_from_bytes(event_bytes)
        else:
            raise tiny_service.event_stream.EventStreamException(f"Cannot deserialize event `{event_type}` as the class could not be found!")




class DummyEventProducer(tiny_service.events.EventProducer):
    @classmethod
    def generate_events(cls, event_count):
        rng = random.Random(42)
        result = [DummyStartedEvent.create()]
        for x in range(event_count-2):
            event_class = rng.choice([DummyNoStateChangeEvent, DummyStateXEvent, DummyStateYEvent, DummyStateZEvent])
            result.append(event_class.create())
        result += [DummyFinishedEvent.create()]
        return result

    def __init__(self, event_generator):
        self._event_generator = event_generator

    async def receive_event(self):
        await asyncio.sleep(0.005)
        try:
            event = next(self._event_generator)
            return event
        except StopIteration:
            raise tiny_service.events.EventProducerException("No more events available")




def generate_event_stream(event_stream_meta, events):
    result_stream = tiny_service.event_stream.EventStream(event_stream_meta)
    for event in events:
        result_stream.write_event(event)
    return result_stream


def test_event_stream():
    TEST_EVENT_COUNT = 100
    test_events = DummyEventProducer.generate_events(TEST_EVENT_COUNT)
    test_event_stream_meta = {'field-a': 42, 'field-b': False}
    test_event_stream = generate_event_stream(test_event_stream_meta, test_events)
    assert list(test_event_stream.events()) == test_events
    assert len(list(test_event_stream.events())) == TEST_EVENT_COUNT
    assert test_event_stream.metadata() == {'field-a': 42, 'field-b': False}



def test_event_stream_io():
    TEST_EVENT_COUNT = 100
    test_events = DummyEventProducer.generate_events(TEST_EVENT_COUNT)
    test_event_stream_meta = {'field-a': 42, 'field-b': False}
    test_event_stream = generate_event_stream(test_event_stream_meta, test_events)
    with tempfile.TemporaryDirectory() as working_dir:
        with open(os.path.join(working_dir, 'stream.events'), 'wb') as file_obj:
            event_stream_file_writer = tiny_service.event_stream.EventStreamFileWriter(file_obj, test_event_stream.metadata())
            for event in test_event_stream.events():
                event_stream_file_writer.write_event(event)
        # check we can read it back
        with open(os.path.join(working_dir, 'stream.events'), 'rb') as file_obj:
            event_stream_file_reader = DummyEventStreamFileReader(file_obj)
            assert list(event_stream_file_reader.events()) == list(test_event_stream.events())
            assert len(list(event_stream_file_reader.events())) == TEST_EVENT_COUNT
            assert event_stream_file_reader.metadata() == test_event_stream.metadata()



@pytest.mark.asyncio
async def test_event_recorder():
    TEST_EVENT_COUNT = 100
    test_events = DummyEventProducer.generate_events(TEST_EVENT_COUNT)
    test_event_stream_meta = {'dummy': 0.4242}
    test_event_stream = generate_event_stream(test_event_stream_meta, test_events)
    event_producer = DummyEventProducer((event for event in test_events))
    #
    with tempfile.TemporaryDirectory() as working_dir:
        with open(os.path.join(working_dir, 'stream.events'), 'wb') as file_obj:
            event_stream_file_writer = tiny_service.event_stream.EventStreamFileWriter(file_obj, test_event_stream_meta)
            async with tiny_service.event_stream.EventStreamRecorder(event_producer, event_stream_file_writer) as event_stream_recorder:
                try:
                    await event_stream_recorder.wait_closed()
                except tiny_service.events.EventProducerException as e:
                    assert str(e) == "No more events available"

        # check we can read it back
        with open(os.path.join(working_dir, 'stream.events'), 'rb') as file_obj:
            event_stream_file_reader = DummyEventStreamFileReader(file_obj)
            assert list(event_stream_file_reader.events()) == test_events
            assert len(list(event_stream_file_reader.events())) == TEST_EVENT_COUNT
            assert event_stream_file_reader.metadata() == test_event_stream_meta




@pytest.mark.asyncio
async def test_event_stream_replayer():
    TEST_EVENT_COUNT = 100
    test_events = DummyEventProducer.generate_events(TEST_EVENT_COUNT)
    test_event_stream_meta = {'dummy': 0.4242}
    test_event_stream = generate_event_stream(test_event_stream_meta, test_events)
    #
    with tempfile.TemporaryDirectory() as working_dir:
        with open(os.path.join(working_dir, 'stream.events'), 'wb') as file_obj:
            event_stream_file_writer = tiny_service.event_stream.EventStreamFileWriter(file_obj, test_event_stream.metadata())
            for event in test_event_stream.events():
                event_stream_file_writer.write_event(event)
        # start an event replayer from the file
        with open(os.path.join(working_dir, 'stream.events'), 'rb') as file_obj:
            event_stream_file_reader = DummyEventStreamFileReader(file_obj)
            event_stream_replayer = tiny_service.event_stream.EventStreamReplayer(event_stream_file_reader, 1)
            event_stream_replayer.start()
            # record the replayed events to a new file so we can check it produces same output
            with open(os.path.join(working_dir, 'stream-clone.events'), 'wb') as file_obj_2:
                event_stream_file_writer = tiny_service.event_stream.EventStreamFileWriter(file_obj_2, event_stream_file_reader.metadata())
                async with tiny_service.event_stream.EventStreamRecorder(event_stream_replayer, event_stream_file_writer) as event_stream_recorder:
                    try:
                        await event_stream_recorder.wait_closed()
                    except tiny_service.events.EventProducerException as e:
                        assert str(e) == "No more events in the stream."

            # check we can read it back
            with open(os.path.join(working_dir, 'stream-clone.events'), 'rb') as file_obj:
                event_stream_file_reader = DummyEventStreamFileReader(file_obj)
                assert list(event_stream_file_reader.events()) == test_events
                assert len(list(event_stream_file_reader.events())) == TEST_EVENT_COUNT
                assert event_stream_file_reader.metadata() == test_event_stream_meta
