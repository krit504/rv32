"""cache_model.py: independent Python model of the D$ (direct-mapped, write-back, write-allocate, with
the restricted-store path of spec Section 4). Also the golden replay of T3.5.

Written from the specification in rtl/dcache.sv's header, not from its logic. It replays a request
stream [(kind, addr, size, bypass)], kind "L" or "S", and reports per-line data-array write counts
and the counters the RTL exposes. It tracks only tags, valid and dirty bits (what the counts
depend on); data correctness is checked separately against a plain byte array.

Counting rules (spec Section 4 definition of an array write: a store hit, a line fill, or a
partial-word merge; reads, write-back reads and metadata are not writes):
  load   hit: hit+1.  miss: miss+1; if the victim is valid and dirty: wb+1; fill+1, one array write
         on the line (refill_after_bypass+1 if the line was last invalidated by a bypass).
  store  (not bypassed) hit: hit+1 and one array write. Miss: miss+1, victim write-back as above,
         fill (one array write), then the store hits (one more array write). The line becomes dirty.
  store  bypassed: bypass+1, never an array write. Line present: if dirty wb+1; the line is
         invalidated (valid, dirty cleared, "bypass-invalidated" set). Absent: nothing in the cache.
  every request: access+1; every store: write+1.
Usage: m = CacheModel(cache_bytes=2048, line_bytes=16); m.replay(ops); m.writes, m.counters
"""


class CacheModel:
    def __init__(self, cache_bytes=2048, line_bytes=16):
        self.line_bytes = line_bytes
        self.lines = cache_bytes // line_bytes
        self.off_bits = line_bytes.bit_length() - 1
        self.idx_bits = self.lines.bit_length() - 1
        self.valid = [False] * self.lines
        self.dirty = [False] * self.lines
        self.tag = [0] * self.lines
        self.byp_inv = [False] * self.lines
        self.writes = [0] * self.lines
        self.c = dict(access=0, hit=0, miss=0, fill=0, wb=0, bypass=0, refill_after_bypass=0, write=0)

    def split(self, addr):
        idx = (addr >> self.off_bits) & (self.lines - 1)
        return idx, addr >> (self.off_bits + self.idx_bits)

    def _fill(self, idx, tag):
        self.c["fill"] += 1
        self.writes[idx] += 1                 # the fill writes the data array once
        if self.byp_inv[idx]:
            self.c["refill_after_bypass"] += 1
            self.byp_inv[idx] = False
        self.valid[idx], self.dirty[idx], self.tag[idx] = True, False, tag

    def _miss_path(self, idx, tag):
        self.c["miss"] += 1
        if self.valid[idx] and self.dirty[idx]:
            self.c["wb"] += 1
        self._fill(idx, tag)

    def op(self, kind, addr, size=4, bypass=False):
        idx, tag = self.split(addr)
        hit = self.valid[idx] and self.tag[idx] == tag
        self.c["access"] += 1
        if kind == "L":
            if hit:
                self.c["hit"] += 1
            else:
                self._miss_path(idx, tag)
        elif bypass:
            self.c["write"] += 1
            self.c["bypass"] += 1
            if hit:
                if self.dirty[idx]:
                    self.c["wb"] += 1
                self.valid[idx], self.dirty[idx], self.byp_inv[idx] = False, False, True
        else:
            self.c["write"] += 1
            if hit:
                self.c["hit"] += 1
            else:
                self._miss_path(idx, tag)
            self.writes[idx] += 1             # the store (merge) writes the array
            self.dirty[idx] = True

    def stall(self, kind, addr, bypass, lat, wl=1):
        """Cycles with dmiss = 1 for this request in the current state, fixed memory latency `lat`, array
        write latency `wl` (each array write adds wl-1 cycles). Derived from the state machine in
        rtl/dcache.sv's header: miss L+2 (clean victim) or 2L+3 (dirty), bypass L+1 or 2L+2 (dirty)."""
        idx, tag = self.split(addr)
        hit = self.valid[idx] and self.tag[idx] == tag
        dirty_victim = self.valid[idx] and self.dirty[idx] and not hit
        if kind == "S" and bypass:
            return 2 * lat + 2 if (hit and self.dirty[idx]) else lat + 1
        writes = 0 if kind == "L" and hit else (1 if kind == "L" else (1 if hit else 2))
        base = 0 if hit else (2 * lat + 3 if dirty_victim else lat + 2)
        return base + (wl - 1) * writes

    def replay(self, ops):
        for o in ops:
            self.op(*o)
        return self

    @property
    def counters(self):
        return dict(self.c)
