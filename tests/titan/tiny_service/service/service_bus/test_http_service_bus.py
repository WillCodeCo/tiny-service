import time
import io
import asyncio
import pytest
import logging
import aiohttp
import random
from titan.tiny_service.async_helper import AsyncTaskRunner
from titan.tiny_service.service.service_bus import (
    ServiceBusException
)
from titan.tiny_service.service.service_bus import service_bus_messages
from titan.tiny_service.service.service_bus.http_service_bus import (
    HttpServiceBusServer,
    HttpServiceBusClient,
    HttpCommandableServiceBusClient,
)

logger = logging.getLogger(__name__)



def system_timestamp():
    return int(time.time()*1000)

async def delay_task_completion(coro, min_running_time: int):
    quit_timestamp = system_timestamp() + min_running_time
    result = await coro
    while system_timestamp() < quit_timestamp:
        ms_remaining = quit_timestamp - system_timestamp()
        try:
            await asyncio.sleep(((ms_remaining*0.8) / 1000))
        except asyncio.CancelledError:
            break
    return result

def generate_random_event_messages(rng, count: int):
    for x in range(count):
        byte_len = random.randint(3,10)
        event_bytes = random.getrandbits(byte_len * 8).to_bytes(length=byte_len, byteorder='big')
        yield service_bus_messages.EventMessage(seq=x, event_type='DummyEvent', event_bytes=event_bytes)


def generate_random_command_messages(rng, count: int):
    BAD_COMMAND_PROBABILITY = 0.1
    for x in range(count):
        byte_len = random.randint(3,10)
        command_bytes = str(x).encode('ascii')+b'-'+random.getrandbits(byte_len * 8).to_bytes(length=byte_len, byteorder='big')
        if random.random() < BAD_COMMAND_PROBABILITY:
            yield service_bus_messages.CommandMessage(command_type='BadCommand', command_bytes=command_bytes)
        else:
            yield service_bus_messages.CommandMessage(command_type='DummyCommand', command_bytes=command_bytes)


async def simulate_event_publishing(service_bus_server, delay, event_messages):
    for event_message in event_messages:
        await service_bus_server.send_event_message(event_message)
        await asyncio.sleep(delay)



async def ensure_http_endpoint_exists(url: str):
    async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                assert resp.status == 200

async def ensure_ws_endpoint_exists(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(url) as ws:
            assert ws.exception() == None
            return
    pytest.fail(f"Could not connect to `{url}`")



async def ensure_valid_catchup_events(host: str, port: int, expected_event_messages):

    async def _read_chunks_into_buf(resp, buf):
        chunk = None
        while chunk != b'':
            chunk = await resp.read(10)
            if chunk:
                buf.write(chunk)
        buf.seek(0)

    url = f"http://{host}:{port}/catchup-event-messages?min_event_message_seq=0"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            assert resp.status == 200
            buf = io.BytesIO()
            await _read_chunks_into_buf(resp.content, buf)
            catchup_event_messages = list(service_bus_messages.EventMessage.generate_from_stream(buf))           
            assert len(catchup_event_messages) == len(expected_event_messages)
            assert catchup_event_messages == expected_event_messages





async def ensure_valid_event_receiving(service_bus_client, expected_event_messages, rng, max_sleep: int):
    logger.info(f"ensure_valid_event_receiving({id(service_bus_client)})")                
    for counter, expected_event_message in enumerate(expected_event_messages):
        sleep_time = rng.randint(0, max_sleep)/1000
        logger.info(f"Sleeping for {sleep_time} seconds")
        await asyncio.sleep(sleep_time)
        assert service_bus_client.active(), "service_bus_client is no longer active"
        logger.info(f"Waiting for event #{counter} ...")
        received_event_message = await service_bus_client.receive_event_message()
        assert received_event_message == expected_event_message
        logger.info(f"Validated event #{received_event_message.seq()}")



async def simulate_command_sending(commandable_service_bus_client, command_messages, rng, max_sleep: int):
    for command_message in command_messages:
        assert commandable_service_bus_client.active(), "commandable_service_bus_client is no longer active"
        await commandable_service_bus_client.send_command_message(command_message)
        sleep_time = rng.randint(0, max_sleep)/1000
        logger.info(f"Sleeping for {sleep_time} seconds")
        await asyncio.sleep(sleep_time)
        assert commandable_service_bus_client.active(), "commandable_service_bus_client is no longer active"
        await commandable_service_bus_client.receive_command_receipt_message()

async def ensure_valid_command_receiving(service_bus_server, expected_command_messages, rng, max_sleep: int):
    try:
        logger.info(f"ensure_valid_command_receiving() by service_bus_server")                
        for counter, expected_command_message in enumerate(expected_command_messages):           
            logger.info(f"Waiting for command #{counter} ...")
            assert service_bus_server.active(), "service_bus_server is no longer active"
            received_command_message = await service_bus_server.receive_command_message()
            assert received_command_message == expected_command_message
            logger.info(f"Validated command #{counter}")
            # random sleep
            sleep_time = rng.randint(0, max_sleep)/1000
            logger.info(f"Sleeping for {sleep_time} seconds")
            await asyncio.sleep(sleep_time)
            # need to send a receipt
            command_receipt_message = service_bus_messages.CommandReceiptMessage(   command_receipt_type='DummyReceipt',
                                                                                    command_receipt_bytes=b'' )
            assert service_bus_server.active(), "service_bus_server is no longer active"
            await service_bus_server.send_command_receipt_message(command_receipt_message)
    except BaseException as e:
        logger.error(f"Got error in ensure_valid_command_receiving() : {e}", exc_info=True)
        raise


async def simulate_random_disconnections(service_bus_server, rng):
    while True:
        await asyncio.sleep(rng.randint(2000, 10000)/1000)
        logger.info(f"Simulating a disconnection !")
        for ws in list(service_bus_server._app['websockets']):
            try:
                await ws.close()
            except:
                pass

async def count_websocket_connections(service_bus_server):
    try:
        result = set()
        while True:
            for ws in service_bus_server._app['websockets']:
                result.add(id(ws))
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        return len(result)


async def ensure_no_websocket_disconnections(service_bus_server, timeout: int):
    TICK_DURATION = 0.1
    last_socks = set()
    for tick_count in range(int(timeout/TICK_DURATION)):
        current_socks = set((id(ws) for ws in service_bus_server._app['websockets']))
        assert (last_socks - current_socks) == set(), f"A websocket was disconnected after {tick_count*TICK_DURATION} seconds"
        last_socks = current_socks
        await asyncio.sleep(TICK_DURATION)


async def simulate_command_execution(service_bus_client, command_messages):
    for command_message in command_messages:
        assert service_bus_client.active(), "service_bus_client is no longer active"
        await service_bus_client.send_command_message(command_message)
        assert service_bus_client.active(), "service_bus_client is no longer active"
        command_receipt_message = await service_bus_client.receive_command_receipt_message()
        if command_message.command_type() == 'BadCommand':
            assert command_receipt_message.command_receipt_type() == 'CommandRejectedReceipt'
        else:
            assert command_receipt_message.command_receipt_type() == 'CommandAcceptedReceipt'
        await asyncio.sleep(0.01)



async def simulate_service_and_verify_commands_received(service_bus_server, expected_command_messages, event_messages, rng, max_sleep: int):
    event_messages = list(event_messages)
    result = 0
    try:
        logger.info(f"simulate_service_and_verify_commands_received()")
        for counter, expected_command_message in enumerate(expected_command_messages):
            logger.info(f"Waiting for command #{counter} ...")
            assert service_bus_server.active(), "service_bus_server is no longer active"
            received_command_message = await service_bus_server.receive_command_message()
            assert received_command_message == expected_command_message

            if received_command_message.command_type() == 'BadCommand':
                command_receipt_message = service_bus_messages.CommandReceiptMessage(   command_receipt_type='CommandRejectedReceipt',
                                                                                        command_receipt_bytes=b'' )
            else:
                command_receipt_message = service_bus_messages.CommandReceiptMessage(   command_receipt_type='CommandAcceptedReceipt',
                                                                                        command_receipt_bytes=b''  )
            sleep_time = rng.randint(0, max_sleep)/1000
            logger.info(f"Sleeping for {sleep_time} seconds")
            await asyncio.sleep(sleep_time)

            assert service_bus_server.active(), "service_bus_server is no longer active"
            await service_bus_server.send_command_receipt_message(command_receipt_message)


            # publish some events ?
            if received_command_message.command_type() != 'BadCommand':
                assert service_bus_server.active(), "service_bus_server is no longer active"
                await service_bus_server.send_event_message(event_messages.pop(0))
            await asyncio.sleep(0.01)


            logger.info(f"Validated command #{counter}")

            result += 1
        # publish remaining events
        while event_messages:
            assert service_bus_server.active(), "service_bus_server is no longer active"
            await service_bus_server.send_event_message(event_messages.pop(0))
            await asyncio.sleep(0.01)

        return result

    except BaseException as e:
        logger.error(f"Got error in simulate_service_and_verify_commands_received() : {e}", exc_info=True)
        raise



@pytest.mark.asyncio
async def test_http_service_bus_server_connections():
    test_event_messages = list(generate_random_event_messages(random.Random(42), 50))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        await simulate_event_publishing(service_bus_server, 0.1, test_event_messages)
        await ensure_http_endpoint_exists('http://localhost:6666/catchup-event-messages?min_event_message_seq=0')
        await ensure_ws_endpoint_exists('http://localhost:6666/event-bus')
        await ensure_ws_endpoint_exists('http://localhost:6666/command-bus')
        await ensure_valid_catchup_events('localhost', 6666, test_event_messages)


@pytest.mark.asyncio
async def test_http_service_publishing_events():
    test_event_messages = list(generate_random_event_messages(random.Random(42), 100))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        await simulate_event_publishing(service_bus_server, 0.1, test_event_messages)
        

@pytest.mark.asyncio
async def test_http_service_publishing_bad_event_message_seq():
    test_event_messages = list(generate_random_event_messages(random.Random(42), 100))
    # last event message is a 'bad one'
    test_event_messages.append(service_bus_messages.EventMessage(seq=101, event_type='DummyEvent', event_bytes=b'bad event'))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        try:
            await simulate_event_publishing(service_bus_server, 0.1, test_event_messages)
            pytest.fail(f"Expected an exception since we are trying to publish an event with a bad seq number !")
        except BaseException as e:
            assert type(e) == ServiceBusException



@pytest.mark.asyncio
async def test_http_service_bus_can_receive_an_event_message():
    test_event_messages = list(generate_random_event_messages(random.Random(42), 10))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpServiceBusClient('localhost', 6666) as service_bus_client_a:
            await simulate_event_publishing(service_bus_server, 0.1, test_event_messages)
            received_event_message = await service_bus_client_a.receive_event_message()
            assert received_event_message == test_event_messages[0]
            logger.info("trying to close server")
            await service_bus_server.close()



@pytest.mark.asyncio
async def test_http_service_bus_all_event_messages_get_received():
    MAX_TEST_DURATION = 90000
    MAX_SLEEP = 1800
    rng = random.Random(42)
    test_event_messages = list(generate_random_event_messages(random.Random(42), 100))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpServiceBusClient('localhost', 6666) as service_bus_client_a:
            tasks = [
                asyncio.create_task(delay_task_completion(simulate_event_publishing(service_bus_server, 0.1, test_event_messages), MAX_TEST_DURATION)),
                asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages, rng, MAX_SLEEP)),
            ]
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()
            assert tasks[1].done() and (not tasks[1].cancelled())




@pytest.mark.asyncio
async def test_http_service_bus_event_receiving_amidst_disconnections():
    MAX_TEST_DURATION = 90000
    rng = random.Random(42)
    test_event_messages = list(generate_random_event_messages(rng, 100))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpServiceBusClient('localhost', 6666) as service_bus_client_a:
            tasks = [
                asyncio.create_task(delay_task_completion(simulate_event_publishing(service_bus_server, 0.2, test_event_messages), MAX_TEST_DURATION)),
                asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages, rng, 500)),
                asyncio.create_task(simulate_random_disconnections(service_bus_server, rng))
            ]            
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()
            assert tasks[1].done() and (not tasks[1].cancelled())


@pytest.mark.asyncio
async def test_http_service_bus_event_keepalives():
    """Publish events super slowly to make sure that our connections still stay despite this"""
    MAX_TEST_DURATION = 30000
    MAX_SLEEP = 1800
    rng = random.Random(42)
    test_event_messages = list(generate_random_event_messages(rng, 2))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpServiceBusClient('localhost', 6666) as service_bus_client_a:
            tasks = [
                asyncio.create_task(delay_task_completion(simulate_event_publishing(service_bus_server, 20, test_event_messages), MAX_TEST_DURATION)),
                asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages, rng, MAX_SLEEP)),
                asyncio.create_task(count_websocket_connections(service_bus_server))
            ]            
            async with AsyncTaskRunner(tasks) as task_runner:                
                await task_runner.wait_closed()
            assert tasks[1].done() and (not tasks[1].cancelled())
            assert tasks[2].result() == 1


@pytest.mark.asyncio
async def test_http_service_stable_event_bus():
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpServiceBusClient('localhost', 6666) as service_bus_client:
            tasks = [
                asyncio.create_task(ensure_no_websocket_disconnections(service_bus_server, timeout=20))
            ]            
            async with AsyncTaskRunner(tasks) as task_runner:                
                await task_runner.wait_closed()
            assert tasks[0].done() and (not tasks[0].cancelled())


@pytest.mark.asyncio
async def test_http_service_stable_command_bus():
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpCommandableServiceBusClient('localhost', 6666) as service_bus_client:
            tasks = [
                asyncio.create_task(ensure_no_websocket_disconnections(service_bus_server, timeout=10))
            ]            
            async with AsyncTaskRunner(tasks) as task_runner:                
                await task_runner.wait_closed()
            assert tasks[0].done() and (not tasks[0].cancelled())



@pytest.mark.asyncio
async def test_http_service_bus_all_command_messages_get_received():
    MAX_TEST_DURATION = 90000
    MAX_SLEEP = 1800
    rng = random.Random(42)
    test_command_messages = list(generate_random_command_messages(rng, 100))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpCommandableServiceBusClient('localhost', 6666) as service_bus_client_a:
            tasks = [
                asyncio.create_task(delay_task_completion(simulate_command_sending(service_bus_client_a, test_command_messages, rng, MAX_SLEEP), MAX_TEST_DURATION)),
                asyncio.create_task(ensure_valid_command_receiving(service_bus_server, test_command_messages, rng, MAX_SLEEP)),
            ]
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()
            assert tasks[1].done() and (not tasks[1].cancelled())


@pytest.mark.asyncio
async def test_http_service_bus_all_command_messages_get_received_amidst_disconnections():
    MAX_TEST_DURATION = 180000
    MAX_SLEEP = 1800
    rng = random.Random(42)
    test_command_messages = list(generate_random_command_messages(rng, 100))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpCommandableServiceBusClient('localhost', 6666) as service_bus_client_a:
            tasks = [
                asyncio.create_task(delay_task_completion(simulate_command_sending(service_bus_client_a, test_command_messages, rng, MAX_SLEEP), MAX_TEST_DURATION)),
                asyncio.create_task(ensure_valid_command_receiving(service_bus_server, test_command_messages, rng, MAX_SLEEP)),
                asyncio.create_task(simulate_random_disconnections(service_bus_server, rng))
            ]
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()
            assert tasks[1].done() and (not tasks[1].cancelled())


@pytest.mark.asyncio
async def test_http_service_command_execution():
    MAX_TEST_DURATION = 180000
    MAX_SLEEP = 1800
    rng = random.Random(42)
    test_event_messages = list(generate_random_event_messages(rng, 100))
    test_command_messages = list(generate_random_command_messages(rng, 100))
    async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
        async with HttpServiceBusClient('localhost', 6666) as service_bus_client_a:
            async with HttpCommandableServiceBusClient('localhost', 6666) as service_bus_client_b:
                tasks = [
                    asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, test_event_messages, rng, MAX_SLEEP)),
                    asyncio.create_task(delay_task_completion(simulate_command_sending(service_bus_client_b, test_command_messages, rng, MAX_SLEEP), MAX_TEST_DURATION)),
                    asyncio.create_task(delay_task_completion(simulate_service_and_verify_commands_received(service_bus_server, test_command_messages, test_event_messages, rng, MAX_SLEEP), MAX_TEST_DURATION)),
                    asyncio.create_task(simulate_random_disconnections(service_bus_server, rng))
                ]
                async with AsyncTaskRunner(tasks) as task_runner:
                    await task_runner.wait_closed()
                    assert tasks[0].done() and (tasks[0].exception() == None)
                    assert tasks[2].done() and (tasks[2].result() == len(test_command_messages))


@pytest.mark.asyncio
async def test_http_service_reconnect_to_restarted_service():
    MAX_TEST_DURATION = 20000
    MAX_SLEEP = 1800
    rng_a = random.Random(42)
    rng_b = random.Random(4242)

    first_server_event_messages = list(generate_random_event_messages(rng_a, 5))
    second_server_event_messages = list(generate_random_event_messages(rng_b, 5))

    # we start the client first in this case
    async with HttpServiceBusClient('localhost', 6666) as service_bus_client_a:
        async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
            tasks = [
                asyncio.create_task(delay_task_completion(simulate_event_publishing(service_bus_server, 0.1, first_server_event_messages), MAX_TEST_DURATION)),
                asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, first_server_event_messages, rng_a, MAX_SLEEP)),
            ]
            async with AsyncTaskRunner(tasks) as task_runner:
                await task_runner.wait_closed()
            assert tasks[1].done() and (not tasks[1].cancelled())

        # sleep a bit
        await asyncio.sleep(0.1)
        # make a new server and have the client reconnect to this one !
        async with HttpServiceBusServer('localhost', 6666) as service_bus_server:
            tasks = [
                asyncio.create_task(delay_task_completion(simulate_event_publishing(service_bus_server, 0.1, second_server_event_messages), MAX_TEST_DURATION)),
                asyncio.create_task(ensure_valid_event_receiving(service_bus_client_a, second_server_event_messages, rng_b, MAX_SLEEP)),
            ]
            try:
                async with AsyncTaskRunner(tasks) as task_runner:
                    await task_runner.wait_closed()
                pytest.fail(f"Expected an exception to occur since the client should have failed.")
            except AssertionError as e:
                assert "is no longer active" in str(e)
