import time
import asyncio
import pytest
import logging
import random
from titan.tiny_service.async_helper import AsyncTaskRunner
from titan.tiny_service.service.service_bus import (
    ServiceBusException
)
from titan.tiny_service.service.service_bus import service_bus_messages
from titan.tiny_service.service.service_bus.memory_service_bus import (
    MemoryServiceBusServer,
    MemoryServiceBusClient,
)

logger = logging.getLogger(__name__)



def generate_random_event_messages(rng, count: int):
    for x in range(count):
        byte_len = random.randint(3,10)
        event_bytes = random.getrandbits(byte_len * 8).to_bytes(length=byte_len, byteorder='big')
        yield service_bus_messages.EventMessage(seq=x, event_type='DummyEvent', event_bytes=event_bytes)


def generate_random_command_messages(rng, count: int):
    BAD_COMMAND_PROBABILITY = 0.1
    for x in range(count):
        byte_len = random.randint(3,10)
        command_bytes = random.getrandbits(byte_len * 8).to_bytes(length=byte_len, byteorder='big')
        if random.random() < BAD_COMMAND_PROBABILITY:
            yield service_bus_messages.CommandMessage(command_type='BadCommand', command_bytes=command_bytes)
        else:
            yield service_bus_messages.CommandMessage(command_type='DummyCommand', command_bytes=command_bytes)


async def simulate_event_publishing(service_bus_server, event_messages):
    for event_message in event_messages:
        await service_bus_server.send_event_message(event_message)
        await asyncio.sleep(0.01)

async def ensure_valid_event_receiving(service_bus_client, expected_event_messages):
    try:
        logger.info(f"ensure_valid_event_receiving({id(service_bus_client)})")                
        # make a copy
        expected_event_messages = list(expected_event_messages)
        result = 0

        # # receive any catchup events first
        # async for event_message in service_bus_client.catchup_event_messages():
        #     assert event_message == expected_event_messages.pop(0)
        #     logger.info(f"Validated catchup event #{event_message.seq()}")


        for counter, expected_event_message in enumerate(expected_event_messages):
            logger.info(f"Waiting for event #{counter} ...")
            received_event_message = await service_bus_client.receive_event_message()
            assert received_event_message == expected_event_message
            logger.info(f"Validated event #{received_event_message.seq()}")
            result += 1

        return result


    except BaseException as e:
        logger.error(f"Got error in ensure_valid_event_receiving({id(service_bus_client)}) : {e}", exc_info=True)
        raise



async def simulate_command_sending(service_bus_client, command_messages):
    for command_message in command_messages:
        await service_bus_client.send_command_message(command_message)
        command_receipt_message = await service_bus_client.receive_command_receipt_message()
        if command_message.command_type() == 'BadCommand':
            assert command_receipt_message.command_receipt_type() == 'CommandRejectedReceipt'
        else:
            assert command_receipt_message.command_receipt_type() == 'CommandAcceptedReceipt'
        await asyncio.sleep(0.01)


async def simulate_service_and_verify_commands_received(service_bus_server, expected_command_messages, event_messages):
    event_messages = list(event_messages)
    result = 0
    try:
        logger.info(f"simulate_service_and_verify_commands_received()")
        for counter, expected_command_message in enumerate(expected_command_messages):
            logger.info(f"Waiting for command #{counter} ...")
            received_command_message = await service_bus_server.receive_command_message()
            assert received_command_message == expected_command_message

            if received_command_message.command_type() == 'BadCommand':
                command_receipt_message = service_bus_messages.CommandReceiptMessage(   command_receipt_type='CommandRejectedReceipt',
                                                                                        command_receipt_bytes=b'' )
            else:
                command_receipt_message = service_bus_messages.CommandReceiptMessage(   command_receipt_type='CommandAcceptedReceipt',
                                                                                        command_receipt_bytes=b''  )
            await service_bus_server.send_command_receipt_message(command_receipt_message)


            # publish some events ?
            if received_command_message.command_type() != 'BadCommand':
                await service_bus_server.send_event_message(event_messages.pop(0))
            await asyncio.sleep(0.01)


            logger.info(f"Validated command #{counter}")

            result += 1
        # publish remaining events
        while event_messages:
            await service_bus_server.send_event_message(event_messages.pop(0))
            await asyncio.sleep(0.01)

        return result

    except BaseException as e:
        logger.error(f"Got error in simulate_service_and_verify_commands_received() : {e}", exc_info=True)
        raise




@pytest.mark.asyncio
async def test_all_event_messages_get_received():
    test_event_messages = list(generate_random_event_messages(random.Random(42), 100))
    async with MemoryServiceBusServer() as service_bus_server:
        async with service_bus_server.create_service_bus_client() as service_bus_client_a:
            async with service_bus_server.create_service_bus_client() as service_bus_client_b:
                async with service_bus_server.create_service_bus_client() as service_bus_client_c:
                    tasks = [
                        asyncio.create_task(simulate_event_publishing(service_bus_server, test_event_messages)),
                        asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages)),
                        asyncio.create_task(ensure_valid_event_receiving(service_bus_client_b, test_event_messages)),
                        asyncio.create_task(ensure_valid_event_receiving(service_bus_client_c, test_event_messages)),
                    ]
                    async with AsyncTaskRunner(tasks) as task_runner:
                        await task_runner.wait_closed()
                    assert tasks[1].done() and (not tasks[1].cancelled())
                    assert tasks[2].done() and (not tasks[2].cancelled())
                    assert tasks[3].done() and (not tasks[3].cancelled())

@pytest.mark.asyncio
async def test_slow_client():
    test_event_messages = list(generate_random_event_messages(random.Random(42), 100))
    async with MemoryServiceBusServer() as service_bus_server:
        # start publishing before setting up the client
        publish_task = asyncio.create_task(simulate_event_publishing(service_bus_server, test_event_messages))
        await asyncio.sleep(3)
        # now delay the second client - it will miss all events !
        async with service_bus_server.create_service_bus_client() as service_bus_client_a:
            tasks = [
                publish_task,
                asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages)),
            ]
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()
                assert tasks[1].done() and (not tasks[1].cancelled())


@pytest.mark.asyncio
async def test_bad_event_message_seq():
    test_event_messages = list(generate_random_event_messages(random.Random(42), 100))
    # last event message is a 'bad one'
    test_event_messages.append(service_bus_messages.EventMessage(seq=101, event_type='DummyEvent', event_bytes=b'bad event'))
    async with MemoryServiceBusServer() as service_bus_server:
        async with service_bus_server.create_service_bus_client() as service_bus_client_a:
            tasks = [
                asyncio.create_task(simulate_event_publishing(service_bus_server, test_event_messages)),
                asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages)),
            ]
            try:
                async with AsyncTaskRunner(tasks) as task_runner:
                    await task_runner.wait_closed()
                    pytest.fail(f"Expected an exception since the last event message had a bad seq number !")
            except BaseException as e:
                assert type(e) == ServiceBusException



@pytest.mark.asyncio
async def test_command_passing():
    async def _wait_after_task(coro, delay):
        """We don't care about cancellation exceptions after the main task is done"""
        result = await coro
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass
        return result

    test_event_messages = list(generate_random_event_messages(random.Random(42), 100))
    test_command_messages = list(generate_random_command_messages(random.Random(42), 100))

    async with MemoryServiceBusServer() as service_bus_server:
        async with service_bus_server.create_service_bus_client() as service_bus_client_a:
            async with service_bus_server.create_commandable_service_bus_client() as service_bus_client_b:
                tasks = [
                    asyncio.create_task(_wait_after_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages), 2)),
                    asyncio.create_task(_wait_after_task(simulate_command_sending(service_bus_client_b, test_command_messages), 2)),
                    asyncio.create_task(_wait_after_task(simulate_service_and_verify_commands_received(service_bus_server, test_command_messages, test_event_messages), 2))
                ]
                async with AsyncTaskRunner(tasks) as task_runner:
                    await task_runner.wait_closed()
                    assert tasks[0].done() and (tasks[0].result() == len(test_event_messages))
                    assert tasks[2].done() and (tasks[2].result() == len(test_command_messages))