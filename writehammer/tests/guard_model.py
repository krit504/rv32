"""guard_model.py: independent cycle-accurate Python model of rtl/write_guard.sv (spec T5.7 cross-check).

Written from the documented behaviour (header of write_guard.sv, DEC-011), not from the RTL source.
step() takes one cycle's inputs and returns the outputs the RTL shows in that cycle (before the clock edge).
"""
SAT_DEFAULT = 16


def bucket(idx, m):
    f = (idx & 0xFF) ^ ((idx >> 8) & 0xFF)
    p = (f * 167) & 0xFF
    logm = m.bit_length() - 1
    return p >> (8 - logm) if logm else 0


class Guard:
    def __init__(self, det, mode=0, window=100, thr=10, m=16, w=16, lines=128, rate=0, seed=1):
        self.det, self.mode, self.window, self.thr, self.m, self.w, self.lines = det, mode, window, thr, m, w, lines
        self.half = thr // 2
        self.sat = (1 << w) - 1
        n = lines if det == 2 else m if det == 3 else 1
        self.cnt = [0] * n
        self.hot = [False] * n
        self.wtimer = 0
        self.rate = rate
        self.rng = seed if seed else 1
        self.flag = False          # PLACEBO
        self.cyc = 0
        self.cr = 0
        self.first = 0xFFFFFFFF
        self.stores = 0
        self.stores_r = 0

    def _idx(self, line):
        line &= self.lines - 1
        return line if self.det == 2 else bucket(line, self.m)

    def _hot_store(self, sline):
        d = self.det
        if d in (0, 5):
            return False
        if d == 1:
            return True
        if d in (2, 3):
            return self.hot[self._idx(sline)]
        if d == 4:
            return self.hot[0]
        return self.flag

    def _any_hot(self):
        d = self.det
        if d in (0, 5):
            return False
        if d == 1:
            return True
        if d == 6:
            return self.flag
        return any(self.hot)

    def step(self, sv, busy, awv, lidx, sline):
        byp = sv and self._hot_store(sline)
        restr = self._any_hot()
        out = (int(byp), int(restr), self.cr, self.first, self.stores, self.stores_r)
        freeze = sv and busy
        done = sv and not busy
        # observation counters
        if restr:
            self.cr += 1
            if self.first == 0xFFFFFFFF:
                self.first = self.cyc
        if done:
            self.stores += 1
            if byp:
                self.stores_r += 1
        self.cyc += 1
        win_proc = self.wtimer >= self.window - 1 and not freeze
        if win_proc:
            self.wtimer = 0
        elif self.wtimer < self.window - 1:
            self.wtimer += 1
        d = self.det
        if d in (2, 3, 4):
            for i in range(len(self.cnt)):
                if d == 4:
                    inc = done
                else:
                    inc = awv and self._idx(lidx) == i
                cn = min(self.cnt[i] + 1, self.sat) if inc else self.cnt[i]
                if win_proc:
                    self.cnt[i] = 0
                    if cn > self.thr:
                        self.hot[i] = True
                    elif cn < self.half and (d != 4 or self.mode == 1):
                        self.hot[i] = False
                else:
                    self.cnt[i] = cn
                    if not freeze and cn > self.thr:
                        self.hot[i] = True
        elif d == 6 and done:
            x = self.rng
            x ^= (x << 13) & 0xFFFFFFFF
            x ^= x >> 17
            x ^= (x << 5) & 0xFFFFFFFF
            self.rng = x
            self.flag = (x & 0xFFFF) < self.rate
        return out
