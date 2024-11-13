import pytest
import asyncio
import time
import itertools
from titan.tiny_service.time_source import TimeSource, InterpolatingDiscreteTimeSource, ElapsedTimer



def assert_close_enough(target_value, actual_value, tolerance):
    if (abs(actual_value-target_value) / target_value) > tolerance:
        pytest.fail(f"{actual_value} is outside of the tolerance range when comparing to target {target_value}")

def test_native_time():
    timestamp = int(time.time()*1000)
    native_time = TimeSource.create_native()
    assert_close_enough(timestamp, native_time.timestamp(), 0.001)


def test_other_time_reference():
    timestamp = int(time.time()*1000)
    time_source = TimeSource(90000, 1.0)
    time_source.start()
    assert 90000 == time_source.timestamp()
    time.sleep(1)
    assert_close_enough(91000, time_source.timestamp(), 0.005)
    time.sleep(1.23)
    assert_close_enough(92230, time_source.timestamp(), 0.005)

def test_other_time_reference_with_multiplier():
    timestamp = int(time.time()*1000)
    time_source = TimeSource(90000, 2.0)
    time_source.start()
    assert 90000 == time_source.timestamp()
    time.sleep(1)
    assert_close_enough(92000, time_source.timestamp(), 0.005)
    time.sleep(1.23)
    assert_close_enough(94460, time_source.timestamp(), 0.005)



def test_elapsed_timer():
    timestamp = int(time.time()*1000)
    time_source = TimeSource(90000, 2.0)
    time_source.start()
    elapsed_time = ElapsedTimer(time_source)
    time.sleep(1)
    assert_close_enough(2000, elapsed_time.elapsed_ms(), 0.005)
    time.sleep(2.23)
    assert_close_enough(6460, elapsed_time.elapsed_ms(), 0.005)
    elapsed_time.reset()
    time.sleep(1.36)
    assert_close_enough(2720, elapsed_time.elapsed_ms(), 0.005)



@pytest.mark.asyncio
async def test_sleep():
    time_source = TimeSource(90000, 2.0)
    time_source.start()

    target_deadline = time_source.timestamp() + 3000
    await time_source.sleep_until(target_deadline)
    assert time_source.timestamp() == target_deadline


@pytest.mark.asyncio
async def test_timestamps():
    time_source = TimeSource.create_native()

    await asyncio.sleep(1)
    assert_close_enough(int(time.time()*1000), time_source.timestamp(), 0.005)

    await asyncio.sleep(5)
    assert_close_enough(int(time.time()*1000), time_source.timestamp(), 0.005)    


@pytest.mark.asyncio
async def test_interpolating_time_source():
    discrete_timestamps = [125, 3000, 5000, 9000, 12340, 20000]
    speedup = 5
    time_source = InterpolatingDiscreteTimeSource(discrete_timestamps, speedup, discrete_timestamps[-1])
    time_source.start()
    assert time_source.timestamp() == discrete_timestamps[0]
    await asyncio.sleep(1/speedup)
    assert_close_enough(discrete_timestamps[0]+1000, time_source.timestamp(), 0.005)
    await asyncio.sleep(1/speedup)
    assert_close_enough(discrete_timestamps[0]+2000, time_source.timestamp(), 0.005)
    await asyncio.sleep(5/speedup)
    assert_close_enough(discrete_timestamps[1], time_source.timestamp(), 0.005)
    time_source.resume_next_period()
    assert time_source.timestamp() == discrete_timestamps[1]
    await asyncio.sleep(1.75/speedup)
    assert_close_enough(discrete_timestamps[1]+1750, time_source.timestamp(), 0.005)
    await time_source.sleep_until(discrete_timestamps[2])
    assert time_source.timestamp() == discrete_timestamps[2]
    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[3])
    assert time_source.timestamp() == discrete_timestamps[3]    




@pytest.mark.asyncio
async def test_interpolating_time_source_repeated_periods():
    discrete_timestamps = [0, 0, 0, 1, 1, 2, 2, 3]
    speedup = 50
    time_source = InterpolatingDiscreteTimeSource(discrete_timestamps, speedup, None)
    time_source.start()

    await time_source.sleep_until(discrete_timestamps[0])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[1]

    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[1])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[2]

    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[2])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[3]


    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[3])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[4]

    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[4])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[5]

    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[5])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[6]


    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[6])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[7]

    time_source.resume_next_period()
    await time_source.sleep_until(discrete_timestamps[7])
    await asyncio.sleep(1/speedup)
    assert time_source.timestamp() == discrete_timestamps[7]



def test_interpolating_time_source_periods():
    timestamps = list(range(10))
    period_gen = InterpolatingDiscreteTimeSource.generate_periods((t for t in timestamps))
    # expected periods
    a, b = itertools.tee((t for t in timestamps))
    next(b, None)
    expected_periods = zip(a, b)
    assert list(period_gen) == list(expected_periods)
