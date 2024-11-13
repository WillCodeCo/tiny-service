import asyncio
import pytest
import sys
import logging
import multiprocessing
import time
import signal
import sys
import platform
from titan.tiny_service import service
from titan.tiny_service.async_helper import AsyncTaskHelper
from tests.titan.tiny_service.service import prime_number_processor
from tests.titan.tiny_service.service.prime_number_processor_tester import PrimeNumberProcessorTester, PrimeNumberProcessorTesterException


logger = logging.getLogger(__name__)





async def start_service_for_test(listen_host, listen_port):
    if platform.system() != "Windows":
        asyncio.get_running_loop().add_signal_handler(signal.SIGINT, lambda: sys.exit(0))
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, lambda: sys.exit(0))
    # start the service
    async with service.service_bus.HttpServiceBusServer(listen_host, listen_port) as service_bus_server:
        async with prime_number_processor.Service(service_bus_server) as prime_number_processor_service:
            await prime_number_processor_service.wait_closed()



async def run_service_client_test(service_bus_client, test_count):
    logger.info("connecting service-bus")
    service_client = prime_number_processor.ServiceClient(service_bus_client)
    logger.info("connected")
    service_event_producer = service_client
    service_command_executor = service_client
    async with PrimeNumberProcessorTester(service_event_producer, service_command_executor, "tester-0", test_count) as service_client_tester:
        try:
            await service_client_tester.wait_closed()
        except PrimeNumberProcessorTesterException as e:
            logger.error(f"[Client.PrimeNumberProcessorTester]  Test failed: {e}")
            raise

async def start_service_client_for_test(host, port, test_count):
    if platform.system() != "Windows":
        asyncio.get_running_loop().add_signal_handler(signal.SIGINT, lambda: sys.exit(0))
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, lambda: sys.exit(0))
    # start the client    
    async with service.service_bus.HttpServiceBusServer(host, port) as service_bus_server:
        async with service.service_bus.HttpCommandableServiceBusClient(host, port) as service_bus_client:
            tasks = [asyncio.create_task(run_service_client_test(service_bus_client, test_count))]
            await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks, timeout=20)
    await asyncio.sleep(5)
    logger.info("Checking the service is still running with another test")
    async with service.service_bus.HttpCommandableServiceBusClient(host, port) as service_bus_client:
        tasks = [asyncio.create_task(run_service_client_test(service_bus_client, test_count))]
        await AsyncTaskHelper.wait_for_all_and_cancel_pending(tasks, timeout=20)

def service_main(listen_host, listen_port):
    try:
        asyncio.run(start_service_for_test(listen_host, listen_port))
    except SystemExit:
        print("Server closing down ...")
        asyncio.run(asyncio.sleep(0.5))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Exception with type `{type(e)}` in test_service.service_main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        print("Server has terminated.")


def service_client_main(host, port, test_count):
    try:
        asyncio.run(start_service_client_for_test(host, port, test_count))
    except SystemExit:
        print("Client closing down ...")
        asyncio.run(asyncio.sleep(0.5))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Exception with type `{type(e)}` in test_service.service_client_main: {e}", exc_info=True)
        sys.exit(1)
    finally:
        print("Client has terminated.")




def test_service_with_http_service_bus():
    try:
        service_process = multiprocessing.Process(target=service_main, args=('localhost', 9999))
        service_client_process = multiprocessing.Process(target=service_client_main, args=('localhost', 9999, 100))
        service_process.start()
        service_client_process.start()

        processes = [service_process, service_client_process]
        while True:
            if not all([p.is_alive() for p in processes]):
                for p in processes:
                    p.kill()
                    p.join()
                break
            else:
                time.sleep(.5)

        print(f"Exit code from service: {service_process.exitcode}")
        print(f"Exit code from service-client: {service_client_process.exitcode}")

        assert service_client_process.exitcode == 0
        
    finally:
        print("Ensuring all processes are killed ...")
        for p in processes:
            if p.is_alive():
                p.kill()        




@pytest.mark.asyncio
async def test_service_in_memory_basic():
    test_count = 100
    async with service.service_bus.MemoryServiceBusServer() as service_bus_server:
        async with prime_number_processor.Service(service_bus_server) as prime_number_processor_service:
            async with service_bus_server.create_commandable_service_bus_client() as service_bus_client:
                # create the service client
                service_client = prime_number_processor.ServiceClient(service_bus_client)
                try:
                    await PrimeNumberProcessorTester.basic_test(service_client)
                except PrimeNumberProcessorTesterException as e:
                    logger.error(f"[Client.PrimeNumberProcessorTester.]  Test failed: {e}")
                    raise




@pytest.mark.asyncio
async def test_service_in_memory():
    test_count = 100

    async with service.service_bus.MemoryServiceBusServer() as service_bus_server:
        async with prime_number_processor.Service(service_bus_server) as prime_number_processor_service:
            async with service_bus_server.create_commandable_service_bus_client() as service_bus_client:
                service_client = prime_number_processor.ServiceClient(service_bus_client)
                service_event_producer = service_client
                service_command_executor = service_client


                async with PrimeNumberProcessorTester(service_event_producer, service_command_executor, "tester-0", test_count) as service_client_tester:
                    try:
                        await service_client_tester.wait_closed()
                    except PrimeNumberProcessorTesterException as e:
                        logger.error(f"[Client.PrimeNumberProcessorTester]  Test failed: {e}")
                        raise



