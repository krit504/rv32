

**Scope of this document:** the datapath and control changes required to turn the single-cycle core (Steps 1–4 base + the full-ISA extension — `rv32i_extension_spec.md`) into the Harris & Harris pipelined processor of §7.5, Figures 7.49–7.51. Covers the four new pipeline-register modules, the updated `regfile` and `control_unit` specs, and the updated top-level integration, for every instruction already in scope from the extended single-cycle spec: all ten R-type ops, all nine I-type ALU ops, `lw`, `sw`, all six branches, `lui`, `auipc`, `jal`, `jalr`. **Not covered here:** forwarding, stalling, or flushing. With only the four pipeline registers in place, this datapath computes correct results solely for instruction sequences with no data or control dependency between nearby instructions — hazard resolution is later work (Harris & Harris §7.5.3), built on top of what's specified here, not inside it.

**Companion documents:** `rv32i_single_cycle_spec.md` (Steps 1–4 base), `rv32i_extension_spec.md` (full-ISA single-cycle extension) — every block below is a modification of a block already specified in one of those two documents, called out explicitly wherever it changes. `rv32i_pipelining_concepts.md` explains the reasoning behind each change below; this document is the reference tables and updated module specs only.

**Where this diverges from Figure 7.51 itself, stated up front:** Figure 7.51's pipelined processor supports R-type, `lw`, `sw`, `beq`, `jal`, and I-type ALU instructions — it has no `funct3`-dependent branch resolution (only `beq` exists), no `ALUSrcA` mux (no `auipc`), and no third `PCNext` source (no `jalr`). It resolves the next-PC decision with a single `PCSrcE` bit, built from `JumpE OR (BranchE AND ZeroE)`, both flags coming straight out of the Control Unit. This document reuses the already-built extended single-cycle mechanism instead — a 2-bit, opcode-forced `PCSrc` from the Main Decoder (`00` default, `01` for `jal`, `10` for `jalr`), merged at runtime with the branch-taken result — because it already generalizes to `jalr`'s distinct target source, which a single `Jump` flag cannot distinguish from `jal`'s. The merge logic itself sits in the same physical location Figure 7.51 puts its gate cluster: outside the Control Unit, fed by pipelined Decode-stage flags and the ALU's own fresh Execute-stage output.

---

## 1. System Overview

```
  Fetch          Decode                    Execute                 Memory              Writeback
 ┌──────┐  F/D  ┌──────────────┐   D/E   ┌────────────────┐  E/M  ┌──────────┐  M/W  ┌──────────┐
 │ PC   │──────►│ Register File│────────►│ ALU             │─────►│Data      │──────►│ Result   │
 │ IMem │  reg  │ (read ports) │   reg   │ PCTarget adder  │  reg │Memory    │  reg  │  mux     │
 │ +4   │       │ Extend       │         │ PCSrc resolve   │      │          │       │          │
 │      │       │ Control Unit │         │                 │      │          │       │          │
 └──────┘       └──────────────┘         └────────┬────────┘      └──────────┘       └────┬─────┘
     ▲                                             │ PCSrcE / redirect target             │
     └─────────────────────────────────────────────┘                                      │
                                                                                            │
     Register File write port (A3=RdW, WD3=ResultW, WE3=RegWriteW) ◄──────────────────────┘

  Four pipeline registers — F/D, D/E, E/M, M/W — inserted at the four stage boundaries.
  Every signal below carries a suffix (D, E, M, W) marking which stage it belongs to,
  matching Figure 7.51's convention exactly.
```

**Every module reused unchanged from the single-cycle spec:** `alu`, `immediate_generator`, `main_decoder`, `alu_decoder`, `pc`, `imem`, `dmem`. None of these compute anything differently — pipelining only changes _when_ each one's inputs arrive and _where_ its outputs go next. Every module changed or newly added is specified below.

**Every signal that changes, relative to the single-cycle extended spec:**

|Signal / Module|Single-cycle|Pipelined|Change|
|---|---|---|---|
|`regfile` write timing|`posedge clk`|`negedge clk`|write must land in the first half of the cycle so a same-cycle Decode-stage read sees it|
|`regfile.A3`/`WD3`/`WE3` source|`Instr[11:7]` / `Result` / `RegWrite`, same-cycle|`RdW` / `ResultW` / `RegWriteW`, from Writeback|write address/data/enable now come from an instruction four stages ahead of the one currently in Decode|
|`Branch`|internal to `control_unit` only, not a port|`BranchD`, a real top-level output|the branch-taken decision now happens outside `control_unit`, in Execute — `Branch` has to cross a pipeline-register boundary to get there|
|`control_unit` inputs|`op`, `funct3`, `funct7_5`, `Zero`, `ALUResult0`|`op`, `funct3`, `funct7_5` only|`Zero`/`ALUResult0` don't exist at Decode time in the pipelined design; `control_unit` no longer resolves `PCSrc` at all|
|`funct3`|consumed once, inside `control_unit`|also tapped separately at top level, piped `funct3D → funct3E`|needed a second time, in Execute, for the branch-taken table — independently of its Decode-stage use picking `ALUControl`|
|`Rd` (`Instr[11:7]`)|read once, same cycle it's used|piped `RdD → RdE → RdM → RdW`|must still be the same instruction's register number four stages later (Figure 7.49's built-in error, corrected in Figure 7.50)|
|`PCPlus4`|computed once, used same cycle|piped `PCPlus4F → D → E → M → W`|needed at Writeback for `jal`/`jalr`, four stages after Fetch computed it; only one adder exists, in Fetch|
|`ImmExt`|computed once, used same cycle|piped `ImmExtD → E`, and further `→ M → W` for `lui` only|`lui`'s writeback value is produced in Decode and not touched again until Writeback|
|four new modules|—|`f_d_reg`, `d_e_reg`, `e_m_reg`, `m_w_reg`|the pipeline registers themselves|

---

## 2. Block: Register File (`regfile`) — Updated Spec

**Purpose:** unchanged — 32 general-purpose 32-bit registers, `x0` hardwired to zero, two combinational read ports, one clocked write port. What changes is _when_ the write happens and _which stage_ supplies the write address/data.

**Ports (unchanged from the single-cycle spec):** `clk`, `rst_n`, `A1[4:0]`, `A2[4:0]`, `A3[4:0]`, `WD3[31:0]`, `WE3`, `RD1[31:0]`, `RD2[31:0]`. No port added or removed — only what drives `A1`/`A2`/`A3`/`WD3`/`WE3` at the top level changes (§10).

**Functional behavior — what changes:**

- **Write clock edge changes from `posedge clk` to `negedge clk`.** `if (WE3 && A3 != 5'd0) regs[A3] <= WD3;` now triggers on the falling edge, not the rising edge. Reads (`RD1`/`RD2`) stay purely combinational, unclocked, exactly as before.
- **Why:** in the pipelined design, the register file is read by whichever instruction is in Decode and written by a completely different instruction in Writeback, in the same physical clock cycle. Writing on the falling edge means the write commits in the first half of the cycle; the combinational read then sees the just-written value for the remainder of that same cycle. This is what lets one instruction's Writeback-stage write and a different, later instruction's Decode-stage read of the _same register_ both resolve correctly within one cycle, with no forwarding hardware and no stall — matching Figure 7.48's cycle 6, where the register file writes `s3` and reads `t4` in the same cycle with no conflict.
- **`A1`/`A2` now read Decode-stage fields, not raw `Instr`:** `A1 = InstrD[19:15]`, `A2 = InstrD[24:20]` — the same bit positions as before, just sourced from the `F/D` register's output instead of directly from `imem.RD`.
- **`A3`/`WD3`/`WE3` now come from Writeback, not from the instruction currently being decoded:** `A3 = RdW`, `WD3 = ResultW`, `WE3 = RegWriteW`. This is the one part of `regfile`'s wiring that does **not** connect to whatever is in Decode this cycle — it connects to whatever instruction is finishing in Writeback this cycle, which entered the pipeline four cycles earlier.
- Reset and the `x0` handling (zero-forced at the read mux, write-guarded by `A3 != 5'd0`) are unchanged from the single-cycle spec.

**What "done" looks like for this block, updated:** everything from the single-cycle spec's test list, plus: drive a write on the falling edge of a cycle and confirm a combinational read issued later in that _same_ cycle (same clock period, after the falling edge) sees the new value, while a read issued _before_ the falling edge in that same cycle still sees the old value. Confirm `A1`/`A2` and `A3`/`WD3`/`WE3` can address two different registers in the same cycle without interference, matching a write-to-`sX`-while-reading-`tY` scenario.

---

## 3. Block: `f_d_reg` — Fetch/Decode Pipeline Register

**Purpose:** the first of four pipeline registers. Latches everything Fetch produced so Decode has a stable value to read for the entire following cycle, while Fetch itself moves on to the next instruction.

**Ports:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`clk`|in|1|system clock|
|`rst_n`|in|1|async active-low reset|
|`InstrF`|in|32|the instruction word straight out of `imem.RD`, not yet registered|
|`PCF`|in|32|the Fetch-stage `PC` value (= `pc.PCOut`)|
|`PCPlus4F`|in|32|`PCF + 4`|
|`InstrD`|out|32|latched instruction word|
|`PCD`|out|32|latched `PC`|
|`PCPlus4D`|out|32|latched `PC + 4`|

**Functional behavior:** single `always_ff @(posedge clk or negedge rst_n)` block, capturing all three inputs unconditionally every cycle: `if (!rst_n) {InstrD, PCD, PCPlus4D} <= '0; else {InstrD, PCD, PCPlus4D} <= {InstrF, PCF, PCPlus4F};`

**Why `PCD` is carried at all, when Decode itself never reads `PC`:** `PCD` isn't used inside the Decode stage's own logic — it's carried through only so it reaches `d_e_reg` and becomes `PCE`, which the `PCTarget` adder in Execute needs (`PCTarget = PCE + ImmExtE`). This is the general rule stated in Section 4 of the concepts document: a value with no use in the very next stage can still be required several stages later, and has to ride through every register in between regardless.

**On reset:** `InstrD` clears to `32'b0`, which decodes to `op = 7'b0000000` — not one of the nine recognized opcodes in this spec, so `main_decoder`'s default-safe-output discipline (already required for every unrecognized opcode) means this behaves as a defined no-op: `RegWrite=0`, `MemWrite=0`, `BranchD=0`. No dedicated "flush to NOP" logic is needed for the reset case specifically, because the existing decode-default behavior already covers it. This does **not** cover flushing after a taken branch during normal operation — that's still out of scope (§9).

**What "done" looks like for this block:** drive a sequence of known `(InstrF, PCF, PCPlus4F)` triples, confirm `(InstrD, PCD, PCPlus4D)` matches the previous cycle's inputs exactly, one cycle later. Confirm `rst_n` asserted low clears all three outputs to `0` regardless of current inputs.

---

## 4. Block: `d_e_reg` — Decode/Execute Pipeline Register

**Purpose:** latches every Decode-stage output Execute needs, plus every value later stages need that only exists by the end of Decode.

**Ports:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`clk`|in|1|system clock|
|`rst_n`|in|1|async active-low reset|
|`RD1`|in|32|`regfile.RD1`, this cycle's Decode-stage read|
|`RD2`|in|32|`regfile.RD2`|
|`ImmExtD`|in|32|`immediate_generator.ImmExt`|
|`RdD`|in|5|`InstrD[11:7]`|
|`funct3D`|in|3|`InstrD[14:12]`, tapped independently of `control_unit`'s own internal use of it|
|`PCD`, `PCPlus4D`|in|32 each|passed through from `f_d_reg`|
|`RegWriteD`, `ALUSrcD`, `ALUSrcAD`, `MemWriteD`, `BranchD`|in|1 each|from `control_unit`|
|`ResultSrcD`|in|2|from `control_unit`|
|`ALUControlD`|in|4|from `control_unit`|
|`PCSrcD`|in|2|opcode-forced value from `control_unit` (`00`/`01`/`10`)|
|`RD1E`, `RD2E`, `ImmExtE`|out|32 each|latched|
|`RdE`|out|5|latched|
|`funct3E`|out|3|latched|
|`PCE`, `PCPlus4E`|out|32 each|latched|
|`RegWriteE`, `ALUSrcE`, `ALUSrcAE`, `MemWriteE`, `BranchE`|out|1 each|latched|
|`ResultSrcE`|out|2|latched|
|`ALUControlE`|out|4|latched|
|`PCSrcE`|out|2|latched (still the opcode-forced value — see the naming note in §7)|

**Functional behavior:** one `always_ff @(posedge clk or negedge rst_n)` block, every output the registered version of the same-named input, all captured unconditionally every cycle.

**What is deliberately _not_ on this list, and why:** `ImmSrcD` — it was only needed to drive `immediate_generator`, already done by the time Decode finishes; nothing downstream ever reads `ImmSrc` again. Confirming a signal has no further use before leaving it off this register is as much a part of getting this module's field list right as confirming a signal that _does_ have further use is included.

**What "done" looks like for this block:** drive a full set of known Decode-stage values, confirm every `*E` output equals the corresponding input from the previous cycle. Specifically confirm `funct3E` is present and correctly latched even for an instruction where `funct3` played no role in `ALUControlD`'s value (e.g. `lw`) — this is the field most likely to be silently dropped, since it "looks used up" once `control_unit` has already consumed it once.

---

## 5. Block: `e_m_reg` — Execute/Memory Pipeline Register

**Purpose:** latches Execute's outputs for Memory, plus everything later stages still need.

**Ports:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`clk`|in|1|system clock|
|`rst_n`|in|1|async active-low reset|
|`ALUResultE`|in|32|`alu.ALUResult`|
|`WriteDataE`|in|32|`RD2E`, passed straight through Execute unchanged — this is `sw`'s store data|
|`RdE`, `PCPlus4E`, `ImmExtE`|in|32/5/32|passed through from `d_e_reg`|
|`RegWriteE`, `MemWriteE`|in|1 each|from `d_e_reg`|
|`ResultSrcE`|in|2|from `d_e_reg`|
|`ALUResultM`, `WriteDataM`|out|32 each|latched|
|`RdM`, `PCPlus4M`, `ImmExtM`|out|32/5/32|latched|
|`RegWriteM`, `MemWriteM`|out|1 each|latched|
|`ResultSrcM`|out|2|latched|

**Functional behavior:** one `always_ff` block, unconditional capture every cycle, same pattern as §3–4.

**What is deliberately _not_ on this list:** `ALUSrc`, `ALUSrcA`, `ALUControl`, `funct3`, `Branch`, `PCSrc` — every one of these existed only to run the ALU once and resolve `PCSrcE`'s redirect once, both finished inside Execute. None of them are read again in Memory or Writeback.

**What "done" looks like for this block:** drive known Execute-stage outputs, confirm every `*M` output matches one cycle later. Specifically confirm `ImmExtM` survives here even on an instruction where Execute did nothing with it (any instruction other than `lui`) — same category of check as `funct3E` in §4.

---

## 6. Block: `m_w_reg` — Memory/Writeback Pipeline Register

**Purpose:** latches Memory's outputs for Writeback — the last of the four registers.

**Ports:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`clk`|in|1|system clock|
|`rst_n`|in|1|async active-low reset|
|`ReadDataM`|in|32|`dmem.RD`|
|`ALUResultM`, `RdM`, `PCPlus4M`, `ImmExtM`|in|32/5/32/32|passed through from `e_m_reg`|
|`RegWriteM`|in|1|from `e_m_reg`|
|`ResultSrcM`|in|2|from `e_m_reg`|
|`ReadDataW`|out|32|latched|
|`ALUResultW`, `RdW`, `PCPlus4W`, `ImmExtW`|out|32/5/32/32|latched|
|`RegWriteW`|out|1|latched|
|`ResultSrcW`|out|2|latched|

**Functional behavior:** one `always_ff` block, unconditional capture every cycle, same pattern as §3–5.

**`RdW` and `RegWriteW` are the two signals feeding `regfile`'s write port (§2) — they, together with `ResultW` (§10), are what finally leave the pipeline register chain and land back on the register file, four cycles after the instruction they belong to was in Decode.**

**What "done" looks like for this block:** drive known Memory-stage outputs, confirm every `*W` output matches one cycle later. Trace one full instruction's `Rd` value from `RdD` through `RdE`, `RdM`, `RdW` across four consecutive cycles and confirm it is the _same_ value at every stage — the direct check against Figure 7.49's error (§9).

---

## 7. Block: Control Unit (`control_unit`) — Updated Spec

**Ports — changed from the single-cycle spec:**

|Signal|Dir|Width|Change|
|---|---|---|---|
|`op`|in|7|unchanged, now understood to be `InstrD[6:0]`|
|`funct3`|in|3|unchanged, `InstrD[14:12]`|
|`funct7_5`|in|1|unchanged, `InstrD[30]`|
|`Zero`|—|—|**removed.** Doesn't exist at Decode time in the pipelined design.|
|`ALUResult0`|—|—|**removed**, same reason.|
|`RegWrite`, `ImmSrc[2:0]`, `ALUSrc`, `ALUSrcA`, `MemWrite`, `ResultSrc[1:0]`, `ALUControl[3:0]`, `PCSrc[1:0]`|out|as specified|unchanged in meaning; every one of these becomes a `*D`-suffixed signal once it leaves this module and is understood as this cycle's Decode-stage value|
|`Branch`|out|1|**newly exposed as a real port.** In the single-cycle spec this was internal-only, consumed by an AND gate inside this same module. That AND gate no longer exists inside `control_unit` — the branch-taken decision has moved to Execute (§10), so `Branch` now has to leave this module and cross the `D/E` register as `BranchD → BranchE` to get there.|

**Internal structure — unchanged:** still wraps `main_decoder` and `alu_decoder` exactly as specified in the single-cycle extension spec, with the same `ALUOp` wire strictly internal between the two. The only thing removed is the old `PCSrc = Branch & Zero`-style resolution logic that used to live inside this module — that computation is now impossible to do here, since `Zero` doesn't exist until Execute, four... one stage later than Decode.

**What `PCSrc` means as an output of this module, now:** exactly what it meant in the single-cycle extension spec's Main Decoder row — the _opcode-forced_ value only (`00` for every instruction whose next-PC decision isn't opcode-determined, including branches; `01` forced for `jal`; `10` forced for `jalr`). This module never merges it with a runtime branch result — it can't, it has no access to one. The merge happens downstream (§10).

**What "done" looks like for this block:** every directed test from the single-cycle extension spec's `control_unit` section still applies, minus anything that drove `Zero`/`ALUResult0` (no longer inputs) or checked a fully-resolved `PCSrc` output (this module only ever produces the opcode-forced value now). Add one test confirming `Branch` is externally observable as a port and correctly reflects `BranchD` for every branch opcode.

---

## 8. Top-Level Integration (`rv32_top`) — Updated Spec

**New module instantiations:** `f_d_reg`, `d_e_reg`, `e_m_reg`, `m_w_reg`, one each, wired between the five stages as shown in §1.

**Stage-by-stage wiring:**

**Fetch:** `pc` and `imem` unchanged internally. `PCPlus4F = PCF + 32'd4`, computed once, here — this is the _only_ place this addition happens; every later stage receives it already computed, via the pipeline registers. `PCNext` (feeding `pc.PCNext`) is now a 3-way mux driven by a signal computed in Execute and fed straight back, combinationally, across the width of the Decode stage:

```
PCNext = (PCNextSelE == 2'b00) ? PCPlus4F :
         (PCNextSelE == 2'b01) ? PCTargetE :
                                  {ALUResultE[31:1], 1'b0};
```

**Decode:** `regfile` (read ports only — the write port is wired from Writeback, §2), `immediate_generator`, `control_unit` all instantiated here, fed from `InstrD` and its field slices, exactly as in the single-cycle spec but reading `InstrD` instead of raw `Instr`. `RdD = InstrD[11:7]`. `funct3D = InstrD[14:12]`, tapped directly here — fed both into `control_unit.funct3` (as before) _and_ separately into `d_e_reg.funct3D`, since these are two independent downstream uses of the same bits (§4).

**Execute:** `alu` instantiated here, fed by the two new muxes:

```
SrcAE = ALUSrcAE ? PCE : RD1E;
SrcBE = ALUSrcE  ? ImmExtE : RD2E;
```

`PCTargetE = PCE + ImmExtE` — the dedicated adder, now operating on Execute-stage-registered values instead of the same-cycle values it used in the single-cycle design. **`PCSrc` resolution — the logic that replaces the old in-`control_unit` AND gate:**

|`funct3E`|Taken condition|
|---|---|
|`000` (`beq`)|`ZeroE = 1`|
|`001` (`bne`)|`ZeroE = 0`|
|`100` (`blt`)|`ALUResultE[0] = 1`|
|`101` (`bge`)|`ALUResultE[0] = 0`|
|`110` (`bltu`)|`ALUResultE[0] = 1`|
|`111` (`bgeu`)|`ALUResultE[0] = 0`|

```
takenE      = /* row lookup above, using funct3E, ZeroE, ALUResultE[0] */;
PCNextSelE  = (PCSrcE != 2'b00)      ? PCSrcE :   // jal (01) or jalr (10), opcode-forced
              (BranchE & takenE)     ? 2'b01  :   // branch actually taken
                                        2'b00;    // default: sequential
```

This is safe as a plain priority structure for the same reason it was in the single-cycle spec: `PCSrcE` (the opcode-forced value pipelined in from `d_e_reg`) is `00` for every instruction where `BranchE` can be `1` — a branch and a forced jump/jalr redirect never compete for the same cycle. `PCNextSelE` and `PCTargetE`/`ALUResultE` together are exactly the signal pair fed back to the Fetch-stage mux above — this is the wire Figure 7.51 draws crossing all the way from the Execute-stage gate cluster back to the leftmost mux, and it is a direct combinational feedback path, not something that goes through any pipeline register.

**Memory:** `dmem` instantiated here, unchanged internally, fed by `ALUResultM` (address), `WriteDataM` (write data), `MemWriteM` (write enable).

**Writeback:**

```
ResultW = (ResultSrcW == 2'b00) ? ALUResultW :
          (ResultSrcW == 2'b01) ? ReadDataW  :
          (ResultSrcW == 2'b10) ? ImmExtW    :
                                   PCPlus4W;
```

`ResultW` and `RdW` feed back together into `regfile`'s write port (`WD3`, `A3`), with `RegWriteW` as `WE3` — the feedback loop described in §2, now shown from the Writeback side.

**What "done" looks like for the integrated core:** extend the single-cycle extension spec's integration test program unchanged in instruction content, but now step it cycle by cycle watching five instructions in flight at once. For a sequence with **no** data or control dependency between adjacent instructions (the explicit limit of this document's scope, §9), confirm every stage's signals — `InstrD`, `RD1E`/`RD2E`, `ALUResultM`, `ReadDataW`, `ResultW`, and the final register file contents — match hand-computed expectations at every cycle, tracking each instruction through all five stages independently.

---

## 9. Pipeline-Specific Failure-Mode Notes

**Note 1 — reading `Rd` straight from `InstrD[11:7]` at the write port instead of pipelining it through to `RdW`.** This is Figure 7.49's own deliberately-built-in error: wiring `regfile.A3` directly to `InstrD[11:7]` while `WD3` comes from `ResultW`, four stages later, silently writes the _current_ Decode-stage instruction's destination register with a _different, earlier_ instruction's result. The fix (Figure 7.50, and this document's §4–6) is pipelining `Rd` itself through every register — `RdD → RdE → RdM → RdW` — so the register number reaching the write port in Writeback belongs to the same instruction as `ResultW`. Any signal read fresh from an early stage's field instead of carried forward through the registers hits this same class of bug; `Rd` is simply the book's worked example of it, and `ImmExt` surviving to Writeback for `lui` (§4–6) is the identical principle applied a second time.

**Note 2 — forgetting `Branch` now has to be a real port.** The single-cycle spec explicitly documented `Branch` as "internal to Control Unit only, not a top-level port" — correct at the time, and now the opposite of correct. In the pipelined design the branch-taken decision has moved out of `control_unit` entirely, so `Branch` must leave the module, cross `d_e_reg`, and arrive in Execute as `BranchE`. Copying the single-cycle `control_unit` port list forward unmodified leaves `Branch` trapped inside the module with nowhere to go, and every branch silently fails to redirect the PC.

**Note 3 — leaving `regfile`'s write on `posedge clk`.** Doing so doesn't produce an obvious error in isolation — the register file still writes correctly, one cycle at a time. What breaks is the same-cycle read-after-write case in Figure 7.48's cycle 6 pattern: a Decode-stage read of a register that a Writeback-stage instruction is writing _this same cycle_ will see the _old_ value instead of the new one, because the write hasn't landed yet when the read (evaluated combinationally, all cycle) samples it. This produces a data hazard that looks identical to the genuine data hazards forwarding is meant to fix (§9's own scope boundary), except it's actually a clocking bug masquerading as one, and won't be fixed by adding forwarding later if the underlying edge is still wrong.

**Note 4 — dropping `PCPlus4` or `ImmExt` partway through the pipeline because "nothing in this stage needs it."** `PCPlus4` is unused by Execute or Memory logic directly, but `jal`/`jalr` need `PCPlus4W` at Writeback; `ImmExt` is unused by Memory logic directly, but `lui` needs `ImmExtM`/`ImmExtW`. Both must occupy a field in every intermediate pipeline register regardless of local stage use — the general rule from §4's `d_e_reg` note, restated at every subsequent register too.

**Note 5 — the redirect wire existing does not mean control hazards are handled.** `PCNextSelE`/`PCTargetE` feeding back to the Fetch-stage mux (§8) makes the _correct_ redirect target available at the right time — it says nothing about the one or two instructions Fetch and Decode already pulled in during the cycles before that redirect arrives, on the assumption the branch wasn't taken. Those instructions are not flushed by anything specified in this document. This is the exact scope boundary stated up front: this document builds the datapath Figure 7.51 shows; the fix for what happens when a branch actually is taken is explicitly deferred, matching the book's own "this control hazard will be fixed in Section 7.5.3."

---

## 10. Full Consolidated Control Signal Reference

|Signal|Width|Produced by|Meaning|
|---|---|---|---|
|`RegWriteD/E/M/W`|1|Main Decoder, pipelined through all four registers|write enable, register file — only `RegWriteW` actually reaches `regfile`|
|`ImmSrcD`|3|Main Decoder|immediate format select; consumed entirely within Decode, not pipelined further|
|`ALUSrcD/E`|1|Main Decoder, pipelined to Execute|ALU `SrcB`: register (`0`) or immediate (`1`); consumed in Execute, not pipelined further|
|`ALUSrcAD/E`|1|Main Decoder, pipelined to Execute|ALU `SrcA`: `RD1` (`0`) or `PC` (`1`, `auipc` only); consumed in Execute|
|`MemWriteD/E/M`|1|Main Decoder, pipelined to Memory|write enable, data memory; consumed in Memory, not pipelined further|
|`ResultSrcD/E/M/W`|2|Main Decoder, pipelined through all four registers|writeback source (`00`=ALU, `01`=memory, `10`=`ImmExt`, `11`=`PCPlus4`); consumed in Writeback|
|`BranchD/E`|1|Main Decoder — now a real `control_unit` port|flags a branch opcode to the Execute-stage taken-resolution logic|
|`ALUControlD/E`|4|ALU Decoder, pipelined to Execute|final ALU operation select; consumed in Execute|
|`PCSrcD/E`|2|Main Decoder, pipelined to Execute|opcode-forced next-PC hint (`00` default, `01` `jal`, `10` `jalr`); merged with the runtime branch result in Execute to form `PCNextSelE`|
|`funct3D/E`|3|tapped from `InstrD[14:12]` at the top level|used twice, independently: inside `control_unit` (Decode) to help pick `ALUControlD`, and again in Execute (`funct3E`) for the branch-taken table|
|`ZeroE`|1|ALU|`1` iff `ALUResultE == 0`; consumed immediately in Execute, not pipelined further|
|`ALUResultE[0]`|1|ALU|signed/unsigned less-than result bit; consumed immediately in Execute|
|`PCNextSelE`|2|Execute-stage merge logic (§8)|final `PCNext` mux select, fed back combinationally to Fetch; not itself pipelined — it's regenerated fresh every cycle from that cycle's `d_e_reg` outputs|
|`RdD/E/M/W`|5|`InstrD[11:7]`, pipelined through all four registers|destination register number; must travel in lockstep with the data it's paired with (§9, Note 1)|

---

## 11. Signals Checklist (updated/new modules only)

|Block|Inputs|Outputs|Notes|
|---|---|---|---|
|`regfile`|`clk`, `rst_n`, `A1[4:0]`, `A2[4:0]`, `A3[4:0]` (=`RdW`), `WD3[31:0]` (=`ResultW`), `WE3` (=`RegWriteW`)|`RD1[31:0]`, `RD2[31:0]`|write now on `negedge clk`; `A3`/`WD3`/`WE3` sourced from Writeback, not the current Decode instruction|
|`f_d_reg`|`clk`, `rst_n`, `InstrF[31:0]`, `PCF[31:0]`, `PCPlus4F[31:0]`|`InstrD[31:0]`, `PCD[31:0]`, `PCPlus4D[31:0]`|first of four pipeline registers|
|`d_e_reg`|`clk`, `rst_n`, `RD1[31:0]`, `RD2[31:0]`, `ImmExtD[31:0]`, `RdD[4:0]`, `funct3D[2:0]`, `PCD[31:0]`, `PCPlus4D[31:0]`, `RegWriteD`, `ALUSrcD`, `ALUSrcAD`, `MemWriteD`, `BranchD`, `ResultSrcD[1:0]`, `ALUControlD[3:0]`, `PCSrcD[1:0]`|`RD1E/RD2E/ImmExtE[31:0]`, `RdE[4:0]`, `funct3E[2:0]`, `PCE/PCPlus4E[31:0]`, `RegWriteE`, `ALUSrcE`, `ALUSrcAE`, `MemWriteE`, `BranchE`, `ResultSrcE[1:0]`, `ALUControlE[3:0]`, `PCSrcE[1:0]`|widest of the four registers; `ImmSrcD` deliberately not carried|
|`e_m_reg`|`clk`, `rst_n`, `ALUResultE[31:0]`, `WriteDataE[31:0]` (=`RD2E`), `RdE[4:0]`, `PCPlus4E[31:0]`, `ImmExtE[31:0]`, `RegWriteE`, `MemWriteE`, `ResultSrcE[1:0]`|`ALUResultM/WriteDataM[31:0]`, `RdM[4:0]`, `PCPlus4M/ImmExtM[31:0]`, `RegWriteM`, `MemWriteM`, `ResultSrcM[1:0]`|`ALUSrc`, `ALUSrcA`, `ALUControl`, `funct3`, `Branch`, `PCSrc` all stop here|
|`m_w_reg`|`clk`, `rst_n`, `ReadDataM[31:0]`, `ALUResultM[31:0]`, `RdM[4:0]`, `PCPlus4M/ImmExtM[31:0]`, `RegWriteM`, `ResultSrcM[1:0]`|`ReadDataW/ALUResultW[31:0]`, `RdW[4:0]`, `PCPlus4W/ImmExtW[31:0]`, `RegWriteW`, `ResultSrcW[1:0]`|last register; `RdW`/`ResultW`/`RegWriteW` feed straight back to `regfile`|
|`control_unit`|`op[6:0]`, `funct3[2:0]`, `funct7_5`|`RegWrite`, `ImmSrc[2:0]`, `ALUSrc`, `ALUSrcA`, `MemWrite`, `ResultSrc[1:0]`, `ALUControl[3:0]`, `PCSrc[1:0]`, `Branch`|`Zero`/`ALUResult0` inputs removed; `Branch` newly exposed as a port|


---

## 12. Hazard Handling — Scope and Overview

**Scope:** the changes that add forwarding, load-use stalling, and control-hazard flushing to the pipelined core in §1–§11.

- This section supersedes the "Not covered here" statement at the top of this document, and §9, Note 5.
- After these changes the pipeline gives correct results for any instruction sequence.
- The cost is performance only: one stall cycle per load-use dependency, and two flushed instructions per taken branch or jump.

`rv32i_hazards_concepts.md` explains the reasoning. This section is the reference tables and updated module specs only. Source design: Harris & Harris §7.5.3.

**Where this diverges from the book's baseline:**

- **Forwarding from Memory is not always `ALUResultM`.**
    - `lui` writes back `ImmExtM`. `jal` and `jalr` write back `PCPlus4M`.
    - This design forwards `FwdDataM`, selected by `ResultSrcM` (§17).
    - `ImmExtM` and `PCPlus4M` are already carried in `e_m_reg`, so no new pipeline fields are needed.
- **Forwarding is applied before the `ALUSrcE`/`ALUSrcAE` muxes.**
    - For I-type, U-type, and J-type instructions, `Instr[19:15]` and `Instr[24:20]` are immediate bits, not register numbers.
    - `Rs1E`/`Rs2E` can match `RdM`/`RdW` by accident (§18, Note 1).
- **The flush clears `PCSrcE`, not only the write enables.**
    - `PCSrc` is a 2-bit opcode-forced value carried through `D/E` in this design.
    - A flushed wrong-path `jal` or `jalr` that kept `PCSrcE` set would trigger a second, wrong redirect.

**Modules added or changed:**

|Module|Change|
|---|---|
|`hazard_unit`|**new.** Combinational. Produces `ForwardAE`, `ForwardBE`, `StallF`, `StallD`, `FlushD`, `FlushE` (§13)|
|`pc`|new input `StallF` (§14)|
|`f_d_reg`|new inputs `StallD`, `FlushD` (§15)|
|`d_e_reg`|new inputs `Rs1D`, `Rs2D`, `FlushE`; new outputs `Rs1E`, `Rs2E` (§16)|
|`rv32_top`|`hazard_unit` instantiated; `FwdDataM`, `FwdRD1E`, `FwdRD2E` added; `SrcAE`/`SrcBE` and `WriteDataE` re-sourced (§17)|

**Modules unchanged:** `alu`, `regfile`, `imem`, `dmem`, `immediate_generator`, `main_decoder`, `alu_decoder`, `control_unit`, `e_m_reg`, `m_w_reg`. `e_m_reg`'s port list does not change. Only what drives its `WriteDataE` input changes, at the top level.

**Superseded where they disagree with §12–§20:**

- the scope paragraph at the top of this document
- §3 and §4: port tables and functional behavior
- §5: `WriteDataE` described as `RD2E`
- §8: the Execute-stage `SrcAE`/`SrcBE` assigns
- §9: Note 5
- §11: the `f_d_reg` and `d_e_reg` rows

---

## 13. Block: Hazard Unit (`hazard_unit`)

**Purpose:** detects the hazards the pipeline registers do not resolve, and drives the controls that resolve them:

- forwarding selects for the two ALU operand paths
- stall enables for `pc` and `f_d_reg`
- flush clears for `f_d_reg` and `d_e_reg`

Purely combinational. Instantiated at the top level as a sibling of the stages, not inside `control_unit`. It compares signals from three different stages in the same cycle, and no single stage's block can see all of them.

**Ports:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`Rs1D`|in|5|`InstrD[19:15]`, `rs1` of the instruction in Decode|
|`Rs2D`|in|5|`InstrD[24:20]`, `rs2` of the instruction in Decode|
|`Rs1E`|in|5|`rs1` of the instruction in Execute (`d_e_reg` output)|
|`Rs2E`|in|5|`rs2` of the instruction in Execute (`d_e_reg` output)|
|`RdE`|in|5|destination register of the instruction in Execute|
|`RdM`|in|5|destination register of the instruction in Memory|
|`RdW`|in|5|destination register of the instruction in Writeback|
|`RegWriteE`|in|1|instruction in Execute writes a register. Qualifies the load-use check (§18, Note 9)|
|`RegWriteM`|in|1|instruction in Memory writes a register|
|`RegWriteW`|in|1|instruction in Writeback writes a register|
|`ResultSrcE`|in|2|`01` identifies a `lw` in Execute, together with `RegWriteE`|
|`PCNextSelE`|in|2|resolved next-PC select from §8. Non-zero means a redirect is happening this cycle|
|`ForwardAE`|out|2|select for the `SrcA` register-value forwarding mux|
|`ForwardBE`|out|2|select for the `SrcB` register-value forwarding mux|
|`StallF`|out|1|hold `pc`|
|`StallD`|out|1|hold `f_d_reg`|
|`FlushD`|out|1|clear `f_d_reg`|
|`FlushE`|out|1|clear `d_e_reg`|

**Parameters:** `FORWARDING` (default `1`; `0` selects the ablation described under Functional behavior). **Internal signals:** `lwStall` (1), `depStall` (1), `stallCond` (1), `redirectE` (1). All combinational, no state.

**`ForwardAE`/`ForwardBE` encoding:**

|Code|Source selected|Meaning|
|---|---|---|
|`00`|`RD1E` / `RD2E`|no forwarding|
|`01`|`ResultW`|match against the instruction in Writeback|
|`10`|`FwdDataM`|match against the instruction in Memory|

**Forwarding conditions, in priority order** (`ForwardBE` is identical, using `Rs2E`):

```
ForwardAE = ((Rs1E == RdM) && RegWriteM && (RdM != 5'd0)) ? 2'b10 :
            ((Rs1E == RdW) && RegWriteW && (RdW != 5'd0)) ? 2'b01 :
                                                             2'b00;
```

**Stall and flush conditions:**

```
lwStall   = ((Rs1D == RdE) || (Rs2D == RdE)) && RegWriteE && (ResultSrcE == 2'b01) && (RdE != 5'd0);
redirectE = (PCNextSelE != 2'b00);
stallCond = (FORWARDING != 0) ? lwStall : depStall;   // depStall: ablation only, see below

StallF = stallCond;
StallD = stallCond;
FlushD = redirectE;
FlushE = stallCond | redirectE;
```

With `FORWARDING = 1` (default) `stallCond` is `lwStall`, so `StallF`/`StallD` equal `lwStall` and `FlushE` is `lwStall | redirectE`, as in the rest of this document.

**Functional behavior:**

- **Priority: Memory before Writeback.**
    - If `RdM` and `RdW` both equal `Rs1E`, two earlier instructions wrote the same register.
    - The one in Memory entered the pipeline later, so its value is the correct one.
- **`RdM != 0` and `RdW != 0` are required.**
    - `x0` is never actually written.
    - Without the guard, `addi x0,x0,5` followed by `add x5,x0,x0` would forward `5` into a register that must read `0`.
- **A load in Memory is never forwarded from.**
    - For `lw`, the data does not exist until the end of its Memory cycle. `FwdDataM` would be the load's address.
    - A live consumer cannot reach Execute with a load in Memory. That is the load-use case, and `lwStall` already held it in Decode one cycle earlier.
    - During the stall cycle, Execute holds a bubble with `Rs1E = Rs2E = 0`, which cannot match a non-zero `RdM`.
- **The stall check and the forwarding check use different stage pairs.**
    - Stall: `Rs1D`/`Rs2D` against `RdE`. The instruction in Decode against a load in Execute.
    - Forwarding: `Rs1E`/`Rs2E` against `RdM`/`RdW`. The instruction in Execute against older instructions ahead of it.
- **Stall and flush never assert in the same cycle.**
    - `lwStall` needs a load in Execute.
    - `redirectE` needs a branch or jump in Execute.
    - One instruction cannot be both, so no priority logic is needed. `FlushE` is the OR of the two causes.
- **No combinational loop.**
    - `ForwardAE`/`ForwardBE` depend only on `Rs1E`, `Rs2E`, `RdM`, `RdW`, `RegWriteM`, `RegWriteW`.
    - `redirectE` depends on `PCNextSelE`, which depends on the ALU output, which depends on `ForwardAE`/`ForwardBE`.
    - `FlushD`/`FlushE` are synchronous clears, sampled at the next clock edge, so they do not feed back.
- **`RegWriteE` qualifies the load check.**
    - A load must write a register, so `RegWriteE = 1` for every real `lw`.
    - For `sw` and branches the `Instr[11:7]` field is immediate bits, not a destination register. It can equal `Rs1D`/`Rs2D` by accident.
    - `main_decoder` now drives `ResultSrc` to a defined `00` on those rows, so `ResultSrcE == 01` is already false for them. The qualifier is kept as defense in depth (§18, Note 9).
- **`FORWARDING = 0` (ablation).**
    - `ForwardAE`/`ForwardBE` are tied to `00`. Results are only correct if dependent instructions are held apart instead, so the unit stalls the consumer in Decode:
      ```
      depStall = ((RegWriteE && (RdE != 0) && (Rs1D == RdE || Rs2D == RdE)) ||
                  (RegWriteM && (RdM != 0) && (Rs1D == RdM || Rs2D == RdM))) && !redirectE;
      ```
    - A producer in Writeback needs no stall: the negedge register-file write lands before the Decode-stage read is sampled (§2).
    - `depStall` is masked by `redirectE`. A redirect flushes the instruction in Decode anyway, and holding `pc` during a redirect would drop the new target. This also keeps stall and flush from asserting together.
    - It compares register-number fields unconditionally, so it also stalls on immediate-bit matches (§18, Note 8), and costs more cycles than forwarding.

**What "done" looks like for this block:** directed tests that drive the inputs directly and check every output.

- `ForwardAE`/`ForwardBE`:
    - match on `RdM` only → `10`
    - match on `RdW` only → `01`
    - match on both → `10`
    - match on `RdM` with `RegWriteM = 0` → falls through to the `RdW` check
    - `Rs1E = 0` with `RdM = 0` → `00`
    - no match → `00`
    - repeat each case for `ForwardBE` with `Rs2E`
- `lwStall`:
    - load in Execute, `Rs1D == RdE` → `1`
    - load in Execute, `Rs2D == RdE` → `1`
    - same match with `ResultSrcE != 01` → `0`
    - match with `ResultSrcE = 01` but `RegWriteE = 0` → `0`
    - `RdE = 0` with `Rs1D = 0` → `0`
    - no match → `0`
- no hazard_unit input or output is `x` or `z` on any cycle of any test program (checked by `tb_hazard.sv`).
- `redirectE`: `PCNextSelE = 00` gives `FlushD = 0`. `01` or `10` gives `FlushD = 1`.
- `FlushE` asserts for either cause alone.
- `StallD` and `FlushD` are never both `1` for any input combination the datapath can produce.

---

## 14. Block: PC Register (`pc`) — Updated Spec

**Ports — one added:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`StallF`|in|1|when `1`, `PCOut` holds its value instead of loading `PCNext`|

`clk`, `rst_n`, `PCNext[31:0]`, `PCOut[31:0]` are unchanged.

**Functional behavior — what changes:**

```
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)        PCOut <= 32'b0;
    else if (!StallF)  PCOut <= PCNext;
end
```

- Reset is unchanged and takes priority over the stall.
- While stalled, `imem` is addressed with the same `PCOut`, so the instruction in Fetch is fetched again the next cycle.
- `f_d_reg` ignores that instruction while `StallD` is also asserted (§15).
- `StallF` and `StallD` are always asserted together. Holding only one corrupts the instruction stream (§18, Note 6).

**What "done" looks like for this block:**

- everything from the single-cycle spec's test list
- with `StallF = 1`, drive several different `PCNext` values on consecutive cycles. `PCOut` must not change.
- deassert `StallF`. The next `PCNext` value must be captured on the following edge.
- assert `rst_n` low during a stall. `PCOut` must clear to `0`.

---

## 15. Block: `f_d_reg` — Updated Spec

**Ports — two added:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`StallD`|in|1|when `1`, all outputs hold their current values|
|`FlushD`|in|1|when `1`, all outputs clear to `0` on the next clock edge|

All other ports are unchanged from §3.

**Functional behavior — what changes:**

```
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)         {InstrD, PCD, PCPlus4D} <= '0;
    else if (FlushD)    {InstrD, PCD, PCPlus4D} <= '0;
    else if (!StallD)   {InstrD, PCD, PCPlus4D} <= {InstrF, PCF, PCPlus4F};
end
```

- **Priority: reset, then flush, then stall.** `FlushD` and `StallD` are never asserted together (§13). The order is fixed anyway so the module is defined for every input.
- **A flushed `f_d_reg` outputs `InstrD = 32'b0`.**
    - This decodes to `op = 7'b0000000`, which is not a recognized opcode.
    - `main_decoder`'s default-safe outputs then give `RegWrite = 0`, `MemWrite = 0`, `Branch = 0`, `PCSrc = 00`.
    - No separate bubble encoding is needed. §3 already relies on the same mechanism for reset.
- **`FlushD` is synchronous.** It is sampled at the clock edge. The instruction in Fetch during the cycle `FlushD` is high is the one replaced by zeros as it would otherwise be latched.

**What "done" looks like for this block:**

- everything from §3's test list
- with `StallD = 1`, drive different `InstrF` values. All three outputs must hold.
- with `FlushD = 1`, all three outputs must clear to `0` one edge later, regardless of inputs.
- with both asserted, the flush wins.

---

## 16. Block: `d_e_reg` — Updated Spec

**Ports — added:**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`Rs1D`|in|5|`InstrD[19:15]`, tapped separately from `regfile.A1`|
|`Rs2D`|in|5|`InstrD[24:20]`, tapped separately from `regfile.A2`|
|`FlushE`|in|1|when `1`, all outputs clear to `0` on the next clock edge|
|`Rs1E`|out|5|latched|
|`Rs2E`|out|5|latched|

All other ports are unchanged from §4.

**Functional behavior — what changes:**

```
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)        begin /* every output <= '0 */ end
    else if (FlushE)   begin /* every output <= '0 */ end
    else               begin /* every output <= its same-named D-stage input */ end
end
```

- **Why `Rs1E`/`Rs2E` are new.**
    - Every register number pipelined so far was a destination: `RdD → RdE → RdM → RdW`.
    - Forwarding compares the _source_ register numbers of the instruction in Execute against `RdM`/`RdW`.
    - `regfile` used `rs1`/`rs2` in Decode to read `RD1`/`RD2`. That does not make them available in Execute.
- **`Rs1E`/`Rs2E` stop here.** Nothing in Memory or Writeback reads them, so `e_m_reg` and `m_w_reg` do not carry them.
- **`FlushE` clears every field.**
    - `RegWriteE` and `MemWriteE` clear so the bubble cannot change architectural state.
    - `PCSrcE` and `BranchE` clear so a flushed wrong-path `jal`, `jalr`, or branch cannot trigger a second redirect.
    - `RdE`, `Rs1E`, `Rs2E` clear so the bubble cannot match any forwarding or stall comparison.
    - Clearing every field is what reset already does, and guarantees none is missed.
- `FlushE` has two causes (§13): a load-use stall and a redirect. The register does not distinguish them.
- `FlushE` is synchronous, like `FlushD`.

**What "done" looks like for this block:**

- everything from §4's test list
- `Rs1E`/`Rs2E` track `Rs1D`/`Rs2D` one cycle later.
- with `FlushE = 1`, every output clears to `0` one edge later, regardless of inputs.
- specifically: drive `PCSrcD = 01` and `BranchD = 1` while asserting `FlushE`. Both outputs must be `0`.

---

## 17. Top-Level Integration (`rv32_top`) — Updated Spec for Hazard Handling

**New instantiation:** `hazard_unit`, connected as follows.

|`hazard_unit` port|Connected to|
|---|---|
|`Rs1D`|`InstrD[19:15]`|
|`Rs2D`|`InstrD[24:20]`|
|`Rs1E`, `Rs2E`|`d_e_reg.Rs1E`, `d_e_reg.Rs2E`|
|`RdE`|`d_e_reg.RdE`|
|`RegWriteE`|`d_e_reg.RegWriteE`|
|`RdM`, `RdW`|`e_m_reg.RdM`, `m_w_reg.RdW`|
|`RegWriteM`, `RegWriteW`|`e_m_reg.RegWriteM`, `m_w_reg.RegWriteW`|
|`ResultSrcE`|`d_e_reg.ResultSrcE`|
|`PCNextSelE`|the resolved select from §8|
|`ForwardAE`, `ForwardBE`|drive the forwarding muxes below|
|`StallF`|`pc.StallF`|
|`StallD`|`f_d_reg.StallD`|
|`FlushD`|`f_d_reg.FlushD`|
|`FlushE`|`d_e_reg.FlushE`|

`rv32_top` has a parameter `FORWARDING` (default `1`) that it passes to `hazard_unit` (§13).

**New taps feeding `d_e_reg`:** `.Rs1D(InstrD[19:15])` and `.Rs2D(InstrD[24:20])`. These are the same bit slices already feeding `regfile.A1`/`A2`, routed to a second destination.

**Execute stage — replaces §8's `SrcAE`/`SrcBE` assigns:**

```
FwdDataM = (ResultSrcM == 2'b10) ? ImmExtM  :
           (ResultSrcM == 2'b11) ? PCPlus4M :
                                    ALUResultM;

FwdRD1E  = (ForwardAE == 2'b10) ? FwdDataM :
           (ForwardAE == 2'b01) ? ResultW  :
                                   RD1E;

FwdRD2E  = (ForwardBE == 2'b10) ? FwdDataM :
           (ForwardBE == 2'b01) ? ResultW  :
                                   RD2E;

SrcAE      = ALUSrcAE ? PCE     : FwdRD1E;
SrcBE      = ALUSrcE  ? ImmExtE : FwdRD2E;
WriteDataE = FwdRD2E;
```

**`FwdDataM` source table:**

|`ResultSrcM`|Instruction in Memory|Value it writes back|`FwdDataM`|
|---|---|---|---|
|`00`|R-type, I-type ALU, `auipc`|`ALUResultM`|`ALUResultM`|
|`01`|`lw`|`ReadData`, not available yet|not forwarded (see below)|
|`10`|`lui`|`ImmExtM`|`ImmExtM`|
|`11`|`jal`, `jalr`|`PCPlus4M`|`PCPlus4M`|

- For `ResultSrcM = 01` the mux outputs `ALUResultM`, which is a don't-care. The load-use stall guarantees no live consumer reaches Execute with a load in Memory (§13).
- The `11` row is included so the mux is correct for any producer. A live consumer cannot reach Execute one cycle behind a `jal` or `jalr`, because two wrong-path instructions are flushed between them.

**Two other changes in the Execute stage:**

- `alu.SrcA` and `alu.SrcB` still connect to `SrcAE` and `SrcBE`. Their definitions changed, their connections did not.
- `e_m_reg.WriteDataE` connects to `FwdRD2E` instead of `RD2E`. §5 describes `WriteDataE` as `RD2E` passed straight through. With forwarding it is the forwarded value, because `sw`'s store data goes stale in the same cases an ALU operand does.

**Unchanged:** `PCTargetE = PCE + ImmExtE`, the branch-taken table, `takenE`, and `PCNextSelE` from §8. They now read `ZeroE`/`ALUResultE[0]` from an ALU fed by forwarded operands. A branch comparing a register written one or two instructions earlier now gets the correct value.

**Load-use stall trace.** `lw x3,0(x1)` (A), `add x5,x3,x4` (B), a third instruction (C):

|Instruction|1|2|3|4|5|6|7|
|---|---|---|---|---|---|---|---|
|`lw x3,0(x1)` (A)|F|D|E|M|W|||
|`add x5,x3,x4` (B)||F|D|D (held)|E|M|W|
|third instruction (C)|||F|F (again)|D|E|M|

|Cycle|`lwStall`|`StallF`, `StallD`|`FlushE`|What happens|
|---|---|---|---|---|
|3|1|1|1|`Rs1D = 3 == RdE` and `ResultSrcE = 01`. `pc` and `f_d_reg` hold. B enters Execute as a bubble.|
|4|0|0|0|Execute holds the bubble, so `ResultSrcE = 00`. B is still in Decode. C is fetched again.|
|5|0|0|0|`Rs1E = 3 == RdW` and `RegWriteW = 1`, so `ForwardAE = 01` and `SrcAE = ResultW`.|

All other cycles: all three signals are `0`.

**Taken-branch flush trace.** `beq` (A), two wrong-path instructions (B, C), and the target (T):

|Instruction|1|2|3|4|5|6|
|---|---|---|---|---|---|---|
|`beq` (A)|F|D|E (taken)|M|W||
|wrong path (B)||F|D|flushed|||
|wrong path (C)|||F|flushed|||
|target (T)||||F|D|E|

- Cycle 3: `PCNextSelE = 01`, `FlushD = 1`, `FlushE = 1`. All other cycles: `00`, `0`, `0`.
- `FlushE` replaces B (in Decode) with a bubble as it enters Execute.
- `FlushD` replaces C (in Fetch) with `InstrD = 0` as it enters Decode.
- `pc` loads the target address, so T is fetched in cycle 4.

**What "done" looks like for the integrated core.**

The no-hazard integration test from §8 must still pass unchanged. It is the regression check that forwarding, stall, and flush do not alter behavior when no hazard is present.

Then add directed tests. Each checks final register or memory state against a hand-computed value:

- **Forwarding, gap 1, both operands:** `add x3,x1,x2` immediately followed by `sub x5,x3,x4`, and by `sub x6,x4,x3`.
- **Forwarding, gap 2:** one independent instruction between producer and consumer.
- **Memory-vs-Writeback priority:** `addi x3,x0,1` / `addi x3,x0,2` / `add x5,x3,x0` gives `x5 = 2`.
- **`x0` guard:** `addi x0,x0,5` / `add x5,x0,x0` gives `x5 = 0`.
- **`FwdDataM` from `lui`:** `lui x5,0x12345` / `add x6,x5,x0` gives `x6 = 0x12345000`.
- **Store-data forwarding:** `addi x5,x0,7` / `sw x5,0(x0)` / `lw x6,0(x0)` gives `x6 = 7`.
- **False match on I-type immediate bits:** `addi x5,x0,100` / `addi x6,x0,5` gives `x6 = 5`.
    - The second instruction's `Instr[24:20]` is `5`, equal to `RdM`, so `ForwardBE = 10` fires by accident.
    - Correct mux ordering ignores it.
- **False match on `auipc`'s `Instr[19:15]`:** `addi x5,x0,100` / `auipc x6,0x28` gives `x6 = PC + 0x28000`. The value `0x28` puts `5` in `Instr[19:15]`.
- **Load-use, `rs1` and `rs2`:** `lw x5,0(x0)` immediately followed by `add x6,x5,x0`, and by `add x6,x0,x5`. Check the result and that exactly one stall cycle occurs.
- **Load, gap 2:** `lw` / independent instruction / consumer. Correct result, no stall.
- **Branch operand from a load:** `lw x5,0(x0)` immediately followed by `beq x5,x0,target`. Stall, then the correct taken or not-taken outcome.
- **Taken branch flush:** `beq x0,x0,+12` followed by two instructions that write distinct registers. Both registers stay unchanged. The target executes.
- **Not-taken branch:** following instructions execute normally, no flush.
- **`jal` and `jalr`:**
    - wrong-path instructions after each do not write registers
    - the link register holds `PCPlus4`
    - for `jalr`, a computed target with bit 0 set lands on the bit-cleared address
- **Redirect on a wrong path:** a taken `beq` immediately followed by a `jal`. Only the `beq`'s target runs. The `jal`'s link register is not written. This confirms `FlushE` cleared `PCSrcE`.

---

## 18. Hazard-Specific Failure-Mode Notes

**Note 1 — applying forwarding after the `ALUSrcE`/`ALUSrcAE` muxes instead of before.**

- Wrong form: `SrcBE = (ForwardBE == 10) ? FwdDataM : ... : (ALUSrcE ? ImmExtE : RD2E)`. A forward can override the immediate.
- Example: `addi x5,x0,100` then `addi x6,x0,5`. The second instruction's `Instr[24:20]` is `5`, so `Rs2E = 5 == RdM` and `ForwardBE = 10`. The immediate `5` is replaced by `100`.
- It fails silently, and only when an immediate's low five bits equal the previous instruction's destination register.
- The same applies to `auipc` and `Instr[19:15]`.
- Fix: forwarding produces `FwdRD1E`/`FwdRD2E` first. The existing muxes then choose between those and `PCE`/`ImmExtE`.

**Note 2 — leaving `WriteDataE` connected to raw `RD2E`.**

- The ALU operand path does not cover `sw`'s store data.
- `addi x5,x0,7` followed immediately by `sw x5,0(x0)` stores a stale `x5` unless `WriteDataE = FwdRD2E`.

**Note 3 — forwarding plain `ALUResultM` from Memory.**

- Correct only when the instruction in Memory writes back its ALU result.
- For `lui x5,0x12345` followed immediately by `add x6,x5,x0`, `ALUResultM` is whatever the ALU produced with unused operands, not `0x12345000`.
- The forwarded source must be `FwdDataM`, selected by `ResultSrcM`.

**Note 4 — flushing `d_e_reg` by clearing only some fields.**

- Clearing `RegWriteE` and `MemWriteE` stops a wrong-path instruction from writing state, but not from redirecting the PC.
- A wrong-path `jal` still carrying `PCSrcE = 01` produces a second, wrong `PCNextSelE` the next cycle.
- Clear every field, as reset does.

**Note 5 — dropping the `!= 0` guards on `RdM`/`RdW`.**

- Without them, any instruction whose destination field is `x0` can forward a value into a later instruction that reads `x0`.
- `x0` must always read `0`.

**Note 6 — holding only one of `pc` and `f_d_reg` during a stall.**

- If `pc` advances while `f_d_reg` holds, the instruction fetched during the stall cycle is lost.
- If `f_d_reg` advances while `pc` holds, the instruction in Decode executes and is also fetched again.
- `StallF` and `StallD` must always be asserted together.

**Note 7 — comparing the wrong stage pair.**

- Stall check: `Rs1D`/`Rs2D` against `RdE`.
- Forwarding check: `Rs1E`/`Rs2E` against `RdM`/`RdW`.
- Swapping them compiles and lints clean, and detects the wrong hazard.

**Note 8 — conservative behaviors that are not bugs.**

- `lwStall` compares register-number fields without checking whether the instruction in Decode actually uses them. An instruction whose `Instr[24:20]` bits are immediate data can trigger a one-cycle stall it did not need.
- A `sw` immediately after a `lw` of its store-data register also stalls, though forwarding from Writeback into Memory could avoid it.
- Both cost one cycle and give correct results.
- Do not "fix" these when debugging a failing test.

**Note 9 — a don't-care (X) control value that crosses a pipeline register can make a stall or flush decision X.**

- A don't-care is harmless where nothing reads it. It is not harmless once it travels through a pipeline register into a hazard condition.
- Concrete case: `sw` and branches carried `ResultSrc = xx`, because `RegWrite = 0` makes it irrelevant to writeback. Their `Instr[11:7]` field is not a destination register either. It holds immediate bits (`imm[4:0]` for `sw`).
- If those bits equalled the next instruction's `Rs1D`/`Rs2D`, `lwStall = (match) && (ResultSrcE == 01) && ...` evaluated `1 && X`, so `lwStall` was X.
- Example: `sw x0,5(x0)` followed by `add x6,x5,x0`. The `sw`'s `Instr[11:7]` is `5`.
- In simulation `StallD = X` made `f_d_reg` hold (`else if (!StallD)` is false for X), while `FlushE = X` meant `d_e_reg` did not flush (`else if (FlushE)` is false for X). The consumer entered Execute and also stayed in Decode, so it executed twice.
  - That is harmless for `add x6,x5,x0` and wrong for `addi x5,x5,1`.
  - In silicon the result depends on how synthesis resolves the X, so it can differ from simulation.
- Fix, both parts:
    - Define every pipelined control output. `main_decoder` drives `0` instead of `x`/`xx`/`xxx` for every functionally don't-care output (see the decoder tables in the single-cycle specs).
    - Qualify load detection with `RegWriteE`.
- Regression check: `tb_hazard.sv` fails any test in which a `hazard_unit` input or output is X/Z on any cycle after reset.
  - It covers the inputs too. `ResultSrcE` was X while `lwStall` stayed defined, and that is how the cause was found.

---

## 19. Hazard Control Signal Reference

|Signal|Width|Produced by|Meaning|
|---|---|---|---|
|`ForwardAE`|2|`hazard_unit`|`SrcA` register-value select: `00` = `RD1E`, `01` = `ResultW`, `10` = `FwdDataM`|
|`ForwardBE`|2|`hazard_unit`|`SrcB` register-value select: `00` = `RD2E`, `01` = `ResultW`, `10` = `FwdDataM`|
|`FwdDataM`|32|top-level mux on `ResultSrcM`|value the instruction in Memory will write back: `ImmExtM` (`lui`), `PCPlus4M` (`jal`/`jalr`), else `ALUResultM`|
|`FwdRD1E`, `FwdRD2E`|32|top-level forwarding muxes|register operand values after forwarding. They feed `SrcAE`/`SrcBE`. `FwdRD2E` also feeds `WriteDataE`|
|`Rs1D`, `Rs2D`|5|`InstrD[19:15]`, `InstrD[24:20]`|source register numbers in Decode, used by the stall check|
|`Rs1E`, `Rs2E`|5|`d_e_reg`|source register numbers in Execute, used by the forwarding check. Not pipelined past Execute|
|`lwStall`|1|`hazard_unit` (internal)|a load (`RegWriteE` and `ResultSrcE = 01`) is in Execute and its destination matches `Rs1D` or `Rs2D`|
|`redirectE`|1|`hazard_unit` (internal)|`PCNextSelE != 00`|
|`StallF`|1|`hazard_unit`|hold `pc`. Equal to `stallCond` (`lwStall` when `FORWARDING = 1`)|
|`StallD`|1|`hazard_unit`|hold `f_d_reg`. Equal to `stallCond` (`lwStall` when `FORWARDING = 1`)|
|`FlushD`|1|`hazard_unit`|clear `f_d_reg`. Equal to `redirectE`|
|`FlushE`|1|`hazard_unit`|clear `d_e_reg`. `stallCond` OR `redirectE`|

---

## 20. Signals Checklist (updated/new modules only)

|Block|Inputs|Outputs|Notes|
|---|---|---|---|
|`hazard_unit`|`Rs1D[4:0]`, `Rs2D[4:0]`, `Rs1E[4:0]`, `Rs2E[4:0]`, `RdE[4:0]`, `RdM[4:0]`, `RdW[4:0]`, `RegWriteE`, `RegWriteM`, `RegWriteW`, `ResultSrcE[1:0]`, `PCNextSelE[1:0]`|`ForwardAE[1:0]`, `ForwardBE[1:0]`, `StallF`, `StallD`, `FlushD`, `FlushE`|new. Combinational. Top-level sibling, not inside `control_unit`. Parameter `FORWARDING` (default 1)|
|`pc`|`clk`, `rst_n`, `PCNext[31:0]`, `StallF`|`PCOut[31:0]`|`StallF` added|
|`f_d_reg`|`clk`, `rst_n`, `StallD`, `FlushD`, `InstrF[31:0]`, `PCF[31:0]`, `PCPlus4F[31:0]`|`InstrD[31:0]`, `PCD[31:0]`, `PCPlus4D[31:0]`|`StallD`, `FlushD` added. Priority: reset, flush, stall|
|`d_e_reg`|every input in §11's row, plus `FlushE`, `Rs1D[4:0]`, `Rs2D[4:0]`|every output in §11's row, plus `Rs1E[4:0]`, `Rs2E[4:0]`|`FlushE` clears every output. `Rs1E`/`Rs2E` stop at Execute|
|`e_m_reg`|unchanged|unchanged|`WriteDataE` input now driven by `FwdRD2E`|
|top-level muxes|`FwdDataM` (3-way on `ResultSrcM`), `FwdRD1E`/`FwdRD2E` (3-way on `ForwardAE`/`ForwardBE`), `SrcAE`/`SrcBE` (existing 2-way, now fed by `FwdRD1E`/`FwdRD2E`)|n/a|see §17|