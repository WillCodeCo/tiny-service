import asyncio
import pytest
import random
from titan.tiny_service import events
from titan.tiny_service.deprecated import state_machine
from titan.tiny_service.deprecated import EventMonitorMachine
from tests.titan.tiny_service.events.sample_events import (
    DummyStartedEvent,
    DummyNoStateChangeEvent,
    DummyStateXEvent,
    DummyStateYEvent,
    DummyStateZEvent,
    DummyFinishedEvent,
)




async def event_watcher_task(task_id, state_id, event_generator, event_task_log):
    events_seen = []
    async for event in event_generator:
        events_seen.append(event)
    event_task_log.append((task_id, state_id, events_seen))



class DummyEventMonitorMachine(EventMonitorMachine):
    def __init__(self, event_task_log):
        super().__init__(initial_state_id='waiting_state', context=state_machine.StateMachineContext())
        self._next_task_id = 0
        self._event_task_log = event_task_log

    def context_transaction_in_waiting_state(self, next_state_id, context, event):
        return context.DoNothingTransaction()
    def context_transaction_in_started_state(self, next_state_id, context, event):
        return context.DoNothingTransaction()
    def context_transaction_in_finished_state(self, next_state_id, context, event):
        return context.DoNothingTransaction()
    def context_transaction_in_state_x(self, next_state_id, context, event):
        return context.DoNothingTransaction()
    def context_transaction_in_state_y(self, next_state_id, context, event):
        return context.DoNothingTransaction()
    def context_transaction_in_state_z(self, next_state_id, context, event):
        return context.DoNothingTransaction()

    def next_state_from_waiting_state(self, context, event):
        if isinstance(event, (DummyStartedEvent)):
            return "started_state"
        else:
            pytest.fail(f"Event {event.event_type()} not expected in waiting_state")

    def next_state_from_started_state(self, context, event):
        if isinstance(event, (DummyStateXEvent)):
            return "state_x"
        elif isinstance(event, (DummyStateYEvent)):
            return "state_y"
        elif isinstance(event, (DummyStateZEvent)):
            return "state_z"
        elif isinstance(event, (DummyFinishedEvent)):
            return "finished_state"

    def next_state_from_finished_state(self, context, event):
        pytest.fail(f"Event {event.event_type()} not expected in finished_state")

    def next_state_from_state_x(self, context, event):
        if isinstance(event, (DummyStateXEvent)):
            return "state_x"
        elif isinstance(event, (DummyStateYEvent)):
            return "state_y"
        elif isinstance(event, (DummyStateZEvent)):
            return "state_z"
        elif isinstance(event, (DummyFinishedEvent)):
            return "finished_state"

    def next_state_from_state_y(self, context, event):
        if isinstance(event, (DummyStateXEvent)):
            return "state_x"
        elif isinstance(event, (DummyStateYEvent)):
            return "state_y"
        elif isinstance(event, (DummyStateZEvent)):
            return "state_z"
        elif isinstance(event, (DummyFinishedEvent)):
            return "finished_state"

    def next_state_from_state_z(self, context, event):
        if isinstance(event, (DummyStateXEvent)):
            return "state_x"
        elif isinstance(event, (DummyStateYEvent)):
            return "state_y"
        elif isinstance(event, (DummyStateZEvent)):
            return "state_z"
        elif isinstance(event, (DummyFinishedEvent)):
            return "finished_state"

    async def monitor_events_in_waiting_state(self, event_generator):
        task_id = self._next_task_id
        self._next_task_id += 1
        await event_watcher_task(task_id, 'waiting_state', event_generator, self._event_task_log)

    async def monitor_events_in_started_state(self, event_generator):
        task_id = self._next_task_id
        self._next_task_id += 1
        await event_watcher_task(task_id, 'started_state', event_generator, self._event_task_log)

    async def monitor_events_in_finished_state(self, event_generator):
        task_id = self._next_task_id
        self._next_task_id += 1
        await event_watcher_task(task_id, 'finished_state', event_generator, self._event_task_log)

    async def monitor_events_in_state_x(self, event_generator):
        task_id = self._next_task_id
        self._next_task_id += 1
        await event_watcher_task(task_id, 'state_x', event_generator, self._event_task_log)

    async def monitor_events_in_state_y(self, event_generator):
        task_id = self._next_task_id
        self._next_task_id += 1
        await event_watcher_task(task_id, 'state_y', event_generator, self._event_task_log)

    async def monitor_events_in_state_z(self, event_generator):
        task_id = self._next_task_id
        self._next_task_id += 1
        await event_watcher_task(task_id, 'state_z', event_generator, self._event_task_log)





def generate_events(event_count):
    rng = random.Random(42)
    result = [DummyStartedEvent.create()]
    for x in range(event_count-2):
        event_class = rng.choice([DummyNoStateChangeEvent, DummyStateXEvent, DummyStateYEvent, DummyStateZEvent])
        result.append(event_class.create())
    result += [DummyFinishedEvent.create()]
    return result


@pytest.mark.asyncio
async def test_event_monitor_machine():
    rng = random.Random(42)
    input_events = generate_events(event_count=100)
    event_task_log = []
    async with DummyEventMonitorMachine(event_task_log) as dummy_event_monitor_machine:
        for event in input_events:
            await dummy_event_monitor_machine.process_event(event)
            await asyncio.sleep(rng.random()*0.01)
        await asyncio.sleep(0)

    # check to see if log is correct
    events_from_log = [event for entry in event_task_log for event in entry[2]]

    assert events_from_log == input_events

    # check state changing events are at start
    for task_id, state_id, events_seen in event_task_log:
        for counter, event in enumerate(events_seen):
            if isinstance(event, (DummyStartedEvent, DummyFinishedEvent, DummyStateXEvent, DummyStateYEvent, DummyStateZEvent)):
                assert counter == 0

    # check non state changing events are not at start
    for task_id, state_id, events_seen in event_task_log:
        for counter, event in enumerate(events_seen):
            if isinstance(event, (DummyNoStateChangeEvent)):
                assert counter > 0
