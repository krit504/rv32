"""arch_test.py: riscv-arch-test (rv32i_m/I) on Spike and on the RTL, signatures compared (T1.5).

Usage:   python3 tests/arch_test.py [--list] [test names...]     (env CACHES=1 LAT=n for caches on)
Inputs:  third_party/riscv-arch-test (tag 3.10.0, pinned in docs/TOOLS.md), tests/arch/*.
Method:  each test .S is built twice from the same source with the same flags and linker script,
         once with tests/arch/model_test_spike.h (halts via HTIF) and once with model_test_rtl.h
         (halts via the MMIO HALT register). Both are linked at 0x80000000 and the two headers'
         RVMODEL_HALT have the same instruction count, so every symbol address is identical (this
         script fails the test if not). The Spike ELF runs on Spike (--isa=rv32i, +signature) to
         produce the reference signature; the RTL image runs in tb/tb_arch.sv, which dumps the
         same signature region. The two signatures must be identical, word for word.
         The reference is Spike, never the RTL.
Output:  PASS/FAIL per test; "[arch] n/n passed"; exit 0 only if every included test passes.
         Env ARCH_REPORT=file appends a markdown pass list for this configuration.
Included/excluded: the 37 of 39 rv32i_m/I tests that need no fence, ecall, ebreak, CSR or
         misaligned access; the exclusion list is docs/ARCH_TESTS.md. A test missing from both
         lists is an error.
"""
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from paths import ROOT, CORE_RTL, TB, work_dir

SUITE = os.path.join(ROOT, "third_party", "riscv-arch-test", "riscv-test-suite")
SRC = os.path.join(SUITE, "rv32i_m", "I", "src")
ARCH = os.path.join(ROOT, "tests", "arch")
CACHES = int(os.environ.get("CACHES", "0"))
LAT = int(os.environ.get("LAT", "2"))
GCC = "riscv64-unknown-elf-gcc"
# excluded from the subset, with the reason (also in docs/ARCH_TESTS.md)
EXCLUDED = {
    "fence-01": "uses fence (not implemented)",
    "misalign1-jalr-01": "tests misaligned jump targets (unsupported)",
}
CFLAGS = ["-march=rv32i_zicsr", "-mabi=ilp32", "-static", "-mcmodel=medany", "-fvisibility=hidden",
          "-nostdlib", "-nostartfiles", "-DXLEN=32", "-T", os.path.join(ARCH, "link.ld")]


def all_tests():
    return sorted(f[:-2] for f in os.listdir(SRC) if f.endswith(".S"))


def included():
    names = all_tests()
    unknown = [n for n in EXCLUDED if n not in names]
    assert not unknown, f"excluded tests not found in the suite: {unknown}"
    return [n for n in names if n not in EXCLUDED]


def case_defines(name):
    """-D flags for every `def TEST_CASE_n=True` the source declares in RVTEST_CASE(...).

    The test bodies are inside `#ifdef TEST_CASE_n`; the official flow (riscof) defines them from
    these annotations. Without them nothing is assembled and every test "passes" with an untouched
    signature. A source that declares none is an error."""
    text = open(os.path.join(SRC, name + ".S")).read()
    cases = sorted(set(re.findall(r"def (TEST_CASE_\d+)=True", text)))
    if not cases:
        raise RuntimeError("no TEST_CASE_n declared in the source")
    return [f"-D{c}=True" for c in cases]


def build(name, model, d):
    elf = os.path.join(d, f"{model}.elf")
    inc = ["-I", os.path.join(ARCH, f"model_{model}"), "-I", os.path.join(SUITE, "env")]
    # the model header is selected by include directory: tests/arch/model_spike/model_test.h etc.
    r = subprocess.run([GCC] + CFLAGS + case_defines(name) + inc + [os.path.join(SRC, name + ".S"), "-o", elf],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"build {model} failed: {r.stderr[-400:]}")
    return elf


def symbols(elf):
    out = subprocess.run(["riscv64-unknown-elf-nm", elf], capture_output=True, text=True).stdout
    return {ln.split()[2]: int(ln.split()[0], 16) for ln in out.splitlines() if len(ln.split()) == 3}


def run_one(name):
    d = work_dir(f"arch/{name}_c{CACHES}_l{LAT}")
    try:
        sp, rt = build(name, "spike", d), build(name, "rtl", d)
        ss, sr = symbols(sp), symbols(rt)
        for sym in ("begin_signature", "end_signature", "rvtest_entry_point"):
            if ss[sym] != sr[sym]:
                return name, f"{sym} differs between builds: {ss[sym]:#x} vs {sr[sym]:#x}"
        beg, end = ss["begin_signature"], ss["end_signature"]
        # reference signature from Spike
        sig = os.path.join(d, "spike.sig")
        r = subprocess.run(["spike", "--isa=rv32i", "--priv=m", f"+signature={sig}", "+signature-granularity=4", sp],
                           capture_output=True, text=True, timeout=120)
        if r.returncode or not os.path.exists(sig):
            return name, f"spike failed rc={r.returncode}: {r.stderr[-200:]}"
        ref = [ln.strip() for ln in open(sig) if ln.strip()]
        # vacuity guards: the test must have written its signature (the framework pre-fills it with
        # the canary 0xdeadbeef), and the ELF must contain test code, not just the prologue
        if sum(w != "deadbeef" for w in ref) < max(1, len(ref) // 4):
            return name, f"spike signature is mostly the untouched canary ({sum(w != 'deadbeef' for w in ref)} of {len(ref)} words written): the test body did not run"
        if len(ref) != (end - beg) // 4:
            return name, f"spike signature has {len(ref)} words, expected {(end - beg) // 4}"
        # RTL image: flat binary starting at 0x80000000 -> word 0
        binf, hexf = os.path.join(d, "rtl.bin"), os.path.join(d, "program.hex")
        subprocess.run(["riscv64-unknown-elf-objcopy", "-O", "binary", rt, binf], check=True)
        data = open(binf, "rb").read()
        data += b"\0" * (-len(data) % 4)
        with open(hexf, "w") as f:
            for i in range(0, len(data), 4):
                f.write(f"{int.from_bytes(data[i:i + 4], 'little'):08x}\n")
        # memories sized to the image: next power of two of the word count, at least 256 KiB
        # (jal-01 spans 1.76 MB because it exercises +-1 MiB jump offsets)
        words = len(data) // 4
        memw = max(65536, 1 << (words - 1).bit_length())
        bw, ew = (beg - 0x80000000) >> 2, (end - 0x80000000) >> 2
        r = subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "a.vvp"),
                            f"-Ptb_arch.CACHES={CACHES}", f"-Ptb_arch.LAT={LAT}", f"-Ptb_arch.MEMW={memw}",
                            f"-Ptb_arch.SIG_BEGIN_W={bw}", f"-Ptb_arch.SIG_END_W={ew}"] + CORE_RTL
                           + [os.path.join(TB, "sys_monitor.sv"), os.path.join(TB, "tb_arch.sv")],
                           capture_output=True, text=True)
        if r.returncode:
            return name, "rtl compile failed: " + r.stderr[-300:]
        out = subprocess.run(["vvp", "a.vvp"], cwd=d, capture_output=True, text=True).stdout
        if "TIMEOUT" in out:
            return name, "RTL run timed out"
        got = re.findall(r"^SIG (\w+)$", out, re.M)
        if len(got) != len(ref):
            return name, f"RTL signature has {len(got)} words, expected {len(ref)} (no HALT?)"
        bad = [(i, ref[i], got[i]) for i in range(len(ref)) if ref[i] != got[i]]
        if bad:
            i, a, b = bad[0]
            return name, f"{len(bad)} of {len(ref)} signature words differ; first at word {i}: spike {a} rtl {b}"
        return name, None
    except Exception as e:                      # a crash is a failure, never a pass
        return name, f"error: {type(e).__name__}: {e}"


def main():
    if "--list" in sys.argv:
        print("included:", *included(), sep="\n  ")
        print("excluded:", *[f"{n}  ({w})" for n, w in EXCLUDED.items()], sep="\n  ")
        return 0
    want = [a for a in sys.argv[1:] if not a.startswith("-")] or included()
    with ThreadPoolExecutor(max_workers=int(os.environ.get("JOBS", "8"))) as ex:
        res = list(ex.map(run_one, want))
    fails = 0
    for name, err in res:
        fails += err is not None
        print(("PASS  " if err is None else "FAIL  ") + name + ("" if err is None else f"  <- {err}"))
    print(f"[arch CACHES={CACHES} LAT={LAT}] {len(res) - fails}/{len(res)} passed")
    report = os.environ.get("ARCH_REPORT")
    if report:                                   # pass list for docs/ (T1.5 deliverable)
        with open(report, "a") as f:
            f.write(f"\n## CACHES={CACHES} LAT={LAT}: {len(res) - fails}/{len(res)} passed\n\n| Test | Result |\n|---|---|\n")
            for name, err in res:
                f.write(f"| `{name}` | {'PASS' if err is None else 'FAIL: ' + err} |\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
