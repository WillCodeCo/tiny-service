import asyncio
import logging
import pytest
from titan.tiny_service.async_helper import AsyncTaskHelper, AsyncTaskHelper, AsyncQueue, AsyncPeekableQueue, AsyncSharedQueue

logger = logging.getLogger(__name__)



async def sleep_then_put_item_in_queue(async_queue, delay, value):
    await asyncio.sleep(delay)
    await async_queue.put(value)

async def sleep_then_consume_until_item_from_queue(async_queue, delay, num_items):
    await asyncio.sleep(delay)
    result = []
    for _ in range(num_items):
        result.append(await async_queue.get())
    return result

async def sleep_then_cancel_queue(async_queue, delay):
    await asyncio.sleep(delay)
    async_queue.cancel()

async def sleep_then_set_exception_on_queue(async_queue, delay, exception):
    await asyncio.sleep(delay)
    async_queue.set_exception(exception)


async def sleep_then_peek_item_on_queue(peekable_queue, delay):
    await asyncio.sleep(delay)
    return (await peekable_queue.peek())


async def sleep_then_pop_item_from_queue(peekable_queue, delay):
    await asyncio.sleep(delay)
    return peekable_queue.pop()




@pytest.mark.asyncio
async def test_async_queue():
    async_queue = AsyncQueue()
    tasks = [
        asyncio.create_task(sleep_then_put_item_in_queue(async_queue, 0, "item_0")),
        asyncio.create_task(sleep_then_put_item_in_queue(async_queue, 0.02, "item_1")),
        asyncio.create_task(sleep_then_put_item_in_queue(async_queue, 0.1, "item_2")),
        asyncio.create_task(sleep_then_consume_until_item_from_queue(async_queue, 0.05, 3)),
    ]
    result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)
    assert result[3] == ["item_0", "item_1", "item_2"]



@pytest.mark.asyncio
async def test_cancel_async_queue():
    async_queue = AsyncQueue()
    tasks = [
        asyncio.create_task(sleep_then_put_item_in_queue(async_queue, 0, "item_0")),
        asyncio.create_task(sleep_then_put_item_in_queue(async_queue, 0.02, "item_1")),
        asyncio.create_task(sleep_then_put_item_in_queue(async_queue, 0.1, "item_2")),
        asyncio.create_task(sleep_then_consume_until_item_from_queue(async_queue, 0.05, 4)),
        asyncio.create_task(sleep_then_cancel_queue(async_queue, 0.04))
    ]
    try:
        result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)
        pytest.fail("We should have got a CancelledError")
    except asyncio.CancelledError:
        pass



@pytest.mark.asyncio
async def test_cancelled_producer():
    async def _consume_until_item(async_queue, last_item, delay):
        result = []
        while (not result) or (result[-1] != last_item):
            await asyncio.sleep(delay)
            result.append(await async_queue.get())
            logger.info(f"Consumer got item: {result[-1]}")
        return result


    async def _produce_items(async_queue, items):
        items = list(items)
        while items:
            await async_queue.put(items.pop(0))

    async_queue = AsyncQueue()
    consumer_task = asyncio.create_task(_consume_until_item(async_queue, "FINISH", delay=1))
    producer_1_task = asyncio.create_task(_produce_items(async_queue, [ "producer_1: 0",
                                                                        "producer_1: 1",
                                                                        "producer_1: 2",
                                                                        "producer_1: 3",
                                                                        "producer_1: 4",
                                                                        "producer_1: 5" ]))
    try:
        await AsyncTaskHelper.wait_for_first_and_cancel_pending([producer_1_task], timeout=2)
    except asyncio.TimeoutError:
        pass
    producer_2_task = asyncio.create_task(_produce_items(async_queue, [ "producer_2: 0",
                                                                        "producer_2: 1",
                                                                        "producer_2: 2",
                                                                        "FINISH"  ]))
    try:
        tasks = [
            consumer_task,
            producer_2_task
        ]
        result = await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks)
        assert consumer_task.result() == [  "producer_1: 0",
                                            "producer_1: 1",
                                            "producer_2: 0",
                                            "producer_2: 1",
                                            "producer_2: 2",
                                            "FINISH"  ]
    finally:
        for t in tasks:
            assert t.done()






@pytest.mark.asyncio
async def test_peekable_queue_can_peek():
    peekable_queue = AsyncPeekableQueue()
    tasks = [
        asyncio.create_task(sleep_then_put_item_in_queue(peekable_queue, 0.00, "item_0")),
        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.00)),
        asyncio.create_task(sleep_then_put_item_in_queue(peekable_queue, 0.05, "item_1")),
        asyncio.create_task(sleep_then_put_item_in_queue(peekable_queue, 0.10, "item_2")),

        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.10)),        
        asyncio.create_task(sleep_then_pop_item_from_queue(peekable_queue, 0.15)),

        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.20)),
        asyncio.create_task(sleep_then_pop_item_from_queue(peekable_queue, 0.25)),

        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.30)),
        asyncio.create_task(sleep_then_pop_item_from_queue(peekable_queue, 0.35)),
        
    ]
    result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)
    assert result[1] == "item_0"
    assert result[4] == "item_0"
    assert result[5] == "item_0"
    assert result[6] == "item_1"
    assert result[7] == "item_1"
    assert result[8] == "item_2"
    assert result[9] == "item_2"




@pytest.mark.asyncio
async def test_peekable_queue_exception():
    peekable_queue = AsyncPeekableQueue()
    tasks = [
        asyncio.create_task(sleep_then_put_item_in_queue(peekable_queue, 0.00, "item_0")),
        asyncio.create_task(sleep_then_put_item_in_queue(peekable_queue, 0.05, "item_1")),
        asyncio.create_task(sleep_then_put_item_in_queue(peekable_queue, 0.10, "item_2")),

        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.10)),        
        asyncio.create_task(sleep_then_pop_item_from_queue(peekable_queue, 0.15)),

        asyncio.create_task(sleep_then_set_exception_on_queue(peekable_queue, 0.20, Exception("dummy-exception"))),
        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.25)), 
    ]

    try:
        result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)
        pytest.fail("We should have got a dummy-exception")
    except Exception as e:
        assert str(e) == "dummy-exception"



@pytest.mark.asyncio
async def test_peekable_queue_cancel_race():
    peekable_queue = AsyncPeekableQueue()
    tasks = [
        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.10)),
        asyncio.create_task(sleep_then_put_item_in_queue(peekable_queue, 0.15, "item_0")),
        asyncio.create_task(sleep_then_cancel_queue(peekable_queue, 0.25)),
        asyncio.create_task(sleep_then_peek_item_on_queue(peekable_queue, 0.35)),
    ]

    try:
        result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)
        pytest.fail("We were expecting to have got a asyncio.CancelledError")
    except asyncio.CancelledError as e:
        pass

@pytest.mark.asyncio
async def test_shared_queue():
    async def item_produce(queue, items):
        for item in items:
            await asyncio.sleep(0.005)
            await queue.put(item)
            print(f"Produced {item}")

    async def item_consume_until_item(consumer_index, queue, num_items):
        result = []
        for _ in range(num_items):
            await asyncio.sleep(consumer_index*0.003)
            item = await queue.get(consumer_index)
            result.append(item)
            print(f"[Consumer {consumer_index}] consumed {item}")
        return result

    source_queue = AsyncQueue()
    shared_queue = AsyncSharedQueue(source_queue, 5)
    items_to_produce = [f"item: {x}" for x in range(100)]
    tasks = [
        asyncio.create_task(item_produce(source_queue, items_to_produce)),
        asyncio.create_task(item_consume_until_item(0, shared_queue, len(items_to_produce))),
        asyncio.create_task(item_consume_until_item(1, shared_queue, len(items_to_produce))),
        asyncio.create_task(item_consume_until_item(2, shared_queue, len(items_to_produce))),
        asyncio.create_task(item_consume_until_item(3, shared_queue, len(items_to_produce))),
        asyncio.create_task(item_consume_until_item(4, shared_queue, len(items_to_produce))),
    ]
    result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)

    assert result[1] == items_to_produce
    assert result[2] == items_to_produce
    assert result[3] == items_to_produce
    assert result[4] == items_to_produce
    assert result[5] == items_to_produce



@pytest.mark.asyncio
async def test_shared_queue_cancel_consume_until_item():
    async def item_produce(queue, items):
        produced_items = []
        for item in items:
            await asyncio.sleep(0.005)
            await queue.put(item)
            produced_items.append(item)
            print(f"Produced {item}")
        return produced_items

    async def item_consume_until_item(consumer_index, queue, num_items):
        result = []
        for _ in range(num_items):
            await asyncio.sleep(consumer_index*0.003)
            item = await queue.get(consumer_index)
            result.append(item)
            print(f"[Consumer {consumer_index}] consumed {item}")
        return result


    async def cancelling_consume_until_item(consumer_index, queue, num_items, sleep_before_cancel):
        try:
            task = asyncio.create_task(item_consume_until_item(consumer_index, queue, num_items))
            await asyncio.sleep(sleep_before_cancel)
            await AsyncTaskHelper.cancel_and_wait(task)
        finally:
            if task.cancelled():
                print(f"[Consumer {consumer_index}] has been cancelled")


    source_queue = AsyncQueue()
    shared_queue = AsyncSharedQueue(source_queue, 2)
    items_to_produce = [f"item: {x}" for x in range(100)]
    tasks = [
        asyncio.create_task(item_produce(source_queue, items_to_produce)),
        asyncio.create_task(cancelling_consume_until_item(0, shared_queue, len(items_to_produce), 0.1)),
        asyncio.create_task(item_consume_until_item(1, shared_queue, len(items_to_produce))),
    ]
    result = await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks, timeout=5)
    assert result[0] == items_to_produce
    assert result[2] == items_to_produce

