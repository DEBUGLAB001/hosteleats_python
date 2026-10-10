def merge_intervals(intervals):
    ordered = sorted((int(start), int(end)) for start, end in intervals)
    merged = []
    for start, end in ordered:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = end
    return merged


def is_available(start, end, intervals):
    return all(end <= busy_start or start >= busy_end for busy_start, busy_end in merge_intervals(intervals))
