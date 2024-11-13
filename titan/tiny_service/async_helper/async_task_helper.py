import asyncio

class AsyncTaskHelper:
    """
    A class with a selection of helper methods for managing async tasks.
    """

    @staticmethod
    async def wait_for_task_or_cancellation(task):       
        try:
            await task
        except asyncio.CancelledError:
            pass

    @staticmethod
    async def cancel_and_wait(task):
        if not task.done():
            task.cancel()
        await AsyncTaskHelper.wait_for_task_or_cancellation(task)


    @staticmethod
    async def cancel_all_and_ignore_exceptions(tasks):
        for t in tasks:
            try:
                await AsyncTaskHelper.cancel_and_wait(t)
            except:
                pass

    @staticmethod
    async def cancel_all_and_raise_first_exception(tasks):
        exceptions = []
        for t in tasks:
            try:
                await AsyncTaskHelper.cancel_and_wait(t)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                exceptions.append(e)
        if exceptions:
            raise exceptions[0]

    @staticmethod
    async def gather_and_cancel_pending(tasks):
        try:
            return await asyncio.gather(*tasks)
        finally:
            await AsyncTaskHelper.cancel_all_and_ignore_exceptions(tasks)

    @staticmethod
    async def wait_for_all_and_cancel_pending(tasks, timeout=None):
        try:
            done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.ALL_COMPLETED)
            # did we time-out ?
            if timeout and pending:
                raise asyncio.TimeoutError(f"Timeout after {timeout} seconds in AsyncTaskHelper.wait_for_all_and_cancel_pending()")
            # retrieve exceptions
            exceptions = [t.exception() for t in tasks if (t.done() and t.exception())]
            if exceptions:
                raise exceptions[0]
            else:
                return [t.result() for t in tasks if t.done()]
        finally:
            await AsyncTaskHelper.cancel_all_and_ignore_exceptions(tasks)

    @staticmethod
    async def wait_for_first_and_cancel_pending(tasks, timeout=None):
        try:
            done, pending = await asyncio.wait(tasks, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
            # did we time-out ?
            if timeout and (not done):
                raise asyncio.TimeoutError(f"Timeout after {timeout} seconds in AsyncTaskHelper.wait_for_first_and_cancel_pending()")
            # retrieve exceptions
            exceptions = [t.exception() for t in tasks if (t.done() and t.exception())]
            if exceptions:
                raise exceptions[0]
            else:
                return [t.result() for t in tasks if t.done()][0]
        finally:
            await AsyncTaskHelper.cancel_all_and_ignore_exceptions(tasks)


