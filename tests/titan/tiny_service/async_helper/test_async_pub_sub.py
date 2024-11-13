import asyncio
import pytest
from titan.tiny_service.async_helper import AsyncTaskHelper, AsyncPubSub


async def item_producer(pub_sub, items, period, result):
    for item in items:
        await asyncio.sleep(period)
        await pub_sub.publish(item)
        result.append(item)
        print(f"Produced {item}")

async def item_subscriber(subscriber, subscriber_index, num_items, result):
    try:
        for _ in range(num_items):
            item = await subscriber.get()
            result.append(item)
            print(f"[Subscriber {subscriber_index}] consumed {item}")
    except asyncio.CancelledError:
        print(f"[Subscriber {subscriber_index}] was cancelled")

async def cancelling_subscriber(subscriber, subscriber_index, num_items, sleep_before_cancel, result):
    task = asyncio.create_task(item_subscriber(subscriber, subscriber_index, num_items, result))
    await asyncio.sleep(sleep_before_cancel)
    await AsyncTaskHelper.cancel_and_wait(task)


async def subscribe_collect_unsubscribe(pub_sub, subscriber_index, num_items, sleep_before_subscribe, sleep_before_unsubscribe, result):
    await asyncio.sleep(sleep_before_subscribe)
    subscriber = pub_sub.create_subscriber()
    task = asyncio.create_task(item_subscriber(subscriber, subscriber_index, num_items, result))
    await asyncio.sleep(sleep_before_unsubscribe)
    pub_sub.unsubscribe(subscriber)
    return await task


@pytest.mark.asyncio
async def test_async_pub_sub():
    PERIOD = 0.005
    items_to_produce = [f"item: {x}" for x in range(100)]
    pub_sub = AsyncPubSub()
    subscriber_0 = pub_sub.create_subscriber()
    subscriber_1 = pub_sub.create_subscriber()
    subscriber_2 = pub_sub.create_subscriber()
    subscriber_3 = pub_sub.create_subscriber()
    subscriber_4 = pub_sub.create_subscriber()
    results = [[],[],[],[],[],[]]
    tasks = [
        asyncio.create_task(item_producer(pub_sub, items_to_produce, PERIOD, results[0])),
        asyncio.create_task(item_subscriber(subscriber_0, 0, len(items_to_produce), results[1])),
        asyncio.create_task(item_subscriber(subscriber_1, 1, len(items_to_produce), results[2])),
        asyncio.create_task(item_subscriber(subscriber_2, 2, len(items_to_produce), results[3])),
        asyncio.create_task(item_subscriber(subscriber_3, 3, len(items_to_produce), results[4])),
        asyncio.create_task(item_subscriber(subscriber_4, 4, len(items_to_produce), results[5])),
    ]
    result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)

    assert results[0] == items_to_produce
    assert results[1] == items_to_produce
    assert results[2] == items_to_produce
    assert results[3] == items_to_produce
    assert results[4] == items_to_produce
    assert results[5] == items_to_produce



@pytest.mark.asyncio
async def test_async_pub_sub_cancelling():
    PERIOD = 0.05
    items_to_produce = [f"item: {x}" for x in range(50)]
    pub_sub = AsyncPubSub()
    subscriber_0 = pub_sub.create_subscriber()
    subscriber_1 = pub_sub.create_subscriber()
    subscriber_2 = pub_sub.create_subscriber()
    subscriber_3 = pub_sub.create_subscriber()
    subscriber_4 = pub_sub.create_subscriber()
    results = [[],[],[],[],[],[]]
    tasks = [
        asyncio.create_task(item_producer(pub_sub, items_to_produce, PERIOD, results[0])),
        asyncio.create_task(item_subscriber(subscriber_0, 0, len(items_to_produce), results[1])),
        asyncio.create_task(item_subscriber(subscriber_1, 1, len(items_to_produce), results[2])),
        asyncio.create_task(cancelling_subscriber(subscriber_2, 2, len(items_to_produce), PERIOD*20 + PERIOD/2, results[3])),
        asyncio.create_task(item_subscriber(subscriber_3, 3, len(items_to_produce), results[4])),
        asyncio.create_task(item_subscriber(subscriber_4, 4, len(items_to_produce), results[5])),
    ]
    result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)

    assert results[0] == items_to_produce
    assert results[1] == items_to_produce
    assert results[2] == items_to_produce
    assert results[3] == items_to_produce[:20]
    assert results[4] == items_to_produce
    assert results[5] == items_to_produce


@pytest.mark.asyncio
async def test_async_pub_sub_change_subscriptions():
    PERIOD = 0.05
    items_to_produce = [f"item: {x}" for x in range(50)]
    pub_sub = AsyncPubSub()
    subscriber_2 = pub_sub.create_subscriber()
    subscriber_3 = pub_sub.create_subscriber()
    subscriber_4 = pub_sub.create_subscriber()
    results = [[],[],[],[],[],[]]
    tasks = [
        asyncio.create_task(item_producer(pub_sub, items_to_produce, PERIOD, results[0])),
        asyncio.create_task(subscribe_collect_unsubscribe(pub_sub, 0, len(items_to_produce), PERIOD*0, PERIOD*10 + PERIOD/2, results[1])),
        asyncio.create_task(subscribe_collect_unsubscribe(pub_sub, 1, len(items_to_produce), PERIOD*5 + PERIOD/2, PERIOD*10 + PERIOD/2, results[2])),
        asyncio.create_task(item_subscriber(subscriber_2, 2, len(items_to_produce), results[3])),
        asyncio.create_task(item_subscriber(subscriber_3, 3, len(items_to_produce), results[4])),
        asyncio.create_task(item_subscriber(subscriber_4, 4, len(items_to_produce), results[5])),
    ]
    result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)

    assert results[0] == items_to_produce
    assert results[1] == items_to_produce[:10]
    assert results[2] == items_to_produce[5:15]
    assert results[3] == items_to_produce
    assert results[4] == items_to_produce
    assert results[5] == items_to_produce

