import pytest

import analytics
import auth
import campus
import clock
import combo
import data
import limiter
import slots


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


@pytest.fixture(autouse=True)
def reset_application_state():
    auth.clear_sessions()
    limiter.clear_limits()
    data.reset_data()
    yield
    auth.clear_sessions()
    limiter.clear_limits()
    data.reset_data()


def test_session_expires_at_configured_time(monkeypatch):
    current = [1000.0]
    monkeypatch.setattr(clock, "now_seconds", lambda: current[0])
    
    # Valid login produces an active session immediately
    login_result = auth.login("aarav", "hostel123")
    check(login_result is not None, "Expected valid demo credentials to succeed")
    token = login_result["token"]
    session = auth.get_session(token)
    check(session is not None, "A new session must be active immediately after login")
    check(session["username"] == "aarav", "Session username must match")

    # After configured TTL passes, the session must be expired
    current[0] += auth.TOKEN_TTL_SECONDS + 1
    expired_session = auth.get_session(token)
    check(expired_session is None, f"Expected session to expire after {auth.TOKEN_TTL_SECONDS} seconds")


def test_rejected_request_does_not_extend_limit_window(monkeypatch):
    current = [100.0]
    monkeypatch.setattr(clock, "now_seconds", lambda: current[0])

    # Three valid requests within the window
    check(limiter.allow_order("aarav") is True, "First request must be accepted")
    current[0] = 110.0
    check(limiter.allow_order("aarav") is True, "Second request must be accepted")
    current[0] = 120.0
    check(limiter.allow_order("aarav") is True, "Third request must be accepted")

    # Fourth request exceeds rate limit and is rejected
    current[0] = 121.0
    check(limiter.allow_order("aarav") is False, "Fourth request exceeds rate limit")

    # Advance time past expiration of the first request (at 100.0)
    current[0] = 100.0 + limiter.WINDOW_SECONDS + 1
    # Only two valid requests remain in the window, so a new request should be permitted
    check(limiter.allow_order("aarav") is True, "Expected a fresh order slot after the earliest valid request expired")


def test_peak_window_includes_final_valid_start():
    # Ordinary case where the peak is near the beginning
    early = analytics.peak_load([12, 10, 2, 1, 1], 2)
    check(early["total"] == 22, f"Expected 22 orders, got {early['total']}")
    check(early["start"] == 0, f"Expected start at hour 0, got {early['start']}")

    # Case where the peak volume is in the final valid rolling window
    late_rush = analytics.peak_load([1, 2, 3, 20], 2)
    check(late_rush["total"] == 23, f"Expected 23 orders, got {late_rush['total']}")
    check(late_rush["start"] == 2, f"Expected the rush to start at hour 2, got {late_rush['start']}")


def test_route_distance_includes_full_path():
    # Direct route with single hop
    direct = campus.shortest_route({"A": {"B": 3}, "B": {"A": 3}}, "A", "B")
    check(direct["minutes"] == 3, f"Expected 3 minutes, got {direct['minutes']}")

    # Graph where multi-hop has smaller final edge weight but larger accumulated total distance
    graph = {
        "Start": {"Oak": 1, "Pine": 6},
        "Oak": {"Start": 1, "Gate": 7},
        "Pine": {"Start": 6, "Gate": 5},
        "Gate": {"Oak": 7, "Pine": 5},
    }
    route = campus.shortest_route(graph, "Start", "Gate")
    # Path Start -> Oak -> Gate has cumulative minutes: 1 + 7 = 8
    # Path Start -> Pine -> Gate has cumulative minutes: 6 + 5 = 11
    check(route["minutes"] == 8, f"Expected 8 minutes, got {route['minutes']}")
    check(route["path"] == ["Start", "Oak", "Gate"], f"Unexpected route path: {' -> '.join(route['path'])}")


def test_combo_uses_each_menu_item_once():
    items = [
        {"id": "toastie", "name": "Toastie", "price": 50, "satisfaction": 9},
        {"id": "samosa", "name": "Samosa", "price": 20, "satisfaction": 4},
        {"id": "chai", "name": "Chai", "price": 15, "satisfaction": 3},
        {"id": "fruit", "name": "Fruit cup", "price": 30, "satisfaction": 5},
    ]
    # Insufficient budget returns empty combo
    small = combo.best_combo(items, 14)
    check(small["items"] == [] and small["score"] == 0, "A budget below every item should return an empty combo")

    # At budget 60: Toastie (50) gives satisfaction 9
    result = combo.best_combo(items, 60)
    check(result["score"] == 9, f"Expected score 9, got {result['score']}")
    ids = [item["id"] for item in result["items"]]
    check(len(ids) == len(set(ids)), f"A menu item should appear only once, found duplicates: {ids}")
    check(result["total"] <= 60, f"Expected total within budget, got {result['total']}")


def test_overlapping_slots_merge_to_furthest_end():
    # Disjoint bookings
    separate = slots.merge_intervals([[10, 20], [30, 40]])
    check(separate == [[10, 20], [30, 40]], f"Unexpected reserved windows: {separate}")

    # Overlapping bookings where the second window ends earlier than the first
    bookings = [[540, 660], [570, 600], [700, 730]]
    merged = slots.merge_intervals(bookings)
    check(merged == [[540, 660], [700, 730]], f"Expected reserved window to end at 660, got {merged[0][1]}")
    check(slots.is_available(630, 640, bookings) is False, "A time inside a reserved window should be unavailable")
