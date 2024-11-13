import asyncio
import logging
from titan.tiny_service.async_helper import (
    AsyncTaskRunner,
    AsyncDynamicTaskRunner,
    AsyncQueue,
    AsyncPubSub
)
from titan.tiny_service.service.service_bus import (
    ServiceBusClient,
    ServiceBusServer,
    ServiceBusException,
    EventMessageCache,
    EventMessageCacheException
)
from titan.tiny_service.service.service_bus import service_bus_messages

logger = logging.getLogger(__name__)


INFINITE_DELAY = float('inf')



class MemoryServiceBusServer(ServiceBusServer):

    EVENT_MESSAGE_CACHE_SIZE = 10000
    
    def __init__(self):
        self._task_runner = None
        self._event_message_cache = EventMessageCache(MemoryServiceBusServer.EVENT_MESSAGE_CACHE_SIZE)
        self._event_message_pub_sub = AsyncPubSub()
        self._command_message_queue = AsyncQueue()
        self._command_receipt_message_queue = AsyncQueue()
        self._has_commandable_service_bus_client = False

    def create_service_bus_client(self):
        try:
            return MemoryServiceBusClient(  event_message_pub_sub=self._event_message_pub_sub,
                                            event_message_cache=self._event_message_cache )
        except EventMessageCacheException:
            raise ServiceBusException(f"Could not retrieve the catchup_event_messages needed to create the MemoryServiceBusClient")

    def create_commandable_service_bus_client(self):
        if self._has_commandable_service_bus_client:
            raise ServiceBusException(f"{self.__class__.__name__} already has a commandable_service_client. Cannot have more than one !")
        try:
            self._has_commandable_service_bus_client = True
            return MemoryCommandableServiceBusClient(   event_message_pub_sub=self._event_message_pub_sub,
                                                        event_message_cache=self._event_message_cache,
                                                        command_message_queue=self._command_message_queue,
                                                        command_receipt_message_queue=self._command_receipt_message_queue  )
        except EventMessageCacheException:
            raise ServiceBusException(f"Could not retrieve the catchup_event_messages needed to create the MemoryCommandableServiceBusClient")

    async def receive_command_message(self):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke receive_command_message() on a {self.__class__.__name__} that is not active")
        return await self._command_message_queue.get()

    async def send_command_receipt_message(self, command_receipt_message: service_bus_messages.CommandReceiptMessage):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke send_command_receipt_message() on a {self.__class__.__name__} that is not active")
        await self._command_receipt_message_queue.put(command_receipt_message)

    async def send_event_message(self, event_message: service_bus_messages.EventMessage):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke send_event_message() on a {self.__class__.__name__} that is not active")
        self._event_message_cache.add(event_message)
        await self._event_message_pub_sub.publish(event_message)

    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        # We don't have any async tasks to launch, so just start a dummy one
        dummy_task = asyncio.create_task(asyncio.sleep(INFINITE_DELAY))
        self._task_runner = AsyncTaskRunner([dummy_task])
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




class MemoryServiceBusClient(ServiceBusClient):
    def __init__(self, event_message_pub_sub, event_message_cache):
        self._event_message_pub_sub = event_message_pub_sub
        self._event_message_cache = event_message_cache
        self._catchup_event_messages = None
        self._next_event_message_seq = 0
        self._event_subscriber = None
        self._task_runner = None

    async def manage_event_subscriber(self):
        try:
            self._event_subscriber = self._event_message_pub_sub.create_subscriber()
            self._catchup_event_messages = self._event_message_cache.latest_event_messages(min_event_message_seq=0)
            if self._catchup_event_messages:
                self._next_event_message_seq = self._catchup_event_messages[-1].seq() + 1
            await asyncio.sleep(INFINITE_DELAY)
        finally:
            self._event_message_pub_sub.unsubscribe(self._event_subscriber)
            self._event_subscriber = None

    def next_event_message_seq(self):
        return self._next_event_message_seq

    async def receive_event_message(self):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke receive_event_message() on a {self.__class__.__name__} that is not active")
        # return catchup event messages first
        if self._catchup_event_messages:
            return self._catchup_event_messages.pop(0)
        # make sure we dont receive a 'catchup' event_message as that could cause application to process duplucates !
        event_message = None
        while (not event_message) or (event_message.seq() < self.next_event_message_seq()):
            event_message = await self._event_subscriber.get()
        # make sure we get the one we expect !
        if event_message.seq() > self.next_event_message_seq():
            raise ServiceBusException(f"Received event_message with seq {event_message.seq()} instead of the expected {self.next_event_message_seq()}")
        self._next_event_message_seq = event_message.seq() + 1
        return event_message

    async def send_command_message(self, command_message: service_bus_messages.CommandMessage):
        raise ServiceBusException(f"Cannot send a command message from {self.__class__.__name__}")

    async def receive_command_receipt_message(self):
        raise ServiceBusException(f"Cannot receive a command_receipt_message in {self.__class__.__name__}")

    def active(self):
        return (self._event_subscriber) and (self._task_runner) and (self._task_runner.active())

    async def start(self):
        task = asyncio.create_task(self.manage_event_subscriber())
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





class MemoryCommandableServiceBusClient(MemoryServiceBusClient):
    def __init__(self, event_message_pub_sub, event_message_cache, command_message_queue, command_receipt_message_queue):
        super().__init__(event_message_pub_sub, event_message_cache)
        self._command_message_queue = command_message_queue
        self._command_receipt_message_queue = command_receipt_message_queue

    async def send_command_message(self, command_message: service_bus_messages.CommandMessage):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke send_command_message() on a {self.__class__.__name__} that is not active")
        await self._command_message_queue.put(command_message)

    async def receive_command_receipt_message(self):
        if not self.active():
            raise ServiceBusException(f"Cannot invoke receive_command_receipt_message() on a {self.__class__.__name__} that is not active")
        return await self._command_receipt_message_queue.get()
