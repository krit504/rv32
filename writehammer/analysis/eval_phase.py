"""Derive T6 phase metrics from T5 WGPHASE/WGEND snapshots."""
import re

FIELDS = ("cycle", "restricted_cycles", "stores", "stores_restricted", "restricted_now", "first_restrict_prev_phase")
SENTINEL = 4294967295


def metrics(output, workload_class):
    found = []
    for line in output.splitlines():
        if line.startswith(("WGPHASE ", "WGEND ")):
            values = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", line)}
            if not set(FIELDS) <= values.keys():
                raise ValueError(f"incomplete phase snapshot: {line}")
            found.append(values)
    if not found or "id" in found[-1] or sum("id" not in s for s in found) != 1:
        raise ValueError("expected one final WGEND snapshot")
    start = {key: 0 for key in FIELDS}
    intervals = []
    previous = start
    for end in found:
        for key in ("cycle", "restricted_cycles", "stores", "stores_restricted"):
            if end[key] < previous[key]:
                raise ValueError(f"decreasing {key} in phase snapshots")
        if end["restricted_cycles"] - previous["restricted_cycles"] > end["cycle"] - previous["cycle"]:
            raise ValueError("restricted cycles exceed interval cycles")
        if end["stores_restricted"] - previous["stores_restricted"] > end["stores"] - previous["stores"]:
            raise ValueError("restricted stores exceed interval stores")
        intervals.append((previous, end))
        previous = end
    ids = [s.get("id") for s in found]
    if workload_class == "mixed":
        if ids != [0, 1, 2, 3, None]:
            raise ValueError(f"unexpected mixed markers {ids}")
        benign, attack = [intervals[1], intervals[3]], intervals[2]
    elif workload_class == "attack":
        if ids != [1, 2, None]:
            raise ValueError(f"unexpected attack markers {ids}")
        benign, attack = [], intervals[1]
    else:
        if ids != [None]:
            raise ValueError(f"unexpected benign markers {ids}")
        benign, attack = intervals, None
    benign_cycles = sum(b["cycle"] - a["cycle"] for a, b in benign)
    benign_restricted_cycles = sum(b["restricted_cycles"] - a["restricted_cycles"] for a, b in benign)
    benign_stores = sum(b["stores"] - a["stores"] for a, b in benign)
    benign_restricted_stores = sum(b["stores_restricted"] - a["stores_restricted"] for a, b in benign)
    end = found[-1]
    result = {
        "restricted_cycle_frac": end["restricted_cycles"] / end["cycle"] if end["cycle"] else 0,
        "fp_cycle_frac": benign_restricted_cycles / benign_cycles if benign_cycles else "",
        "fp_store_frac": benign_restricted_stores / benign_stores if benign_stores else "",
        "detect_latency_cycles": "",
        "_carry_over": False,
    }
    if attack:
        begin, finish = attack
        first = finish["first_restrict_prev_phase"]
        if begin["restricted_now"]:
            result["detect_latency_cycles"] = 0
            result["_carry_over"] = True
        elif first != SENTINEL:
            if not begin["cycle"] <= first <= finish["cycle"]:
                raise ValueError("first restriction outside attack interval")
            result["detect_latency_cycles"] = first - begin["cycle"]
    return result
