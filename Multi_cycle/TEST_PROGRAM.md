# Full-ISA Integration Test — Instruction Reference

**Authority.** The program is [program.hex](program.hex), loaded by `imem` ([imem.sv:10](imem.sv#L10)) via `$readmemh`. Expected values are asserted register-by-register in [tb_rv32i_single_cycle.sv](tb_rv32i_single_cycle.sv). Control signal tables are `main_decoder.sv`/`alu_decoder.sv`, matching the spec in `RV32I Single-Cycle Core 2 — Spec Sheet (Remaining Instructions).md` and the worked examples in `RV32I remaining instructions.md`. This document explains *why* each instruction was chosen and which specific piece of hardware its result depends on — not just what the ISA defines.

## Word Layout by Format

Every instruction is one 32-bit word. `opcode[6:0]` is always the low 7 bits and always selects the format:

| Format | Bit 31 | 30:25 | 24:21 | 20 | 19:15 | 14:12 | 11:8 | 7 | 6:0 |
|---|---|---|---|---|---|---|---|---|---|
| R | funct7[6] | funct7[5:0] | rs2 | | rs1 | funct3 | rd | | opcode |
| I | imm[11] | imm[10:5] | imm[4:1] | imm[0] | rs1 | funct3 | rd | | opcode |
| S | imm[11] | imm[10:5] | rs2 | | rs1 | funct3 | imm[4:1] | imm[0] | opcode |
| B | imm[12] | imm[10:5] | rs2 | | rs1 | funct3 | imm[4:1] | imm[11] | opcode |
| U | imm[31:12] (placed directly in bits 31:12) | | | | | | | | opcode |
| J | imm[20] | imm[10:5] | imm[4:1] | imm[11] | imm[19:15] | imm[14:12] | imm[11:8] | imm[7] | opcode |

(J's field layout above is written in raw bit-slice order to line up with the table; see `immediate_generator.sv`'s own reassembly comment for the local-index version actually implemented.)

**Why B/J scramble their immediate bits instead of laying them out contiguously:** bit position 7 of a B-type word is also bit position 7 of an S-type word (both are the low immediate chunk `imm[4:1]/imm[0]`) and bits 31:25 are the same slot in R/I/S/B alike (`funct7`/`imm[11:5]`). The encoding is designed so `rs1`, `rs2`, and `funct3` sit in the exact same bit positions across every format that uses them — the decoder never needs to know the format before it can find `rs1`. Only the immediate bits move around, because those are the only fields that differ in count and meaning between formats.

**Opcodes used in this program:**

| Opcode (bin) | Format | Instructions |
|---|---|---|
| `0110011` | R | `sll`, `xor`, `srl`, `sra`, `slt`, `sltu` |
| `0010011` | I | `slli`, `xori`, `ori`, `andi`, `srli`, `srai`, `slti`, `sltiu`, `addi` |
| `0000011` | I | `lw` |
| `0100011` | S | `sw` |
| `1100011` | B | `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu` |
| `1101111` | J | `jal` |
| `1100111` | I | `jalr` |
| `0110111` | U | `lui` |
| `0010111` | U | `auipc` |

## Register Map

Every register below is written exactly once by a single instruction and never touched again, **except** `x30` and `x31`, which are each written twice by design — a deliberate two-step proof chain, not an accidental overwrite (see their rows). This is what makes every check in `tb_rv32i_single_cycle.sv` a check on *that specific instruction's* result, not on whatever a later instruction happened to leave behind — the exact mistake the earlier 4-instruction integration test made with `x9`.

| Reg | Addr | Instruction word | Decoded | Value | Datapath actually being proven |
|---|---|---|---|---|---|
| x1 | `0x000` | `00600093` | `addi x1,x0,6` | `6` | base operand; also gives every later R-type test a nonzero, non-x0 register source |
| x2 | `0x004` | `00200113` | `addi x2,x0,2` | `2` | base operand |
| x3 | `0x008` | `002091b3` | `sll x3,x1,x2` | `0x18` | `ALUControl=0110`; `SrcB[4:0]` read as shift amount from a register, not an immediate |
| x4 | `0x00c` | `0020c233` | `xor x4,x1,x2` | `0x4` | `ALUControl=1000`, the one new R-type op with no shift/compare shape to accidentally reuse |
| x5 | `0x010` | `00309293` | `slli x5,x1,3` | `0x30` | I-type shift: the 5-bit `shamt` field lives inside what `imm_gen` treats as an ordinary I-immediate — `imm_gen` needs no shift-specific logic (§2 of the remaining-instructions doc) |
| x6 | `0x014` | `0030c313` | `xori x6,x1,3` | `0x5` | I-type ALU immediate path (`ALUSrc=1`, `ALUOp=10`, `funct3=100`) |
| x7 | `0x018` | `0080e393` | `ori x7,x1,8` | `0xe` | `funct3=110` |
| x8 | `0x01c` | `0030f413` | `andi x8,x1,3` | `0x2` | `funct3=111` |
| x9 | `0x020` | `ff000493` | `addi x9,x0,-16` | `0xFFFFFFF0` | negative base operand — everything below that needs sign-fill behavior reads this register |
| x10 | `0x024` | `00400513` | `addi x10,x0,4` | `4` | shift-amount operand, register-sourced (R-type shifts can't take an immediate shift amount) |
| x11 | `0x028` | `00a4d5b3` | `srl x11,x9,x10` | `0x0FFFFFFF` | `ALUControl=0111`, logical right shift, zero-fill |
| x12 | `0x02c` | `40a4d633` | `sra x12,x9,x10` | `0xFFFFFFFF` | `ALUControl=1001`, arithmetic right shift — **same `SrcA`/shift-amount as x11; the fill bit is the only thing that can differ, so x11≠x12 is a direct proof `>>>` is wired, not `>>`** ([ALU.sv:38](ALU.sv#L38)) |
| x13 | `0x030` | `0044d693` | `srli x13,x9,4` | `0x0FFFFFFF` | I-type logical shift — same operand and shift amount as x11 by construction, must match it exactly |
| x14 | `0x034` | `4044d713` | `srai x14,x9,4` | `0xFFFFFFFF` | I-type arithmetic shift — must match x12; the `Instr[30]` tie-break here is read **unconditionally**, unlike `funct3=000`'s `{op5,funct7_5}` gating (`alu_decoder.sv`, `ALUOp=10`, `funct3=101` row) |
| x15 | `0x038` | `fff00793` | `addi x15,x0,-1` | `0xFFFFFFFF` | base operand for the signed/unsigned comparison pair |
| x16 | `0x03c` | `00100813` | `addi x16,x0,1` | `1` | base operand |
| x17 | `0x040` | `0107a8b3` | `slt x17,x15,x16` | `1` | `ALUControl=0101`; `$signed(-1) < $signed(1)` → true |
| x18 | `0x044` | `0107b933` | `sltu x18,x15,x16` | `0` | `ALUControl=0100`; unsigned `0xFFFFFFFF < 1` → false — **same operands as x17, opposite result, proves the ALU has two genuinely different comparison paths** |
| x19 | `0x048` | `0017a993` | `slti x19,x15,1` | `1` | I-type mirror of x17 |
| x20 | `0x04c` | `0017ba13` | `sltiu x20,x15,1` | `0` | I-type mirror of x18 |
| x22 | `0x05c`/`0x054` | branch scaffold | `beq x1,x1` | `1` | equal operands → `Zero=1` → taken |
| x23 | `0x06c`/`0x064` | branch scaffold | `bne x1,x1` | `0` | same operands as x22, opposite polarity requirement → not taken |
| x24 | `0x07c`/`0x074` | branch scaffold | `blt x9,x16` | `1` | `-16 < 1` signed → `ALUResult0=1` → taken |
| x25 | `0x08c`/`0x084` | branch scaffold | `bge x9,x16` | `0` | same operands as x24, opposite condition → not taken |
| x26 | `0x09c`/`0x094` | branch scaffold | `bltu x9,x16` | `0` | same bit pattern as x24/x25, reinterpreted unsigned: `0xFFFFFFF0 < 1` → false → not taken |
| x27 | `0x0ac`/`0x0a4` | branch scaffold | `bgeu x9,x16` | `1` | same operands as x26, opposite condition → taken |
| x28 | `0x0b4` | `0080ae03` | `lw x28,8(x1)` | `0xFFFFFFF0` | `ResultSrc=01`; round-trips the value `sw` stored below |
| x29 | `0x0b8` | `12345eb7` | `lui x29,0x12345` | `0x12345000` | `ResultSrc=10`; `ImmExt` written straight to `rd`, ALU never involved |
| x30 | `0x0bc`,`0x0c0` | `00001f17`,`234f0f13` | `auipc x30,1` then `addi x30,x30,0x234` | `0x000012F0` | `ALUSrcA=1` selects `PC` (not `RD1`) for the first `auipc`; the immediate `addi` on top proves the 2-instruction PC-relative idiom actually composes |
| x21 | `0x0c4` | `00c00aef` | `jal x21,+12` | `0x000000C8` | `ResultSrc=11`; return address is `PCPlus4` of the `jal` itself, not of wherever it jumps to |
| x31 | `0x0d0`,`0x0c8` | `06400f93`,`001f8f93` | `addi x31,x0,100` (subroutine) then `addi x31,x31,1` (after `jalr` return) | `101` | only reaches `101` if the subroutine actually executed *and* `jalr` landed exactly back at the return point |

`dmem` word index `3` also independently holds `0xFFFFFFF0` (see `sw`, below) — checked directly against memory, not only through `x28`.

## Per-Instruction Bit Breakdown

Two representative decodes, chosen because they exercise the two newest and easiest-to-miswire pieces of hardware in this revision: the `sra`/`srai` sign-fill and the `jalr` bit-0 clear.

### `sra x12,x9,x10` — `0x40a4d633`

```
0100000 01010 01001 101 01100 0110011
funct7  rs2   rs1   f3  rd    opcode
```

| Field | Bits | Value | Meaning |
|---|---|---|---|
| `opcode` | `[6:0]` | `0110011` | R-type |
| `rd` | `[11:7]` | `01100` = x12 | destination |
| `funct3` | `[14:12]` | `101` | shift-right family (`srl`/`sra`) |
| `rs1` | `[19:15]` | `01001` = x9 | value being shifted |
| `rs2` | `[24:20]` | `01010` = x10 | shift amount source — only `rs2[4:0]` is read by the ALU |
| `funct7` | `[31:25]` | `0100000` | bit 30 (`funct7[5]`) = `1` selects arithmetic (sign-fill); `0` at this position would select `srl` instead — this single bit is the entire distinction between the two instructions |

`alu_decoder` reads `funct3=101` and `funct7_5=1` and outputs `ALUControl=1001`. The ALU's `else` branch (`ALU.sv:37-38`) then performs `$signed(SrcA) >>> $signed(SrcB[4:0])` — sign-extending because `>>>` on a signed operand fills with the MSB, not zero. Flip `funct7[5]` to `0` and the *only* thing that changes anywhere in this pipeline is `ALUControl`'s low bit (`1001`→`0111`), which routes to `ALU.sv:31-32`'s `SrcA>>SrcB[4:0]` — plain zero-fill. That's the whole reason `x11` (`srl`) and `x12` (`sra`) must differ: everything upstream of `ALUControl` is identical for both instructions.

### `jalr x0,0(x21)` — `0x000a8067`

```
000000000000 10101 000 00000 1100111
imm[11:0]    rs1   f3  rd    opcode
```

| Field | Bits | Value | Meaning |
|---|---|---|---|
| `opcode` | `[6:0]` | `1100111` | `jalr` |
| `rd` | `[11:7]` | `00000` = x0 | return address discarded — the `jalr x0,...` idiom, since this call's return address was already captured by the `jal` that invoked it |
| `funct3` | `[14:12]` | `000` | fixed for `jalr` |
| `rs1` | `[19:15]` | `10101` = x21 | holds the saved return address from the `jal` at `0x0C4` |
| `imm[11:0]` | `[31:20]` | `000000000000` | offset `0` |

Main decoder forces `ALUSrc=1`, `ALUSrcA=0`, `ALUOp=00` for this opcode, so the ALU computes `RD1(x21) + ImmExt(0) = 0x000000C8` — the same `PCTarget`-style add used by `lw`/`sw`, reusing the ALU rather than a second adder. `PCSrc=10` (forced by `main_decoder`) then selects `{ALUResult[31:1],1'b0}` at the top-level `PCNext` mux ([rv32i_single_cycle.sv:130-132](rv32i_single_cycle.sv#L130)) — bit 0 is already `0` here since `0xC8` is even, but the mux applies the clear unconditionally regardless. If that mux instead passed `ALUResult` straight through, this specific test wouldn't catch the omission (spec's Note 4) — the return address in this program happens to be even. That failure mode isn't exercised by this program and would need a deliberately odd-target `jalr` to catch, per the spec's own recommendation.

## Branch Scaffold — Why It Doesn't Repeat the Old `x9` Mistake

The original 4-instruction integration test's `beq` check only proved a branch instruction *executed without error* — a later instruction had already overwritten the one register that would have shown whether the branch actually redirected the PC. Every branch here uses this pattern instead:

```
        <branch> rs1,rs2,TAKEN     ; e.g. beq x1,x1,+12
        addi xEvidence,x0,0        ; reached only if NOT taken
        jal  x0,DONE               ; skip the taken-arm
TAKEN:
        addi xEvidence,x0,1        ; reached only if taken
DONE:
```

`xEvidence` is written by exactly one of the two `addi`s, never both, and nothing after `DONE` ever writes it again. A wrong `ALUControl` (e.g. `blt` computing `subtract` instead of `slt`) or a wrong polarity (`bge` reading `ALUResult0` instead of `~ALUResult0`) changes which arm executes, which changes the final value in `xEvidence` — the checked value is a direct function of which path the hardware actually took, not an inference from a coincidentally-correct downstream register.

## What This Program Does Not Prove

Matching the ASIC project's own documentation discipline: this is a directed test, not exhaustive coverage.

- Only one operand pair per branch type — not swept across the signed/unsigned boundary or zero.
- `jalr`'s bit-0 clear is exercised with an already-even target (`0x0C8`); the clear-a-genuinely-odd-target case from the spec's Note 4 is untested here.
- No instruction-memory address above `0x0D8` is exercised; `imem`/`dmem` are only checked for correctness at the specific indices this program touches (word index `3` for data, `0x000`–`0x0D8` for instructions).
- `FENCE`/`ECALL`/`EBREAK` remain out of scope, per the original project plan.
- This is a single straight-line-plus-branches program on one core instance — it says nothing about timing closure, synthesis, or multi-instruction hazards, which don't exist yet in a single-cycle design but will matter once the pipeline (next milestone) is built.
