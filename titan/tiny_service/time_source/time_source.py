import asyncio
import time
import ntplib
import itertools


class TimeSourceException(Exception):
    pass

class TimeSource:
    def __init__(self, origin_timestamp, multiplier):
        self._creation_monotonic_timestamp = None
        self._origin_timestamp = origin_timestamp
        self._multiplier = multiplier

    @staticmethod
    def native_monotonic_timestamp():
        return int(time.monotonic_ns()//1000000)

    @staticmethod
    def native_timestamp():
        return int(time.time()*1000)

    def _native_elapsed_ms(self):
        if not self._has_started():
            return 0
        return TimeSource.native_monotonic_timestamp() - self._creation_monotonic_timestamp

    def _native_ms_until_timestamp(self, timestamp):
        delta_timestamp = timestamp - self.timestamp()
        return delta_timestamp // self._multiplier

    def _has_started(self):
        return self._creation_monotonic_timestamp is not None

    def timestamp(self):
        return self._origin_timestamp + int(self._native_elapsed_ms() * self._multiplier)

    async def sleep_until(self, deadline_timestamp):
        while not self._has_started():
            await asyncio.sleep(0.1)
        # More accurate sleeping
        while self._native_ms_until_timestamp(deadline_timestamp) > 0:
            delay = max(0.001, int(self._native_ms_until_timestamp(deadline_timestamp) * 0.8))
            await asyncio.sleep(delay/1000)

    async def sleep(self, delay_ms):
        await self.sleep_until(self.timestamp()+delay_ms)

    def start(self):
        self._creation_monotonic_timestamp = TimeSource.native_monotonic_timestamp()

    @staticmethod
    def create_native():
        time_source = TimeSource(TimeSource.native_timestamp(), 1)
        time_source.start()
        return time_source





class NtpTimeSource(TimeSource):
    @staticmethod
    def ntp_timestamp(ntp_server):
        c = ntplib.NTPClient()
        response = c.request(ntp_server, version=3)
        return int((response.dest_time + response.offset)*1000)

    @staticmethod
    def create(ntp_server):
        try:
            time_source = NtpTimeSource(NtpTimeSource.ntp_timestamp(ntp_server), 1)
            time_source.start()
            return time_source
        except Exception as e:
            raise TimeSourceException(f"Failed to create NtpTimeSource with NTP server `{ntp_server}`")


class InterpolatingDiscreteTimeSource:
    def __init__(self, discrete_timestamp_generator, multiplier, focus_timestamp=None):
        self._period_generator = InterpolatingDiscreteTimeSource.generate_periods(discrete_timestamp_generator)
        self._current_period = next(self._period_generator)
        self._multiplier = multiplier
        self._focus_timestamp = focus_timestamp        
        self._period_native_timestamp = None


    @classmethod
    def generate_periods(cls, discrete_timestamp_generator):
        # if we are given a list, wrap it to become a generator - dirty hack !
        if type(discrete_timestamp_generator) == list:
            discrete_timestamp_generator = (timestamp for timestamp in discrete_timestamp_generator)
        # otherwise make two independant iterators
        iter_a, iter_b = itertools.tee(discrete_timestamp_generator)
        # advance the right hand side
        next(iter_b, None)
        yield from zip(iter_a, iter_b)
    
    @staticmethod
    def native_monotonic_timestamp():
        return int(time.monotonic_ns()//1000000)

    @staticmethod
    def native_timestamp():
        return int(time.time()*1000)

    def _period_start_timestamp(self):
        return self._current_period[0]

    def _period_duration(self):
        return self._current_period[1] - self._current_period[0]

    def _native_period_elapsed_ms(self):
        if not self._has_started():
            return 0
        return TimeSource.native_monotonic_timestamp() - self._period_native_timestamp

    def _current_multiplier(self):
        if (self._focus_timestamp is not None) and (self._period_start_timestamp() >= self._focus_timestamp):
            return 1
        return self._multiplier

    def _period_elapsed_ms(self):
        if not self._has_started():
            return 0
        # dont go beyond period duration
        return min(self._period_duration(), self._native_period_elapsed_ms()*self._current_multiplier())

    def _has_started(self):
        return self._period_native_timestamp is not None

    def _is_waiting_for_next_period(self):
        return self._period_duration() < (self._native_period_elapsed_ms() * self._current_multiplier())

    def timestamp(self):
        return self._period_start_timestamp() + self._period_elapsed_ms()

    def resume_next_period(self):
        # only go to next period, if this isnt the very first call to resume_next_period()
        if (not self._has_started()):
            raise TimeSourceException(f"Cannot resume_next_period() because the time-source has not been started yet")
        try:
            self._current_period = next(self._period_generator)
            self._period_native_timestamp = TimeSource.native_monotonic_timestamp()
        except StopIteration:
            pass

    def _native_ms_until_timestamp(self, timestamp):
        delta_timestamp = timestamp - self.timestamp()
        return delta_timestamp // self._current_multiplier()


    async def sleep_until(self, deadline_timestamp):
        while (self._is_waiting_for_next_period() and deadline_timestamp > self.timestamp()):
            await asyncio.sleep(0.1)
        # More accurate sleeping
        while self._native_ms_until_timestamp(deadline_timestamp) > 0:
            delay = max(0.001, int(self._native_ms_until_timestamp(deadline_timestamp) * 0.8))
            await asyncio.sleep(delay/1000)

    async def sleep(self, delay_ms):
        await self.sleep_until(self.timestamp()+delay_ms)

    def start(self):
        self._period_native_timestamp = TimeSource.native_monotonic_timestamp()







class ElapsedTimer:
    def __init__(self, time_source):
        self._time_source = time_source
        self._timestamp_start = self._time_source.timestamp()

    def reset(self):
        self._timestamp_start = self._time_source.timestamp()

    def elapsed_ms(self):
        return self._time_source.timestamp() - self._timestamp_start

