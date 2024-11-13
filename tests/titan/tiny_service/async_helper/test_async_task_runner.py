import asyncio
import pytest
from titan.tiny_service.async_helper import AsyncTaskRunner, AsyncDynamicTaskRunner



async def sleep_and_return(sleep_amount, retval):
    await asyncio.sleep(sleep_amount)
    return retval

async def sleep_and_raise(sleep_amount, exception_msg):
    await asyncio.sleep(sleep_amount)
    raise Exception(exception_msg)

async def sleep_and_return_from_queue(sleep_amount, queue):
    await asyncio.sleep(sleep_amount)
    return (await queue.get())




@pytest.mark.asyncio
async def test_task_runner_with_exceptions():
    tasks = [
        asyncio.create_task(asyncio.sleep(0.1)),
        asyncio.create_task(sleep_and_raise(0.2, "ANOTHER-EXCEPTION")),
        asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
        asyncio.create_task(sleep_and_return(0.1, 424242))
    ]
    task_runner = AsyncTaskRunner(tasks)
    try:
        await task_runner.start()
        await task_runner.wait_closed()
        pytest.fail(f"Expected an exception to have been raised")
    except Exception as e:
        assert str(e) == "FIRST-EXCEPTION"

    for t in tasks:
        assert t.done()



@pytest.mark.asyncio
async def test_task_runner_cancels():
    tasks = [
        asyncio.create_task(sleep_and_return(999, 424242)),
        asyncio.create_task(sleep_and_return(99, 424242)),
        asyncio.create_task(sleep_and_return(99, 424242))
    ]
    task_runner = AsyncTaskRunner(tasks)
    await task_runner.start()
    await asyncio.sleep(0.2)
    await task_runner.close()
    for t in tasks:
        assert t.done()



@pytest.mark.asyncio
async def test_task_runner_with_context_manager_simple_exception():
    tasks = [
        asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
        asyncio.create_task(sleep_and_return(0.5, 424242))
    ]
    try:
        async with AsyncTaskRunner(tasks) as task_runner:
            try:
                await task_runner.wait_closed()
            except asyncio.CancelledError:
                pytest.fail(f"Expected the real exception not CancelledError")
            except Exception as e:
                assert str(e) == "FIRST-EXCEPTION"
                raise
    except Exception as e:
        assert str(e) == "FIRST-EXCEPTION"
    # there should be no tasks left alive
    for t in tasks:
        assert t.done()


@pytest.mark.asyncio
async def test_task_runner_with_context_manager_exceptions():
    tasks = [
        asyncio.create_task(asyncio.sleep(0.1)),
        asyncio.create_task(sleep_and_raise(0.2, "ANOTHER-EXCEPTION")),
        asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
        asyncio.create_task(sleep_and_return(0.1, 424242))
    ]
    try:
        async with AsyncTaskRunner(tasks) as task_runner:
            await task_runner.wait_closed()
        pytest.fail(f"Expected an exception to have been raised")
    except Exception as e:
        assert str(e) == "FIRST-EXCEPTION"
    # there should be no tasks left alive
    for t in tasks:
        assert t.done()


@pytest.mark.asyncio
async def test_task_runner_context_manager_cancels():
    tasks = [
        asyncio.create_task(sleep_and_return(999, 424242)),
        asyncio.create_task(sleep_and_return(99, 424242)),
        asyncio.create_task(sleep_and_return(99, 424242))
    ]
    async with AsyncTaskRunner(tasks) as task_runner:
        await asyncio.sleep(0.2)
    for t in tasks:
        assert t.done()



@pytest.mark.asyncio
async def test_task_runner_with_context_manager_both_exceptions():
    tasks = [
        asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
        asyncio.create_task(sleep_and_raise(0.1, "SECOND-EXCEPTION")),
    ]
    try:
        async with AsyncTaskRunner(tasks) as task_runner:
            await task_runner.wait_closed()
        pytest.fail(f"Expected an exception to have been raised")
    except BaseException as e:
        assert str(e) in ["FIRST-EXCEPTION", "SECOND-EXCEPTION"]
    finally:
        # there should be no tasks left alive
        for t in tasks:
            assert t.done()


@pytest.mark.asyncio
async def test_task_runner_with_context_manager_nested_cancel():
    async def run_child_tasks(tasks):
        async with AsyncTaskRunner(tasks) as task_runner:
            await task_runner.wait_closed()
    child_tasks = [
        asyncio.create_task(sleep_and_return(99, 42)),
        asyncio.create_task(sleep_and_return(99, 4242)),
        asyncio.create_task(sleep_and_return(99, 4242)),
    ]
    parent_task = asyncio.create_task(run_child_tasks(child_tasks))
    # run
    async with AsyncTaskRunner([parent_task]) as parent_task_runner:
        await parent_task_runner.close()
    # check all child tasks are dead
    for t in child_tasks:
        if not t.done():
            pytest.fail("All child tasks should be finished.")





@pytest.mark.asyncio
async def test_task_runner_deep_nested_stopping():
    task_a = asyncio.create_task(sleep_and_return(9999, 42))
    task_b = asyncio.create_task(sleep_and_return(9999, 42))
    task_c = asyncio.create_task(sleep_and_return(1, 42))
    try:
        async with AsyncTaskRunner([task_a]) as task_runner_a:
            async with AsyncTaskRunner([task_b]) as task_runner_b:
                async with AsyncTaskRunner([task_c]) as task_runner_c:
                    await task_runner_c.wait_closed()

    except Exception as e:
        pytest.fail(f"Did not expect an exception `{type(e)}` : {e}")
    finally:
        # check all child tasks are dead
        for t in [task_a, task_b, task_c]:
            if not t.done():
                pytest.fail("All child tasks should be finished.")


@pytest.mark.asyncio
async def test_task_runner_cancel_waiter_does_not_cancel_tasks():
    tasks = [
        asyncio.create_task(sleep_and_return(99, 42)),
        asyncio.create_task(sleep_and_return(99, 4242)),
        asyncio.create_task(sleep_and_return(99, 4242)),
    ]
    task_runner = AsyncTaskRunner(tasks)
    await task_runner.start()
    try:
        await asyncio.wait_for(task_runner.wait_closed(), timeout=1)
        pytest.fail("We should have got a timeout exception")
    except asyncio.TimeoutError:
        pass

    assert task_runner._completion_future.done() == False

    for t in tasks:
        assert (not t.cancelled())
    await task_runner.close()
    for t in tasks:
        assert t.done()



@pytest.mark.asyncio
async def test_dynamic_task_runner_force_closes_tasks():
    some_empty_queue = asyncio.Queue()
    tasks = [
        asyncio.create_task(sleep_and_return(0.3, 4242)),
        asyncio.create_task(sleep_and_return(0.1, 424242)),
        asyncio.create_task(sleep_and_return_from_queue(0, some_empty_queue)),
    ]
    task_runner = AsyncDynamicTaskRunner()
    await task_runner.start()
    for task in tasks:
        task_runner.add_task(task)
    await asyncio.sleep(0.1)
    try:
        await task_runner.close()
    except:
        pass
    for t in tasks:
        assert t.done()


@pytest.mark.asyncio
async def test_dynamic_task_runner_with_exceptions():
    tasks = [
        asyncio.create_task(asyncio.sleep(0.1)),
        asyncio.create_task(sleep_and_raise(0.2, "ANOTHER-EXCEPTION")),
        asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
        asyncio.create_task(sleep_and_return(0.1, 424242))
    ]
    task_runner = AsyncDynamicTaskRunner()
    await task_runner.start()
    for task in tasks:
        task_runner.add_task(task)
    await asyncio.sleep(0.1)
    try:
        await task_runner.close()
        pytest.fail(f"Expected an exception to have been raised")
    except Exception as e:
        assert str(e) in ["FIRST-EXCEPTION", "ANOTHER-EXCEPTION"]

    for t in tasks:
        assert t.done()





@pytest.mark.asyncio
async def test_dynamic_task_runner_cancel_waiter_does_not_cancel_tasks():
    tasks = [
        asyncio.create_task(sleep_and_return(99, 42)),
        asyncio.create_task(sleep_and_return(99, 4242)),
        asyncio.create_task(sleep_and_return(99, 4242)),
    ]
    task_runner = AsyncDynamicTaskRunner()
    await task_runner.start()
    for task in tasks:
        task_runner.add_task(task)

    try:
        await asyncio.wait_for(task_runner.wait_closed(), timeout=1)
        pytest.fail("We should have got a timeout exception")
    except asyncio.TimeoutError:
        pass
    for t in tasks:
        assert (not t.cancelled())
    await task_runner.close()
    for t in tasks:
        assert t.done()
