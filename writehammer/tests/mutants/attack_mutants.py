"""A D$ mutant that drops stores to program data while preserving stack stores.

This is a negative control for attack C self-checks. It is applied only to a
temporary RTL copy. The RLA/RTA/RnLA/RnTA taxonomy is the author's group's
prior work (TENDRA and the Write Hammer draft).
"""
FILE = "dcache.sv"
OLD = ("            for (int k = 0; k < 4; k++)\n"
       "                if (be[k]) data[index][32 * wsel + 8 * k +: 8] <= wdata[8 * k +: 8];")
NEW = ("            for (int k = 0; k < 4; k++)\n"
       "                if (be[k] && addr >= 32'h0003c000) "
       "data[index][32 * wsel + 8 * k +: 8] <= wdata[8 * k +: 8];")
