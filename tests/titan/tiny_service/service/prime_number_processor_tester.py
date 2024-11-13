from math import sqrt
from itertools import count, islice
import asyncio
import logging
import tempfile
import os
from titan.tiny_service.async_helper import AsyncTaskRunner, AsyncTaskHelper
from titan.tiny_service import commands
from titan.tiny_service import events
from titan.tiny_service.service import (
    UnrecognizedEventException
)
from titan.tiny_service import event_stream
from tests.titan.tiny_service.service import prime_number_processor


logger = logging.getLogger(__name__)

class PrimeNumberProcessorTesterException(Exception):
    pass

class PrimeNumberProcessorTester:
    def __init__(self, service_event_producer, service_command_executor, tester_id, test_count):        
        self._service_event_producer = service_event_producer
        self._service_command_executor = service_command_executor
        self._tester_id = tester_id
        self._test_count = test_count


    @classmethod
    async def expect_successful_command_execution(cls, command_executor, command, timeout):
        task = asyncio.create_task(command_executor.execute_command(command))
        try:
            await AsyncTaskHelper.wait_for_all_and_cancel_pending([task], timeout=timeout)
        except asyncio.TimeoutError:
            raise PrimeNumberProcessorTesterException(f"Timeout when trying to execute command")
        except commands.CommandExecutorException as e:
            raise PrimeNumberProcessorTesterException(f"Did not expect command execution to fail: {e}")


    @classmethod
    async def expect_to_fail_command_execution(cls, command_executor, command, timeout):
        task = asyncio.create_task(command_executor.execute_command(command))
        try:
            await AsyncTaskHelper.wait_for_all_and_cancel_pending([task], timeout=timeout)
            raise PrimeNumberProcessorTesterException(f"Did not expect command execution to succeed.")
        except asyncio.TimeoutError:
            raise PrimeNumberProcessorTesterException(f"Timeout when trying to execute command")
        except commands.CommandExecutorException as e:
            logger.info(f"Command failed as expected with exception: {e}")


    @classmethod
    async def expect_next_events_to_match(cls, event_producer, target_event_types, event_receive_timeout):
        for target_event_type in target_event_types:

            task = asyncio.create_task(event_producer.receive_event())
            try:
                event = (await AsyncTaskHelper.wait_for_all_and_cancel_pending([task], timeout=event_receive_timeout))[0]
                logger.info(f"Received event: {event}")
                if type(event) != target_event_type:
                    raise PrimeNumberProcessorTesterException(f"Expecting an event of type `{target_event_type}` not `{type(event)}`")
            except asyncio.TimeoutError:
                raise PrimeNumberProcessorTesterException(f"Timeout when trying to receive event")
            except events.EventProducerException as e:
                raise PrimeNumberProcessorTesterException(f"Failed to receive event: {e}")



    @classmethod
    async def basic_test(cls, service_client):
        await cls.expect_successful_command_execution(  service_client,
                                                        prime_number_processor.service_interface.ProcessThisPrimeNumberCommand.create(3),
                                                        timeout=5.0 )

        await cls.expect_next_events_to_match(service_client, [ prime_number_processor.service_interface.FoundPrimeSquareEvent ], event_receive_timeout=0.1)


        await cls.expect_to_fail_command_execution( service_client,
                                                    prime_number_processor.service_interface.ProcessThisPrimeNumberCommand.create(10),
                                                    timeout=5.0 )

        await cls.expect_successful_command_execution(  service_client,
                                                        prime_number_processor.service_interface.ProcessThisPrimeNumberCommand.create(13),
                                                        timeout=5.0 )

        await cls.expect_next_events_to_match(service_client, [ prime_number_processor.service_interface.FoundPrimeSquareEvent ], event_receive_timeout=0.1)




    @classmethod
    def is_prime(cls, n):
        return n > 1 and all(n%i for i in islice(count(2), int(sqrt(n)-1)))

    @classmethod
    def prime_square_generator(cls, limit):
        for n in range(limit):
            if cls.is_prime(n):
                yield (n*n)
            n += 1
  

    async def _event_monitor(self):
        all_events = []

        with tempfile.TemporaryDirectory() as working_dir:

            with open(os.path.join(working_dir, 'stream.events'), 'wb') as f:
                event_stream_meta = {'bla': 'blabla'}
                event_stream_file_writer = event_stream.EventStreamFileWriter(f, event_stream_meta)

                for expected_prime_square in self.prime_square_generator(self._test_count):
                    try:
                        event = await self._service_event_producer.receive_event()
                        all_events.append(event)
                        event_stream_file_writer.write_event(event)
                        logger.info(f"[CLIENT {self._tester_id}] received an event: {event}")
                        # check the event type
                        assert isinstance(event, prime_number_processor.service_interface.FoundPrimeSquareEvent), "Unexpected event type"
                        # check event contents
                        #assert event.prime_square() == expected_prime_square, f"Expected prime square {expected_prime_square} but got {event.prime_square()} instead"
                        # otherwise
                        logger.info(f"[CLIENT {self._tester_id}] received a valid prime square: {event.prime_square()}")
                    except UnrecognizedEventException as e:
                        logger.error(f"Received an unrecognized event: {e}")
                        raise
                    except AssertionError as e:
                        logger.error(f"Assertion failed: {e}")
                        raise PrimeNumberProcessorTesterException(f"Assertion failure: {e.args[0]}")
                    except asyncio.CancelledError as e:
                        logger.info(f"Closing down the PrimeNumberProcessorTester._event_monitor()")
                        raise
                    except Exception as e:
                        logger.error(f"Unexpected exception `{type(e)}` when receiving an event from client: {e}")
                        raise

            with open(os.path.join(working_dir, 'stream.events'), 'rb') as f:
                event_stream_file_reader = prime_number_processor.EventStreamFileReader(f)
                assert list(event_stream_file_reader.events()) == all_events

            

    async def _command_executor(self):
        try:
            for some_number in range(self._test_count):
                try:
                    logger.info(f"[CLIENT {self._tester_id}] Executing command for {some_number}")
                    await self._service_command_executor.execute_command(prime_number_processor.service_interface.ProcessThisPrimeNumberCommand.create(some_number))
                    logger.info(f"[CLIENT {self._tester_id}] successfully executed command for {some_number}")
                    # we should have raised an exception if some_number was not prime
                    assert self.is_prime(some_number), f"Expected a CommandExecutorException because {some_number} is not a prime"
                    # sleep a bit
                    await asyncio.sleep(0.01)
                except commands.CommandExecutorException as e:
                    assert (not self.is_prime(some_number)), f"Unexpected CommandExecutorException exception for prime number {some_number}"
                    logger.info(f"[CLIENT {self._tester_id}] received expected command rejection for {some_number}")
        except AssertionError as e:
            logger.error(f"Assertion failed: {e}")
            raise PrimeNumberProcessorTesterException(f"Assertion failure: {e.args[0]}")



    async def wait_closed(self):
        if self._task_runner:
            await self._task_runner.wait_closed()

    async def close(self):
        if self._task_runner:
            await self._task_runner.close()

    async def start(self):
        tasks = [
            asyncio.create_task(self._command_executor()),
            asyncio.create_task(self._event_monitor()),
        ]
        self._task_runner = AsyncTaskRunner(tasks)
        await self._task_runner.start()

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
            logger.info(f"{self.__class__.__name__} is suppressing exception with type `{type(e)}` : {e}")
