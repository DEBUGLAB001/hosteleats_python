import clock

MENU = [
    {"id": "masala-dosa", "name": "Masala Dosa", "category": "South Indian", "price": 65, "satisfaction": 9, "description": "Crisp dosa, potato masala, coconut chutney", "emoji": "🥞", "popular": True},
    {"id": "samosa", "name": "Punjabi Samosa", "category": "Snacks", "price": 20, "satisfaction": 4, "description": "Two golden pastries with mint chutney", "emoji": "🥟", "popular": True},
    {"id": "masala-chai", "name": "Masala Chai", "category": "Drinks", "price": 15, "satisfaction": 3, "description": "Ginger, cardamom, and a little comfort", "emoji": "☕", "popular": False},
    {"id": "fruit-cup", "name": "Seasonal Fruit Cup", "category": "Fresh", "price": 30, "satisfaction": 5, "description": "Fresh-cut fruit, chilled and ready", "emoji": "🍉", "popular": False},
    {"id": "paneer-roll", "name": "Paneer Tikka Roll", "category": "Wraps", "price": 55, "satisfaction": 8, "description": "Smoky paneer, crunchy onions, green chutney", "emoji": "🌯", "popular": True},
    {"id": "lemon-rice", "name": "Lemon Rice Bowl", "category": "Meals", "price": 45, "satisfaction": 7, "description": "Tempered rice with peanuts and a pickle", "emoji": "🍚", "popular": False},
    {"id": "filter-coffee", "name": "Filter Coffee", "category": "Drinks", "price": 20, "satisfaction": 4, "description": "Strong, smooth, poured fresh", "emoji": "🥤", "popular": False},
]

ORDERS = [
    {"id": "HE-2401", "user_id": "aarav", "student": "Aarav Mehta", "items": [{"name": "Paneer Tikka Roll", "quantity": 1}], "total": 55, "pickup_at": "12:30 PM", "status": "Preparing", "created_at": clock.now_seconds() - 180},
    {"id": "HE-2402", "user_id": "aarav", "student": "Aarav Mehta", "items": [{"name": "Masala Chai", "quantity": 1}, {"name": "Punjabi Samosa", "quantity": 1}], "total": 35, "pickup_at": "12:45 PM", "status": "Ready", "created_at": clock.now_seconds() - 420},
    {"id": "HE-2403", "user_id": "canteen", "student": "Mira Shah", "items": [{"name": "Masala Dosa", "quantity": 1}], "total": 65, "pickup_at": "12:30 PM", "status": "Queued", "created_at": clock.now_seconds() - 90},
]

BOOKED_SLOTS = [[690, 750], [705, 720], [810, 840]]
HOURLY_ORDER_COUNTS = [2, 4, 7, 5, 8, 6, 11, 9, 12, 8, 20, 38]
HOUR_LABELS = ["8 AM", "9 AM", "10 AM", "11 AM", "12 PM", "1 PM", "2 PM", "3 PM", "4 PM", "5 PM", "6 PM", "7 PM"]


def reset_data():
    ORDERS[:] = [
        {"id": "HE-2401", "user_id": "aarav", "student": "Aarav Mehta", "items": [{"name": "Paneer Tikka Roll", "quantity": 1}], "total": 55, "pickup_at": "12:30 PM", "status": "Preparing", "created_at": clock.now_seconds() - 180},
        {"id": "HE-2402", "user_id": "aarav", "student": "Aarav Mehta", "items": [{"name": "Masala Chai", "quantity": 1}, {"name": "Punjabi Samosa", "quantity": 1}], "total": 35, "pickup_at": "12:45 PM", "status": "Ready", "created_at": clock.now_seconds() - 420},
        {"id": "HE-2403", "user_id": "canteen", "student": "Mira Shah", "items": [{"name": "Masala Dosa", "quantity": 1}], "total": 65, "pickup_at": "12:30 PM", "status": "Queued", "created_at": clock.now_seconds() - 90},
    ]
    BOOKED_SLOTS[:] = [[690, 750], [705, 720], [810, 840]]
