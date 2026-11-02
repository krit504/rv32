"""build.py: build a bare-metal RV32I program into a $readmemh image (T1.4).

Usage:   python3 sw/build.py OUT_DIR SOURCE.c [SOURCE.c|.S ...]
Inputs:  C or assembly sources. crt0.S and link.ld from sw/ are added automatically.
Outputs: OUT_DIR/prog.elf, prog.bin, prog.map, program.hex (one 32-bit little-endian word per
         line, word 0 = address 0; the memories zero-fill everything past the image),
         prog.dis (disassembly).
Flags:   -march=rv32i_zicsr -mabi=ilp32 -O2 -ffreestanding -nostdlib -static -Wl,--gc-sections.
         Why not plain -march=rv32i: this GCC has no rv32i multilib, so it silently falls back to
         the default multilib and `-lgcc` would link an rv64 libgcc (checked with
         -print-libgcc-file-name). rv32i_zicsr/ilp32 is the closest rv32 multilib; its libgcc is
         RV32I-only for the multiply/divide helpers. The compiler emits no CSR instructions unless
         source asks for them.
Check:   after linking, every instruction in the ELF must be an RV32I base instruction (checked
         with objdump -M no-aliases against the full RV32I list); anything else (mul, csr, fence,
         ecall, compressed, ...) fails the build, as does a non-rv32i architecture attribute.
Env:     RISCV_GCC (default riscv64-unknown-elf-gcc), CFLAGS_EXTRA, LDLIBS_EXTRA (e.g. "-lc": linked inside a
         linker group with libgcc; the newlib libc of the rv32i_zicsr multilib is RV32I-only too, and the
         ELF check below still applies to everything that gets linked).
Exit 0 on success.
"""
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GCC = os.environ.get("RISCV_GCC", "riscv64-unknown-elf-gcc")
PREFIX = GCC[:-3]          # riscv64-unknown-elf-
CFLAGS = ["-march=rv32i_zicsr", "-mabi=ilp32", "-O2", "-ffreestanding", "-nostdlib", "-static",
          "-fno-pic", "-ffunction-sections", "-fdata-sections", "-Wall", "-Wextra"] \
    + os.environ.get("CFLAGS_EXTRA", "").split()

RV32I = set("""lui auipc jal jalr beq bne blt bge bltu bgeu lb lh lw lbu lhu sb sh sw addi slti sltiu
xori ori andi slli srli srai add sub sll slt sltu xor srl sra or and""".split())


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f"build.py: command failed: {' '.join(cmd)}\n{r.stdout}{r.stderr}")
    return r.stdout


def check_isa(elf):
    arch = run([PREFIX + "readelf", "-A", elf])
    m = re.search(r'Tag_RISCV_arch: "([^"]+)"', arch)
    if not m or not m.group(1).startswith("rv32i") or re.search(r"_[mac]\d", m.group(1)):
        sys.exit(f"build.py: ELF architecture is {m.group(1) if m else 'unknown'}, expected rv32i (+zicsr only)")
    bad = {}
    for ln in run([PREFIX + "objdump", "-d", "-M", "no-aliases", elf]).splitlines():
        m = re.match(r"\s+[0-9a-f]+:\s+([0-9a-f]+)\s+(\S+)", ln)
        if m and m.group(2) not in RV32I:
            if m.group(2).startswith("."):
                continue                      # data words objdump decodes as .word / .insn
            bad[m.group(2)] = bad.get(m.group(2), 0) + 1
    if bad:
        sys.exit(f"build.py: non-RV32I instructions in {elf}: {bad}")


def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    out, srcs = argv[1], argv[2:]
    os.makedirs(out, exist_ok=True)
    elf = os.path.join(out, "prog.elf")
    run([GCC] + CFLAGS + ["-T", os.path.join(HERE, "link.ld"), "-Wl,--gc-sections",
                          f"-Wl,-Map={os.path.join(out, 'prog.map')}",
                          os.path.join(HERE, "crt0.S")] + srcs
        + (["-Wl,--start-group"] + os.environ["LDLIBS_EXTRA"].split() + ["-lgcc", "-Wl,--end-group"]
           if os.environ.get("LDLIBS_EXTRA") else ["-lgcc"]) + ["-o", elf])
    check_isa(elf)
    binf = os.path.join(out, "prog.bin")
    run([PREFIX + "objcopy", "-O", "binary", elf, binf])
    data = open(binf, "rb").read()
    data += b"\0" * (-len(data) % 4)
    with open(os.path.join(out, "program.hex"), "w") as f:
        for (w,) in struct.iter_unpack("<I", data):
            f.write(f"{w:08x}\n")
    with open(os.path.join(out, "prog.dis"), "w") as f:
        f.write(run([PREFIX + "objdump", "-d", elf]))
    print(f"build.py: {elf} ok, {len(data) // 4} words")


if __name__ == "__main__":
    main(sys.argv)
