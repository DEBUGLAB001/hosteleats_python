import time


def now_seconds():
    return time.time()


def now_millis():
    return int(now_seconds() * 1000)
