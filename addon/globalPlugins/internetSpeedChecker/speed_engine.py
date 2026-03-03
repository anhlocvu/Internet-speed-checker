# Internet Speed Engine for NVDA
# Wrapper for the Ookla/Speedtest.net engine.

from . import ookla_engine

def get_speed_results():
    """
    Performs speed test using Speedtest.net's global infrastructure.
    """
    return ookla_engine.run_test()
