# HostelEats

## Description

HostelEats is a Python Flask campus dining and pre-order application designed for students and canteen staff. It runs as a lightweight HTTP service with a browser interface, in-memory catalog and order state, and multiple interactive modules: menu browsing, knapsack combo planning, slot scheduling, shortest-path campus routing, rush hour volume analytics, and kitchen order dispatch.

## Repository Structure

```text
hosteleats-python-challenge/
├── challenge.json          Isolated runtime, port, start, and test configuration
├── requirements.txt        Python dependencies (Flask, pytest)
├── pytest.ini              Pytest configuration and test execution options
├── conftest.py             Pytest runner hooks and JSON test reporting
├── app.py                  Flask HTTP server, REST API endpoints, and session handlers
├── auth.py                 Authentication, HMAC-SHA256 token signing, and session TTL logic
├── clock.py                Time utility module providing epoch seconds and milliseconds
├── data.py                 In-memory seed data for menu items, initial orders, slots, and traffic
├── limiter.py              Sliding-window order rate limiter implementation
├── analytics.py            Hourly order load aggregation and rolling peak-window calculation
├── campus.py               Campus graph definition and Dijkstra shortest-path navigation
├── combo.py                Budget-constrained meal combo knapsack optimizer
├── slots.py                Interval merging and pickup window availability checking
├── static/
│   ├── app.js              Client-side application logic, API calls, and DOM rendering
│   └── style.css           Responsive stylesheet, custom design tokens, and UI components
├── templates/
│   └── index.html          HostelEats single-page application structure and modal dialogs
├── tests/
│   └── test_challenge.py   Six behavioral challenge test suites covering the core modules
└── README.md               Candidate-facing application overview and debugging guide
```

## Bugs and Bug Locations

### 1. Login session never expires (TTL ineffective)

- **Bug location:** `auth.py`, `login` and `get_session`
- **How to observe it:** Log in with demo student credentials (`aarav` / `hostel123`), wait past the configured 30-second TTL, and inspect the session status tooltip in the header.
- **Failure:** Expiration timestamp is calculated in milliseconds while validated against current time in seconds, causing `clock.now_seconds() > session["expires_at"]` to evaluate false perpetually. The user remains logged in indefinitely.
- **Expected:** Sessions expire strictly after the configured TTL (30 seconds), automatically revoking access and prompting the student to sign in again.

### 2. Rate limiter rejected requests extend the lockout window

- **Bug location:** `limiter.py`, `allow_order`
- **How to observe it:** Place 3 rapid pre-orders to exhaust the 3-order quota, then attempt to place a 4th order and wait 30 seconds.
- **Failure:** Rejected order attempts append current timestamps to `ORDER_TIMES` before checking `len(times) > MAX_ORDERS`, locking the user in a continuous penalty window where quota never recovers.
- **Expected:** Rejected requests do not record timestamps, allowing students to place a fresh order as soon as their earliest accepted order expires past the 30-second sliding window.

### 3. Rush hour peak load excludes the final rolling window

- **Bug location:** `analytics.py`, `peak_load`
- **How to observe it:** Navigate to the **Rush Hour** tab with the default 2-hour window.
- **Failure:** An off-by-one loop boundary `range(len(values) - window_size)` skips the final starting index, ignoring the evening rush (6 PM – 7 PM, 58 orders) and reporting an earlier, lower peak (28 orders).
- **Expected:** The rolling window evaluation tests all valid start hours through `len(values) - window_size + 1`, correctly identifying the evening rush (6 PM – 7 PM, 58 orders) as the true peak.

### 4. Campus shortest route evaluates single edge weights instead of accumulated distance

- **Bug location:** `campus.py`, `shortest_route`
- **How to observe it:** Select starting point `Hostel A` and destination `Canteen` on the **Campus Walk** tab, then click **Calculate Quickest Route**.
- **Failure:** Dijkstra relaxation checks single edge weights (`weight < distances[neighbor]`) rather than path sums, producing cyclic loops that fail with "Route unavailable" or report inaccurate walk times.
- **Expected:** The algorithm accumulates path distance (`distance + weight`) to find the true shortest walking path (`Hostel A → Library → Quad → Canteen`, 11 minutes).

### 5. Meal combo builder selects duplicate items

- **Bug location:** `combo.py`, `best_combo`
- **How to observe it:** Enter a budget of `60` in the **Combo Builder** tab and click **Find Optimal Combo**.
- **Failure:** Forward iteration across knapsack capacities allows unbounded item reuse, recommending duplicate items (e.g., 3 Punjabi Samosas) instead of a varied combination.
- **Expected:** Reverse knapsack iteration enforces 0/1 selection, ensuring every recommended menu item in the combo is unique and distinct within the budget.

### 6. Overlapping pickup slots truncate intervals and enable double bookings

- **Bug location:** `slots.py`, `merge_intervals`
- **How to observe it:** Inspect the reserved windows on the **Pickup Slots** tab, then try booking `12:00 PM – 12:30 PM`.
- **Failure:** The merge logic sets `merged[-1][1] = end` directly, shrinking longer existing windows (e.g., 11:30 AM – 12:30 PM cut down to 12:00 PM) and permitting double-bookings on already reserved time slots.
- **Expected:** Overlapping intervals take the furthest end time (`max(merged[-1][1], end)`), preserving the complete reserved span (11:30 AM – 12:30 PM) and rejecting duplicate reservations.

## Expected Behaviour After Fixing All Bugs

- Sessions expire predictably after the configured TTL, ensuring proper student logout.
- Rate-limited users can order again as soon as earlier orders age out of the 30-second window.
- Rush hour analytics reliably identifies the highest-traffic period across all hours.
- Campus walk accurately finds the fastest loop-free route and displays the true walking time.
- Combo builder suggests distinct, varied meal options without duplicate items.
- Pickup slots correctly merge overlapping intervals and block duplicate bookings.
- All 6 tests in `pytest` pass with exit code 0.
