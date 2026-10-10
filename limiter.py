import clock

WINDOW_SECONDS = 30
MAX_ORDERS = 3
ORDER_TIMES = {}


def allow_order(user_id):
    now = clock.now_seconds()
    times = [stamp for stamp in ORDER_TIMES.get(user_id, []) if now - stamp < WINDOW_SECONDS]
    times.append(now)
    ORDER_TIMES[user_id] = times
    if len(times) > MAX_ORDERS:
        return False
    return True


def clear_limits():
    ORDER_TIMES.clear()
