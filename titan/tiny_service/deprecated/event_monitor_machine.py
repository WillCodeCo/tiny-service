import asyncio
import logging
from titan.tiny_service.events import Event
from titan.tiny_service.deprecated.state_machine import StateMachine
from titan.tiny_service.async_helper import AsyncTaskRunner, AsyncPeekableQueue
from titan.tiny_service.events.event_processor import AsyncEventProcessor

logger = logging.getLogger(__name__)

class EventMonitorMachineException(Exception):
    pass



class EventMonitorMachine(AsyncEventProcessor):
    def __init__(self, initial_state_id, context):
        self._state_machine = StateMachine(initial_state_id)
        self._context = context
        self._task_runner = None
        self._event_state_queue = None

    def state_machine(self):
        return self._state_machine

    def context(self):
        return self._context

    @staticmethod
    async def _event_in_state_generator(current_state, event_state_queue):
        while True:
            try:
                # peek at next item
                (next_state, event) = await event_state_queue.peek()
                if next_state == current_state:
                    event_state_queue.pop()
                    yield event
                else:
                    break
            except asyncio.CancelledError:
                break

    @staticmethod
    async def _state_generator(event_state_queue):
        last_state = None
        while True:
            try:
                # peek at next item
                (current_state, event) = await event_state_queue.peek()
                if current_state != last_state:
                    last_state = current_state
                    yield current_state
            except asyncio.CancelledError:
                break

    async def _event_monitor(self):
        async for current_state in EventMonitorMachine._state_generator(self._event_state_queue):
            event_generator = EventMonitorMachine._event_in_state_generator(current_state, self._event_state_queue)
            event_monitor_fn = getattr(self, f"monitor_events_in_{self._state_machine.current_state_id()}")
            await event_monitor_fn(event_generator)

    async def process_event(self, event: Event):
        if (not self.active()):
            raise EventMonitorMachineException("EventMonitorMachine.process_event() cannot be called when EventMonitorMachine is not active")
        next_state_id = getattr(self, f"next_state_from_{self._state_machine.current_state_id()}")(self.context(), event)
        context_transaction = getattr(self, f"context_transaction_in_{self._state_machine.current_state_id()}")(next_state_id, self.context(), event)
        if next_state_id:
            self.state_machine().enter(next_state_id, event)
        context_transaction.apply(self.context(), **context_transaction.params())
        await self._event_state_queue.put((self._state_machine.current_state(), event))

    def can_process_event(self, event):
        try:
            next_state_id = getattr(self, f"next_state_from_{self._state_machine.current_state_id()}")(self.context(), event)
            context_transaction = getattr(self, f"context_transaction_in_{self._state_machine.current_state_id()}")(next_state_id, self.context(), event)
            output = getattr(self, f"output_from_{self._state_machine.current_state_id()}")(next_state_id, self.context(), context_transaction, event)
            context_transaction.ensure_can_apply(self.context(), **context_transaction.params())
        except Exception as e:
            raise EventMonitorMachineException(f"Cannot process event `{event}` in state `{self._state_machine.current_state_id()}`: {e}")


    def active(self):
        return (self._task_runner) and (self._task_runner.active())

    async def start(self):
        self._event_state_queue = AsyncPeekableQueue()
        self._task_runner = AsyncTaskRunner([asyncio.create_task(self._event_monitor())])
        await self._task_runner.start()

    async def run(self):
        await self.start()
        await self.wait_closed()

    async def wait_closed(self):
        if self._task_runner:
            await self._task_runner.wait_closed()

    async def close(self):
        if self.active():
            self._event_state_queue.cancel()
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



