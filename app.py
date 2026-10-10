import datetime
import secrets

from flask import Flask, jsonify, render_template, request

import analytics
import auth
import campus
import clock
import combo
import data
import limiter
import slots

app = Flask(__name__, static_folder="static", template_folder="templates")

BOOT_ID = secrets.token_hex(8)
BOOT_TIME = datetime.datetime.now().strftime("%H:%M:%S")


class PreviewPrefixMiddleware:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        marker = "/preview/"
        if path.startswith("/runtime/") and marker in path:
            prefix, remainder = path.split(marker, 1)
            environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + prefix + "/preview"
            environ["PATH_INFO"] = "/" + remainder
        return self.wrapped(environ, start_response)


app.wsgi_app = PreviewPrefixMiddleware(app.wsgi_app)


@app.after_request
def add_no_store(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def json_error(message, status):
    return jsonify({"error": message}), status


def current_session():
    header = request.headers.get("Authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    return auth.get_session(token)


def require_user(roles=None):
    session = current_session()
    if session is None:
        return None, json_error("Please sign in to continue", 401)
    if roles and session["role"] not in roles:
        return None, json_error("Your account cannot perform this action", 403)
    return session, None


def minutes_text(value):
    hour, minute = divmod(int(value), 60)
    suffix = "AM" if hour < 12 else "PM"
    shown_hour = hour % 12 or 12
    return f"{shown_hour}:{minute:02d} {suffix}"


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def api_health():
    return jsonify({"boot_id": BOOT_ID, "started_at": BOOT_TIME})


@app.post("/api/login")
def api_login():
    payload = request.get_json(silent=True) or {}
    result = auth.login(payload.get("username"), payload.get("password"))
    if result is None:
        return json_error("Check your username and password", 401)
    return jsonify(result)


@app.get("/api/auth/session")
def api_auth_session():
    session = current_session()
    if session is None:
        return json_error("Session expired or invalid", 401)
    remaining = max(0, int(session["expires_at"] - clock.now_seconds()))
    return jsonify({"session": session, "expires_in": remaining})


@app.get("/api/menu")
def api_menu():
    return jsonify({"items": data.MENU})


@app.get("/api/limiter/status")
def api_limiter_status():
    user_id = request.args.get("user_id", "aarav")
    now = clock.now_seconds()
    times = [stamp for stamp in limiter.ORDER_TIMES.get(user_id, []) if now - stamp < limiter.WINDOW_SECONDS]
    available = max(0, limiter.MAX_ORDERS - len(times))
    return jsonify({
        "user_id": user_id,
        "active_window_seconds": limiter.WINDOW_SECONDS,
        "max_orders": limiter.MAX_ORDERS,
        "orders_in_window": len(times),
        "available": available,
        "can_order": len(times) < limiter.MAX_ORDERS,
    })


@app.post("/api/orders")
def api_create_order():
    session, error = require_user(["student"])
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    requested = payload.get("items")
    pickup_at = str(payload.get("pickup_at", ""))
    if not isinstance(requested, list) or not requested or len(requested) > 10:
        return json_error("Choose at least one menu item", 400)
    if pickup_at not in {"12:30 PM", "12:45 PM", "1:00 PM", "1:15 PM", "1:30 PM"}:
        return json_error("Choose an available pickup time", 400)
    menu_by_id = {item["id"]: item for item in data.MENU}
    normalized = {}
    for row in requested:
        if not isinstance(row, dict) or row.get("item_id") not in menu_by_id:
            return json_error("One of the selected items is unavailable", 400)
        quantity = row.get("quantity")
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 10:
            return json_error("Item quantities must be between 1 and 10", 400)
        normalized[row["item_id"]] = normalized.get(row["item_id"], 0) + quantity
        if normalized[row["item_id"]] > 10:
            return json_error("Item quantities must be between 1 and 10", 400)
    if not limiter.allow_order(session["username"]):
        return json_error("Order limit reached. Try again in a little while.", 429)
    lines = [{"name": menu_by_id[item_id]["name"], "quantity": quantity} for item_id, quantity in normalized.items()]
    total = sum(menu_by_id[item_id]["price"] * quantity for item_id, quantity in normalized.items())
    order = {
        "id": f"HE-{secrets.randbelow(9000) + 1000}",
        "user_id": session["username"],
        "student": session["name"],
        "items": lines,
        "total": total,
        "pickup_at": pickup_at,
        "status": "Queued",
        "created_at": clock.now_seconds(),
    }
    data.ORDERS.insert(0, order)
    return jsonify({"order": order}), 201


@app.get("/api/orders/mine")
def api_my_orders():
    session, error = require_user()
    if error:
        return error
    page = request.args.get("page", default=1, type=int)
    if page < 1:
        return json_error("Page must be positive", 400)
    mine = [order for order in data.ORDERS if order["user_id"] == session["username"]]
    start = (page - 1) * 20
    return jsonify({"orders": mine[start:start + 20], "page": page, "has_more": start + 20 < len(mine)})


@app.get("/api/combo")
def api_combo():
    budget = request.args.get("budget", default=60, type=int)
    if budget < 0 or budget > 1000:
        return json_error("Budget must be between ₹0 and ₹1,000", 400)
    return jsonify(combo.best_combo(data.MENU, budget))


@app.get("/api/slots/busy")
def api_busy_slots():
    merged = slots.merge_intervals(data.BOOKED_SLOTS)
    return jsonify({"slots": [{"start": start, "end": end, "start_label": minutes_text(start), "end_label": minutes_text(end)} for start, end in merged]})


@app.post("/api/slots")
def api_book_slot():
    session, error = require_user(["student"])
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    try:
        start, end = int(payload.get("start")), int(payload.get("end"))
    except (TypeError, ValueError):
        return json_error("Choose a valid pickup range", 400)
    if start < 8 * 60 or end > 21 * 60 or end <= start or end - start > 60:
        return json_error("Pickup ranges must be 1 to 60 minutes between 8 AM and 9 PM", 400)
    if not slots.is_available(start, end, data.BOOKED_SLOTS):
        return json_error("That pickup time is already booked", 409)
    data.BOOKED_SLOTS.append([start, end])
    return jsonify({"ok": True, "message": f"Pickup booked for {minutes_text(start)}–{minutes_text(end)}", "student": session["name"]}), 201


@app.get("/api/analytics/peak-load")
def api_peak_load():
    window = request.args.get("window", default=2, type=int)
    if window < 1 or window > 6:
        return json_error("Window must be between 1 and 6 hours", 400)
    peak = analytics.peak_load(data.HOURLY_ORDER_COUNTS, window)
    peak["start_label"] = data.HOUR_LABELS[peak["start"]] if peak["start"] is not None else None
    peak["end_label"] = data.HOUR_LABELS[peak["end"] - 1] if peak["end"] is not None else None
    peak["counts"] = data.HOURLY_ORDER_COUNTS
    peak["labels"] = data.HOUR_LABELS
    return jsonify(peak)


@app.get("/api/campus/route")
def api_campus_route():
    source = request.args.get("from", "Hostel A")
    target = request.args.get("to", "Canteen")
    route = campus.shortest_route(campus.CAMPUS_GRAPH, source, target)
    if route is None:
        return json_error("Choose two connected campus locations", 400)
    return jsonify(route)


@app.get("/api/kitchen/queue")
def api_kitchen_queue():
    session, error = require_user(["staff"])
    if error:
        return error
    queue = [order for order in data.ORDERS if order["status"] != "Ready"]
    return jsonify({"orders": queue, "staff": session["name"]})


@app.post("/api/kitchen/ready")
def api_mark_ready():
    _, error = require_user(["staff"])
    if error:
        return error
    payload = request.get_json(silent=True) or {}
    order_id = str(payload.get("order_id", ""))
    order = next((row for row in data.ORDERS if row["id"] == order_id), None)
    if order is None:
        return json_error("Order was not found", 404)
    order["status"] = "Ready"
    order["ready_at"] = clock.now_seconds()
    return jsonify({"ok": True, "order": order})


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return json_error("API route not found", 404)
    return render_template("index.html")


@app.errorhandler(405)
def method_not_allowed(_error):
    return json_error("Method not allowed", 405)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
