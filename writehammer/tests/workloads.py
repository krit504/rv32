"""workloads.py: the benign workload registry (locked; spec Section 3 and DEC-008).

CALIBRATION is the only set thresholds may be calibrated on (spec Section 3: Dhrystone, CoreMark).
HELD_OUT is the false-positive set (Embench-IoT subset of 8 chosen by the rule in DEC-008, plus
memcpy and memset on buffers larger than the cache, and a store-heavy loop).
Each entry: name -> how to build it. kind "embench": sw/embench/build_embench.py KERNEL OUT;
"workload": sw/workloads/build_workload.py NAME OUT; "dhrystone"/"coremark": their build scripts.
Adding workloads is allowed; removing or reordering is not (spec 0A.A).
"""
CALIBRATION = [("dhrystone", "dhrystone", 500), ("coremark", "coremark", 10)]
HELD_OUT = [
    ("crc32", "embench", "crc32"),
    ("md5sum", "embench", "md5sum"),
    ("nettle-sha256", "embench", "nettle-sha256"),
    ("nettle-aes", "embench", "nettle-aes"),
    ("huffbench", "embench", "huffbench"),
    ("wikisort", "embench", "wikisort"),
    ("sglib-combined", "embench", "sglib-combined"),
    ("qrduino", "embench", "qrduino"),
    ("memcpy_big", "workload", "memcpy_big"),
    ("memset_big", "workload", "memset_big"),
    ("storeloop", "workload", "storeloop"),
]
