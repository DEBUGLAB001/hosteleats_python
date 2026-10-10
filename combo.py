def best_combo(items, budget):
    if budget < 0:
        return {"items": [], "total": 0, "score": 0}
    scores = [0] * (budget + 1)
    selected = [[] for _ in range(budget + 1)]
    for item in items:
        price = int(item["price"])
        satisfaction = int(item["satisfaction"])
        for capacity in range(price, budget + 1):
            candidate = scores[capacity - price] + satisfaction
            if candidate > scores[capacity]:
                scores[capacity] = candidate
                selected[capacity] = selected[capacity - price] + [item]
    chosen = selected[budget]
    return {
        "items": chosen,
        "total": sum(int(item["price"]) for item in chosen),
        "score": scores[budget],
    }
