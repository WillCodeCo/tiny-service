import asyncio
import logging
from titan.tiny_service.async_helper.async_task_helper import AsyncTaskHelper

logger = logging.getLogger(__name__)


class AsyncTaskRunner:
    """
    Context manager for managing asynchronous tasks and ensuring they are cleaned up properly.
    """

    def __init__(self, tasks):
        if not tasks:
            raise asyncio.InvalidStateError("Cannot construct AsyncTaskRunner without tasks")
        self._child_tasks = tasks
        self._waiting_task = None
        self._completion_future = None

    @staticmethod
    async def wait_for_tasks_and_set_future(tasks, completion_future):
        wait_task = asyncio.create_task(AsyncTaskHelper.wait_for_first_and_cancel_pending(tasks))
        try:
            await asyncio.shield(wait_task)
            completion_future.set_result(True)
        except asyncio.CancelledError:
            await AsyncTaskHelper.cancel_all_and_ignore_exceptions(tasks+[wait_task])
            completion_future.cancel()
            raise
        except Exception as e:
            completion_future.set_exception(e)

    def cancelled(self):
        if (not self._completion_future):
            raise asyncio.InvalidStateError("Cannot invoke cancelled() on a AsyncTaskRunner that has not been started")
        return all([t.cancelled() for t in self._child_tasks])

    def done(self):
        if (not self._completion_future):
            raise asyncio.InvalidStateError("Cannot invoke done() on a AsyncTaskRunner that has not been started")
        return all([t.done() for t in self._child_tasks])

    def active(self):
        return (self._completion_future) and (not self.done())

    async def start(self):
        self._completion_future = asyncio.get_running_loop().create_future()
        self._waiting_task = asyncio.create_task(AsyncTaskRunner.wait_for_tasks_and_set_future(self._child_tasks, self._completion_future))

    async def wait_closed(self):
        """
        Wait for tasks to finish
        """
        if (not self._completion_future):
            raise asyncio.InvalidStateError("Cannot invoke wait_closed() on a AsyncTaskRunner that has not been started")
        await asyncio.shield(self._completion_future)

    async def close(self):
        """
        Cancel and wait for all tasks to finish
        """
        if (not self._completion_future):
            raise asyncio.InvalidStateError("Cannot invoke close() on a AsyncTaskRunner that has not been started")
        try:
            await asyncio.shield(AsyncTaskHelper.cancel_all_and_ignore_exceptions([self._waiting_task]))
        except asyncio.CancelledError:
            await AsyncTaskHelper.cancel_all_and_ignore_exceptions([self._waiting_task])
            raise
        finally:
            try:
                await self._completion_future
            except:
                pass

    async def run(self):
        await self.start()
        await self.wait_closed()

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
            logger.info(f"AsyncTaskRunner is suppressing exception with type `{type(e)}` : {e}")


class AsyncDynamicTaskRunner:
    """
    Context manager for managing dynamic asynchronous tasks and ensuring they are cleaned up properly.

    While the TaskRunner is not closed, tasks can be added using the `add_task(task)` method.
    """

    def __init__(self):        
        self._is_closed_future = None
        self._tasks = []

    def closed(self):
        if (not self._is_closed_future):
            raise asyncio.InvalidStateError("Cannot invoke closed() on a AsyncDynamicTaskRunner that has not been started")
        return self._is_closed_future.done()

    def active(self):
        return (self._is_closed_future) and (not self.closed())

    def add_task(self, task):
        if self.closed():
            raise asyncio.InvalidStateError("Cannot invoke add_task() on a AsyncDynamicTaskRunner that has been closed")
        self._tasks.append(task)

    async def start(self):
        self._is_closed_future = asyncio.get_running_loop().create_future()

    async def wait_closed(self):
        if (not self._is_closed_future):
            raise asyncio.InvalidStateError("Cannot invoke wait_closed() on a AsyncDynamicTaskRunner that has not been started")
        elif not self.closed():
            await asyncio.shield(self._is_closed_future)

    async def close(self):
        """
        Cancel and wait for all tasks to finish
        """
        if (not self._is_closed_future):
            raise asyncio.InvalidStateError("Cannot invoke close() on a AsyncDynamicTaskRunner that has not been started")
        if (not self.closed()):
            try:
                await asyncio.shield(AsyncTaskHelper.cancel_all_and_raise_first_exception(self._tasks))
            except asyncio.CancelledError:
                await AsyncTaskHelper.cancel_all_and_ignore_exceptions(self._tasks)
                raise
            finally:
                self._is_closed_future.set_result(True)

    async def run(self):
        await self.start()
        await self.wait_closed()

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
            logger.info(f"AsyncDynamicTaskRunner is suppressing exception with type `{type(e)}` : {e}")