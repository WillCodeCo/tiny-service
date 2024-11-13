import random
import pytest
import logging
from titan.tiny_service.service.service_bus import service_bus_messages
from titan.tiny_service.service.service_bus import (
    EventMessageCache,
    EventMessageCacheException
)


logger = logging.getLogger(__name__)


def generate_random_event_messages(rng, count: int):
    for x in range(count):
        byte_len = random.randint(3,10)
        event_bytes = random.getrandbits(byte_len * 8).to_bytes(length=byte_len, byteorder='big')
        yield service_bus_messages.EventMessage(seq=x, event_type='DummyEvent', event_bytes=event_bytes)



def test_event_message_cache():
    num_test_event_messages = 100
    max_size = 5
    test_event_messages = list(generate_random_event_messages(random.Random(42), num_test_event_messages))
    event_message_cache = EventMessageCache(max_size)

    assert event_message_cache.latest_event_messages(0) == []
    try:
        event_message_cache.latest_event_messages(1)
        pytest.fail(f"An exception should be raised if the cache does not contain an event_message with specified seq number")
    except EventMessageCacheException:
        pass

    for event_message in test_event_messages:
        event_message_cache.add(event_message)
        assert event_message_cache.size() <= max_size

    assert event_message_cache.first_event_message() == test_event_messages[-max_size]
    assert event_message_cache.last_event_message() == test_event_messages[-1]
    assert event_message_cache.last_event_message().seq() == num_test_event_messages - 1

    try:
        event_message_cache.latest_event_messages(num_test_event_messages + 1)
        pytest.fail(f"An exception should be raised if the cache does not contain all the event_messages required")
    except EventMessageCacheException:
        pass


    assert event_message_cache.latest_event_messages(min_event_message_seq=num_test_event_messages) == [], "There should be no newer event messages"
    assert event_message_cache.latest_event_messages(min_event_message_seq=num_test_event_messages - 1) == [test_event_messages[-1]], "There should be no newer event messages"
    assert len(event_message_cache.latest_event_messages(min_event_message_seq=num_test_event_messages-max_size)) == 5
    assert event_message_cache.latest_event_messages(min_event_message_seq=num_test_event_messages-max_size) == test_event_messages[(num_test_event_messages-max_size):] 
    
    try:
        event_message_cache.latest_event_messages(0)
        pytest.fail(f"An exception should be raised if the cache does not contain all the event_messages required")
    except EventMessageCacheException:
        pass
