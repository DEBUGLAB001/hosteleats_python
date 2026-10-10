def peak_load(counts, window_size):
    values = list(counts)
    if window_size <= 0 or window_size > len(values):
        return {"start": None, "end": None, "total": 0}
    best_start = 0
    best_total = -1
    for start in range(len(values) - window_size):
        total = sum(values[start:start + window_size])
        if total > best_total:
            best_start = start
            best_total = total
    return {"start": best_start, "end": best_start + window_size, "total": best_total}
