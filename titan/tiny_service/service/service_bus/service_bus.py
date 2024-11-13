import asyncio
import collections
import itertools
from titan.tiny_service.async_helper import AsyncQueue, AsyncPubSub, AsyncTaskRunner
from titan.tiny_service.service.service_bus import service_bus_messages
import logging

logger = logging.getLogger(__name__)


class ServiceBusException(Exception):
    pass


class EventMessageCacheException(Exception):
    pass

class EventMessageCache:
    def __init__(self, max_size: int):
        self._head_index = None
        self._tail_index = None
        self._max_size = max_size
        self._event_messages = []

    def size(self):
        return len(self._event_messages)

    def is_empty(self):
        return (self._head_index is None)

    def first_event_message(self):
        if self.is_empty():
            raise EventMessageCacheException(f"Cache is empty")
        return self._event_messages[self._tail_index]

    def last_event_message(self):
        if self.is_empty():
            raise EventMessageCacheException(f"Cache is empty")
        return self._event_messages[self._head_index]        

    def contains_seq(self, seq: int):
        return (seq >= self.first_event_message().seq()) and (seq <= self.last_event_message().seq())

    def latest_event_messages(self, min_event_message_seq: int):
        """Return the event messages with seq number greater than or equal to min_event_message_seq"""
        if (self.is_empty()) and (min_event_message_seq==0):
            return []
        elif self.is_empty():
            raise EventMessageCacheException(f"Cache is empty, cannot return latest_event_messages for min_event_message_seq={min_event_message_seq}")
        elif min_event_message_seq == self.last_event_message().seq() + 1:
            return []
        elif (not self.contains_seq(min_event_message_seq)):
            raise EventMessageCacheException(f"Cannot invoke latest_event_messages() because min_event_message_seq {min_event_message_seq} is not present in the cache")
        else:
            num_items_to_skip = min_event_message_seq - self.first_event_message().seq()
            origin_offset = (self._tail_index + num_items_to_skip) % self._max_size
            if origin_offset <= self._head_index:
                return self._event_messages[origin_offset: self._head_index + 1]
            else:
                # need to wrap around
                return self._event_messages[origin_offset:] + self._event_messages[:self._head_index+1]

    def add(self, event_message: service_bus_messages.EventMessage):
        if self.is_empty():
            self._head_index = 0
            self._tail_index = 0
            self._event_messages.append(event_message)
        elif self.size() < self._max_size:
            self._event_messages.append(event_message)
            self._head_index = self.size() - 1
        else:
            self._event_messages[self._tail_index] = event_message
            self._head_index = self._tail_index
            self._tail_index = (self._tail_index + 1) % self._max_size



class CommandBusCacheException(Exception):
    pass

class CommandBusCache:
    def __init__(self):
        self._command_message = None
        self._command_receipt_message = None

    def save_command_message(self, command_message: service_bus_messages.CommandMessage):
        self._command_message = command_message
        self._command_receipt_message = None

    def save_command_receipt_message(self, command_receipt_message: service_bus_messages.CommandReceiptMessage):
        if self._command_message is None:
            raise CommandBusCacheException("Cannot save a command_receipt_message before a command_message is saved !")
        self._command_receipt_message = command_receipt_message

    def last_command_message(self):
        if self._command_message is None:
            raise CommandBusCacheException
        return self._command_message

    def last_command_receipt_message(self):
        if self._command_receipt_message is None:
            raise CommandBusCacheException
        return self._command_receipt_message

    def has_command_message(self):
        return self._command_message is not None

    def has_command_receipt_message(self):
        return self._command_receipt_message is not None




class ServiceBusServer:
    async def receive_command_message(self):
        pass

    async def send_command_receipt_message(self, command_receipt_message: service_bus_messages.CommandReceiptMessage):
        pass

    async def send_event_message(self, event_message: service_bus_messages.EventMessage):
        pass


class ServiceBusClient:
    async def catchup_event_messages(self):
        pass

    async def receive_event_message(self):
        pass

    async def send_command_message(self, command_message: service_bus_messages.CommandMessage):
        pass

    async def receive_command_receipt_message(self):
        pass