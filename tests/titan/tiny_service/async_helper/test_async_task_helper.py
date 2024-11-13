import asyncio
import pytest
from titan.tiny_service.async_helper import AsyncTaskHelper



async def sleep_and_return(sleep_amount, retval):
    await asyncio.sleep(sleep_amount)
    return retval

async def sleep_and_raise(sleep_amount, exception_msg):
    await asyncio.sleep(sleep_amount)
    raise Exception(exception_msg)

@pytest.mark.asyncio
async def test_exceptions():
    tasks = [
        asyncio.create_task(asyncio.sleep(0.1)),
        asyncio.create_task(sleep_and_raise(0.2, "ANOTHER-EXCEPTION")),
        asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
        asyncio.create_task(sleep_and_return(0.1, 424242))
    ]

    try:
        result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)
        pytest.fail("This should have raised an exception")
    except Exception as e:
        assert str(e) == "FIRST-EXCEPTION"
    finally:
        for t in tasks:
            assert t.done()


@pytest.mark.asyncio
async def test_return():
    tasks = [
        asyncio.create_task(asyncio.sleep(0.1)),
        asyncio.create_task(sleep_and_return(0.2, False)),
        asyncio.create_task(sleep_and_return(0.01, "some-result")),
        asyncio.create_task(sleep_and_return(0.3, 424242))
    ]

    try:
        result = await AsyncTaskHelper.gather_and_cancel_pending(tasks)
    except Exception as e:
        pytest.fail("No exception should have been raised")
    finally:        
        assert result == [None, False, "some-result", 424242]
        for t in tasks:
            assert t.done()


async def gather_to_be_cancelled():
    try:
        tasks = [
            asyncio.create_task(sleep_and_return(0.2, 1)),
            asyncio.create_task(sleep_and_return(6, 2)),
            asyncio.create_task(sleep_and_return(0.3, 3))
        ]
        return await AsyncTaskHelper.gather_and_cancel_pending(tasks)
    finally:
        for t in tasks:
            assert t.done()

@pytest.mark.asyncio
async def test_cancel():
    task = asyncio.create_task(gather_to_be_cancelled())
    await asyncio.sleep(0.1)
    try:
        await AsyncTaskHelper.cancel_and_wait(task)
    except Exception as e:
        pytest.fail(f"Did not expect an exception to be raised when cancelling and waiting the task")


@pytest.mark.asyncio
async def test_wait_for_all_result():
    try:
        tasks = [
            asyncio.create_task(sleep_and_return(0, 1)),
            asyncio.create_task(sleep_and_return(0, 2)),
            asyncio.create_task(sleep_and_return(5, 3))
        ]
        result = await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks)
        assert result==[1,2,3]
    finally:
        for t in tasks:
            assert t.done()



@pytest.mark.asyncio
async def test_wait_for_first_result():
    try:
        tasks = [
            asyncio.create_task(sleep_and_return(0.1, 42)),
            asyncio.create_task(sleep_and_return(0.2, 2)),
            asyncio.create_task(sleep_and_return(5, 3))
        ]
        result = await AsyncTaskHelper.wait_for_first_and_cancel_pending(tasks)
        assert result==42

    finally:
        for t in tasks:
            assert t.done()




@pytest.mark.asyncio
async def test_wait_for_first_with_exception():
    try:
        tasks = [
            asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
            asyncio.create_task(sleep_and_raise(0.15, "SECOND-EXCEPTION")),
            asyncio.create_task(sleep_and_return(5, 3))
        ]
        try:
            await AsyncTaskHelper.wait_for_first_and_cancel_pending(tasks)
            pytest.fail(f"Expected an exception")
        except Exception as e:
            assert str(e) == "FIRST-EXCEPTION"
    finally:
        for t in tasks:
            assert t.done()




@pytest.mark.asyncio
async def test_wait_for_first_timeout():
    try:
        tasks = [
            asyncio.create_task(sleep_and_return(2, 42)),
            asyncio.create_task(sleep_and_return(3, 2)),
            asyncio.create_task(sleep_and_return(5, 3))
        ]            
        result = await AsyncTaskHelper.wait_for_first_and_cancel_pending(tasks, timeout=1)
        pytest.fail(f"Expected a timeout exception")
    except asyncio.TimeoutError:
        pass
    finally:
        for t in tasks:
            assert t.done()



@pytest.mark.asyncio
async def test_wait_for_all_timeout():
    try:
        tasks = [
            asyncio.create_task(sleep_and_return(0, 42)),
            asyncio.create_task(sleep_and_return(0, 2)),
            asyncio.create_task(sleep_and_return(99, 3))
        ]            
        result = await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks, timeout=1)
        pytest.fail(f"Expected a timeout exception")
    except asyncio.TimeoutError:
        pass
    finally:
        for t in tasks:
            assert t.done()




@pytest.mark.asyncio
async def test_wait_for_all_with_exception():
    try:
        tasks = [
            asyncio.create_task(sleep_and_raise(0.1, "FIRST-EXCEPTION")),
            asyncio.create_task(sleep_and_raise(0.15, "SECOND-EXCEPTION")),
            asyncio.create_task(sleep_and_return(5, 3))
        ]
        try:
            await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks)
            pytest.fail(f"Expected an exception")
        except Exception as e:
            assert str(e) == "FIRST-EXCEPTION"
    finally:
        for t in tasks:
            assert t.done()
