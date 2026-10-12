
**Scope of this document:** the datapath and control changes required to extend the Steps 1–4 core (`lw`, `sw`, 5 R-type ops, `beq`) to the full RV32I base instruction set: the remaining 5 R-type ops (`sll`, `srl`, `sra`, `xor`, `sltu`), the 9 I-type ALU immediates, the remaining 5 branches (`bne`, `blt`, `bge`, `bltu`, `bgeu`), `lui`, `auipc`, `jal`, `jalr`. Companion document to `rv32i_remaining_instructions_walkthrough.md`, which explains the reasoning behind each item below — this document is the reference tables and updated module specs only. `FENCE`, `ECALL`, `EBREAK` remain out of scope (decoded as no-ops, per the original project plan).

**Full instruction-class table, all opcodes now covered:**

|Class|op|Instructions|
|---|---|---|
|Load|`0000011`|`lw`|
|Store|`0100011`|`sw`|
|R-type|`0110011`|`add`, `sub`, `and`, `or`, `xor`, `sll`, `srl`, `sra`, `slt`, `sltu`|
|I-type ALU|`0010011`|`addi`, `slti`, `sltiu`, `xori`, `ori`, `andi`, `slli`, `srli`, `srai`|
|Branch|`1100011`|`beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`|
|Jump-and-link|`1101111`|`jal`|
|Jump-and-link-register|`1100111`|`jalr`|
|Upper immediate|`0110111`|`lui`|
|Add upper immediate to PC|`0010111`|`auipc`|

**Every signal that widens or is newly added, relative to the Steps 1–4 spec:**

|Signal|Steps 1–4|Now|Change|
|---|---|---|---|
|`ALUControl`|3 bits|4 bits|5 more ALU operations|
|`ImmSrc`|2 bits|3 bits|U-type and J-type added|
|`ResultSrc`|1 bit|2 bits|`ImmExt` and `PCPlus4` added as writeback sources|
|`PCSrc`|1 bit|2 bits|`jalr`'s ALU-based target added as a third `PCNext` source|
|`ALUSrcA`|—|1 bit, new|selects `RD1` (default) or `PC` (`auipc` only) for the ALU's first operand|
|ALU status to `control_unit`|`Zero` only|`Zero` and `ALUResult[0]`|`ALUResult[0]` needed for `blt`/`bge`/`bltu`/`bgeu`|

---

## 1. ALU (`alu`) — Updated Spec

**Ports:** `ALUControl` widens from `[2:0]` to `[3:0]`. All other ports unchanged (`SrcA[31:0]`, `SrcB[31:0]`, `ALUResult[31:0]`, `Zero`).

**Full `ALUControl` table, 10 operations:**

| ALUControl | Operation | Result                                                |
| ---------- | --------- | ----------------------------------------------------- |
| `0000`     | add       | `SrcA + SrcB`                                         |
| `0001`     | subtract  | `SrcA - SrcB`                                         |
| `0010`     | and       | `SrcA & SrcB`                                         |
| `0011`     | or        | `SrcA \| SrcB`                                        |
| `0100`     | sltu      | `(SrcA < SrcB) ? 32'd1 : 32'd0` (unsigned)            |
| `0101`     | slt       | `($signed(SrcA) < $signed(SrcB)) ? 32'd1 : 32'd0`     |
| `0110`     | sll       | `SrcA << SrcB[4:0]`                                   |
| `0111`     | srl       | `SrcA >> SrcB[4:0]` (logical, zero-fill)              |
| `1000`     | xor       | `SrcA ^ SrcB`                                         |
| `1001`     | sra       | `$signed(SrcA) >>> SrcB[4:0]` (arithmetic, sign-fill) |

**Migration note:** the five pre-existing codes (`add` through `slt`) keep their exact bit patterns, just written with one more leading `0` — no behavior change for any already-tested operation.

**Implementation detail — codes `1010`–`1111`:** the actual ALU (`ALU.sv`) is written as an `if/else if` chain terminating in a bare `else` that implements `sra`. This means every `ALUControl` code from `1010` through `1111` (unused/reserved, per the table above) also silently produces the `sra` result, not a defined "unused" output — there is no explicit reserved-code branch. This is harmless today only because the control unit never generates those codes; anyone extending `ALUControl` should replace the trailing `else` with an explicit `4'b1001` case before adding an 11th operation.

**Functional behavior, new operations:**

- `sltu`: identical shape to `slt`, no `$signed()` cast — plain unsigned comparison.
- `sll`/`srl`/`sra`: only `SrcB[4:0]` is read as the shift amount; `SrcB[31:5]` is not consulted regardless of contents.
- `sra` must sign-extend the vacated high bits; `srl` must zero-fill them. This is the one place in the ALU where the same two operands, same shift amount, produce different results depending solely on which operation is selected.

**What "done" looks like, new operations:** `sltu` tested against the same `0xFFFFFFFF`/`1` pair used for `slt`, confirming the two operations disagree (`slt`→`1`, `sltu`→`0`). `sll` tested with a known shift. `srl` and `sra` both tested on the same negative-valued operand (e.g. `0xFFFFFFF0`) with the same shift amount, confirming the two results differ in the upper bits exactly as expected. Confirm `SrcB` bits above `[4:0]` have no effect on any shift's result — vary them while holding `SrcB[4:0]` fixed and confirm `ALUResult` doesn't change.

---

## 2. Immediate Generator (`immediate_generator`) — Updated Spec

**Note:** implemented as module `immediate_generator` (not `imm_gen`).

**Ports:** `ImmSrc` widens from `[1:0]` to `[2:0]`. `instr`/`ImmExt` unchanged.

**Full `ImmSrc` table, 5 formats:**

|ImmSrc|Type|Bit reassembly (absolute `Instr[]` indices)|Used by|
|---|---|---|---|
|`000`|I|`{{20{Instr[31]}}, Instr[31:20]}`|`lw`, I-type ALU, `jalr`|
|`001`|S|`{{20{Instr[31]}}, Instr[31:25], Instr[11:7]}`|`sw`|
|`010`|B|`{{20{Instr[31]}}, Instr[7], Instr[30:25], Instr[11:8], 1'b0}`|branches|
|`011`|U|`{Instr[31:12], 12'b0}`|`lui`, `auipc`|
|`100`|J|`{{11{Instr[31]}}, Instr[31], Instr[19:12], Instr[20], Instr[30:21], 1'b0}`|`jal`|

`ImmSrc` codes `101`–`111` are unused/reserved. Actual RTL (`immediate_generator.sv`) drives `ImmExt = 32'bx` for these — an explicit "don't care," not a defined `0` default. Any future opcode reusing one of these codes must add a real case, not rely on this branch.

**U-type has no sign-extension replication** — the 20-bit field is placed directly at `ImmExt[31:12]` with `ImmExt[11:0]` zeroed. Whatever bit sits at `Instr[31]` is already occupying `ImmExt`'s own sign position once placed there, so no separate replication step is needed, unlike I/S/B/J.

**J-type replicates 11 bits, not 20** — the J-type immediate is a 21-bit signed value (`imm[20:0]`, with `imm[0]` always `0`), so sign-extending it to 32 bits requires `32-21=11` replicated bits, not the 20 used by the 12-bit I/S/B immediates.

**Local port-index mapping** (module's actual port is `instr[24:0]`, representing `Instr[31:7]`; local index = absolute index − 7): `Instr[31]→instr[24]`, `Instr[19:12]→instr[12:5]`, `Instr[20]→instr[13]`, `Instr[30:21]→instr[23:14]`, `Instr[31:12]→instr[24:5]`.

**What "done" looks like, new formats:** directed test for U-type and J-type, each against a hand-computed value, confirming correct placement and (for J-type) correct sign extension for both a positive and a negative offset.

---

## 3. Main Decoder (`main_decoder`) — Updated Spec

**Ports:** two new outputs — `ALUSrcA` (1 bit), and `ResultSrc`/`PCSrc` both widen from 1 bit to 2 bits each. `op` input and `RegWrite`/`ImmSrc`/`ALUSrc`/`MemWrite`/`Branch`/`ALUOp` outputs unchanged in role (`ImmSrc` widens per §2, `ALUOp` stays 2 bits).

**`PCSrc` as a Main-Decoder output, specifically:** this is the _opcode-forced_ value only — `00` for every instruction whose next-PC decision is not opcode-determined (including branches, where the real decision is runtime-dependent and resolved inside `control_unit`, §5), `01` forced for `jal`, `10` forced for `jalr`. `control_unit` combines this with the runtime branch-taken result (§5) to produce the final `PCSrc` driving the `PCNext` mux.

**Full Main Decoder truth table, all 9 opcodes:**

| Instruction(s) | op        | RegWrite | ImmSrc | ALUSrc | ALUSrcA | MemWrite | ResultSrc | Branch | PCSrc | ALUOp |
| -------------- | --------- | -------- | ------ | ------ | ------- | -------- | --------- | ------ | ----- | ----- |
| `lw`           | `0000011` | 1        | `000`  | 1      | 0       | 0        | `01`      | 0      | `00`  | `00`  |
| `sw`           | `0100011` | 0        | `001`  | 1      | 0       | 1        | `00`      | 0      | `00`  | `00`  |
| R-type         | `0110011` | 1        | `000`  | 0      | 0       | 0        | `00`      | 0      | `00`  | `10`  |
| I-type ALU     | `0010011` | 1        | `000`  | 1      | 0       | 0        | `00`      | 0      | `00`  | `10`  |
| Branch         | `1100011` | 0        | `010`  | 0      | 0       | 0        | `00`      | 1      | `00`  | `01`  |
| `jal`          | `1101111` | 1        | `100`  | 0      | 0       | 0        | `11`      | 0      | `01`  | `00`  |
| `jalr`         | `1100111` | 1        | `000`  | 1      | 0       | 0        | `11`      | 0      | `10`  | `00`  |
| `lui`          | `0110111` | 1        | `011`  | 0      | 0       | 0        | `10`      | 0      | `00`  | `00`  |
| `auipc`        | `0010111` | 1        | `011`  | 1      | 1       | 0        | `00`      | 0      | `00`  | `00`  |

No output is left as `x`. Entries that are functionally don't-care (`ResultSrc` on `sw`/branch, `ImmSrc` on R-type, `ALUSrc`/`ALUSrcA`/`ALUOp` on `jal`/`lui`) are driven to a defined `0`, because an `x` on a signal that crosses a pipeline register can reach a hazard decision (pipelined spec §18, Note 9). Nothing reads those values on those rows, so behavior is unchanged.

**Per-row notes for the new rows:**

- **I-type ALU**: `ImmSrc=000` (I-type, same encoding `lw` uses). `ResultSrc=00` — always the ALU result, never memory, since none of these 9 instructions touch `dmem`. `ALUOp=10` — same as R-type, since the exact operation depends on `funct3` (§4).
- **Branch (updated row)**: `ResultSrc=00` is functionally a don't-care (`RegWrite=0`, same reasoning as `sw`/original `beq`), defined rather than `xx`. `PCSrc=00` from this decoder — the actual `01`/`00` choice is resolved at runtime inside `control_unit`, not here.
- **`jal`**: `ALUSrc=0`, `ALUSrcA=0`, `ALUOp=00` — functionally don't-care (the ALU is not involved in computing `jal`'s target at all; the dedicated `PCTarget` adder handles it), driven to defined `0`s rather than `x`. `ResultSrc=11` selects `PCPlus4` (return address) as the writeback value. `PCSrc=01` forced — `jal` always redirects, decided purely from its opcode.
- **`jalr`**: `ALUSrc=1`, `ALUSrcA=0` — reuses the ALU exactly as `lw`/`sw` do, computing `rs1+imm`. `ResultSrc=11` (return address, same as `jal`). `PCSrc=10` forced — always redirects via the ALU's result (with bit 0 cleared at the `PCNext` mux, §6). `ALUOp=00` — this target computation is unconditionally addition, never ambiguous.
- **`lui`**: `ALUSrc=0`, `ALUSrcA=0`, `ALUOp=00` — functionally don't-care (the ALU is bypassed entirely), defined rather than `x`; the writeback value is `ImmExt` directly (`ResultSrc=10`).
- **`auipc`**: `ALUSrc=1` (select `ImmExt` for `SrcB`), `ALUSrcA=1` (select `PC`, not `RD1`, for `SrcA` — the only instruction that sets this bit). `ResultSrc=00` — unlike `lui`, `auipc` does go through the ALU.

---

## 4. ALU Decoder (`alu_decoder`) — Updated Spec

**Ports:** `ALUControl` output widens from `[2:0]` to `[3:0]`. `ALUOp[1:0]`, `funct3[2:0]`, `op5`, `funct7_5` inputs unchanged.

**`ALUOp=00` (always add):** unchanged — `funct3` still `x`, `ALUControl=0000` unconditionally. Covers `lw`, `sw`, `jalr`, `auipc`.

**`ALUOp=01` (branch) — now funct3-dependent, previously was not:**

|funct3|ALUControl|Instruction|
|---|---|---|
|`000`|`0001` (subtract)|`beq`|
|`001`|`0001` (subtract)|`bne`|
|`100`|`0101` (slt, signed)|`blt`|
|`101`|`0101` (slt, signed)|`bge`|
|`110`|`0100` (sltu, unsigned)|`bltu`|
|`111`|`0100` (sltu, unsigned)|`bgeu`|

**`ALUOp=10` (R-type / I-type ALU) — full table, both tie-break rules shown:**

|funct3|Extra bits consulted|ALUControl|Instructions|
|---|---|---|---|
|`000`|`{op5, funct7_5}`: `00`,`01`,`10`→add; `11`→subtract|`0000` / `0001`|`add`, `addi`, `sub`|
|`001`|none|`0110`|`sll`, `slli`|
|`010`|none|`0101`|`slt`, `slti`|
|`011`|none|`0100`|`sltu`, `sltiu`|
|`100`|none|`1000`|`xor`, `xori`|
|`101`|`funct7_5` alone, unconditionally (no `op5` gating)|`0111` / `1001`|`srl`, `srli`, `sra`, `srai`|
|`110`|none|`0011`|`or`, `ori`|
|`111`|none|`0010`|`and`, `andi`|

**The two tie-break rules are not interchangeable:** `funct3=000`'s ambiguity only resolves correctly by checking `op5` first, because `addi`'s I-type immediate field has no reserved bit at that position — `Instr[30]` there is ordinary data, meaningless unless `op5` confirms genuine R-type. `funct3=101`'s ambiguity resolves correctly by reading `funct7_5` alone, unconditionally, because RV32I's shift-immediate encoding deliberately reserves that exact bit as a real flag in both the R-type and I-type forms — there is no competing "immediate data" interpretation to guard against.

**What "done" looks like:** one directed test per row in both new tables (14 rows total across the two `ALUOp` values), each checked against its exact `ALUControl` output. Specifically confirm the `funct3=101` row does **not** consult `op5` — construct an `op5=0` (I-type) input with `funct7_5=1` under `ALUOp=10`, `funct3=101` and confirm `ALUControl=1001` (`srai`) results, not `0111` — this is the one row where naively reusing the `funct3=000` gating pattern would silently produce the wrong answer.

---

## 5. Control Unit (`control_unit`) — Updated Spec

**Ports:** one new input, `ALUResult0` (bit 0 of `ALUResult`, wired from `alu.ALUResult[0]`), alongside the existing `Zero` input. `RegWrite`, `ImmSrc` (3 bits now), `ALUSrc`, `ALUSrcA` (new), `MemWrite`, `ResultSrc` (2 bits now), `ALUControl` (4 bits now), `PCSrc` (2 bits now) as outputs — all pass through from `main_decoder`/`alu_decoder` except `PCSrc`, which this module's own logic finishes resolving.

**Internal branch-taken resolution, replacing the single `Branch & Zero` AND gate:**

|funct3|Taken condition|
|---|---|
|`000` (`beq`)|`Zero = 1`|
|`001` (`bne`)|`Zero = 0`|
|`100` (`blt`)|`ALUResult0 = 1`|
|`101` (`bge`)|`ALUResult0 = 0`|
|`110` (`bltu`)|`ALUResult0 = 1`|
|`111` (`bgeu`)|`ALUResult0 = 0`|

**Final `PCSrc` computation:** `final_PCSrc = (main_decoder_PCSrc != 2'b00) ? main_decoder_PCSrc : (Branch & taken) ? 2'b01 : 2'b00`. This is safe as a plain priority/OR structure because `main_decoder`'s own `PCSrc` output is `00` for every opcode where `Branch` can be `1` (branches never force a non-zero `PCSrc` from the Main Decoder table in §3) — there is no case where both the opcode-forced value and the runtime branch condition are simultaneously trying to drive different non-zero values.

**What "done" looks like:** directed test per branch type (6 rows above), confirming `PCSrc` resolves to `01` or `00` correctly given controlled `Zero`/`ALUResult0` values. Separately confirm `jal`/`jalr` produce `PCSrc=01`/`10` regardless of what `Zero`/`ALUResult0` happen to be — these two should never depend on ALU status at all.

---

## 6. Top-Level Integration — Updated Spec

**New mux — `ALUSrcA`:**

```
SrcA = ALUSrcA ? PC : RD1
```

Replaces the previous fixed connection `SrcA = RD1`. This is a new signal reaching the ALU's first input that didn't exist in the Steps 1–4 datapath — `PC`, previously only routed to `imem` and the `PCTarget`/`PCPlus4` adders.

**`Result` mux widens from 2:1 to 4:1:**

```
Result = (ResultSrc == 2'b00) ? ALUResult :
         (ResultSrc == 2'b01) ? ReadData  :
         (ResultSrc == 2'b10) ? ImmExt    :
                                 PCPlus4;
```

**`PCNext` mux widens from 2:1 to 3:1, with a new bit-clearing step for the `jalr` path:**

```
PCNext = (PCSrc == 2'b00) ? PCPlus4  :
         (PCSrc == 2'b01) ? PCTarget :
                             {ALUResult[31:1], 1'b0};
```

The `{ALUResult[31:1], 1'b0}` construction is the entire "clear bit 0" operation for `jalr` — a plain bit-concatenation, not a subtraction or masking operation, forcing the least significant bit to `0` while passing every other bit through unchanged.

**New direct connection:** `alu.ALUResult[0]` → `control_unit.ALUResult0` (alongside the existing `alu.Zero` → `control_unit.Zero`).

**No change** to `PCPlus4`, `PCTarget` adders, or `dmem`/`imem` connections — `jal` reuses `PCTarget` via `ImmSrc=100`; `jalr` reuses the ALU via `ALUSrc=1`/`ALUSrcA=0`, with only the final bit-clear being new.

**What "done" looks like for the integrated core:** extend the Steps 1–4 integration test program to include every instruction class in this document at least once, including at least one instance of each of the 6 branch types (not just `beq`), at least one `jal`/`jalr` pair exercising a call-and-return sequence, and both `lui` and `auipc` establishing register values used by later instructions. Step cycle by cycle exactly as before, now also checking `PCSrc`'s resolved value and `Result`'s selected source at each cycle, not just the final register/memory state.

---

## 7. Decode and Integration Failure-Mode Notes

**Note 1 — applying the `funct3=000` tie-break pattern to `funct3=101`.** Already covered in full in §4 — repeated here because it's the single most likely copy-paste error in this extension, since the two rows look structurally similar (`funct3` value, `funct7_5`, ALU operation pair) but require different logic.

**Note 2 — `ALUOp=01` losing its `funct3`-independence silently.** If the ALU Decoder's branch handling is extended by editing the existing `ALUOp=01` case without adding a `funct3` check, every branch (`bne` through `bgeu`) silently computes a subtraction instead of the comparison it actually needs. This produces no compiler warning — `ALUControl=0001` is a perfectly valid code, just the wrong one for 4 of the 6 branch types. The directed test in §4 (one row per branch type) is what catches this, not lint.

**Note 3 — `ResultSrc`/`PCSrc` widened in one module but not another.** Both signals grow from 1 bit to 2 bits across three places each: the `main_decoder` output port, the `control_unit` pass-through (and, for `PCSrc`, the resolution logic in §5), and the top-level mux. A width left at 1 bit in any one of these three locations produces a truncation/expansion warning at the connection boundary — the same class of warning seen when the register file's storage was first declared with the wrong dimensionality, just recurring here across a wider signal instead of a memory array.

**Note 4 — the `jalr` bit-0-clear, forgotten.** Omitting `{ALUResult[31:1], 1'b0}` and using `ALUResult` directly as `jalr`'s target produces a core that appears to work correctly on any test program where `rs1+imm` happens to already be even — which, depending on how test addresses are chosen, may be most or all of an initial test program. The bug only surfaces on a `jalr` whose computed target is odd, making it a class of bug that can pass an incomplete test suite and still be present. Worth deliberately constructing at least one `jalr` test case where `rs1+imm` is odd, specifically to exercise this bit-clear.

---

## 8. Full Consolidated Control Signal Reference

|Signal|Width|Produced by|Meaning|
|---|---|---|---|
|`RegWrite`|1|Main Decoder|write enable, register file|
|`ImmSrc`|3|Main Decoder|immediate format (`000`=I, `001`=S, `010`=B, `011`=U, `100`=J)|
|`ALUSrc`|1|Main Decoder|ALU `SrcB`: register (`0`) or immediate (`1`)|
|`ALUSrcA`|1|Main Decoder|ALU `SrcA`: `RD1` (`0`) or `PC` (`1`, `auipc` only)|
|`MemWrite`|1|Main Decoder|write enable, data memory|
|`ResultSrc`|2|Main Decoder|writeback source (`00`=ALU, `01`=memory, `10`=`ImmExt`, `11`=`PCPlus4`)|
|`Branch`|1|Main Decoder — internal to Control Unit only|flags a branch opcode to the runtime taken-resolution logic|
|`ALUOp`|2|Main Decoder — internal to Control Unit only|how the ALU Decoder should resolve `ALUControl`|
|`ALUControl`|4|ALU Decoder|final ALU operation select, 10 operations|
|`Zero`|1|ALU|`1` iff `ALUResult==0`; feeds Control Unit|
|`ALUResult0`|1|ALU (`ALUResult[0]`)|signed/unsigned less-than result bit; feeds Control Unit|
|`PCSrc`|2|Control Unit (Main Decoder's forced value, or runtime branch resolution)|next-PC mux select (`00`=`PCPlus4`, `01`=`PCTarget`, `10`=`jalr` target)|

---

## 9. Signals Checklist (updated ports)

|Block|Inputs|Outputs|Notes|
|---|---|---|---|
|`alu`|`SrcA[31:0]`, `SrcB[31:0]`, `ALUControl[3:0]`|`ALUResult[31:0]`, `Zero`|`ALUControl` widened|
|`main_decoder`|`op[6:0]`|`RegWrite`, `ImmSrc[2:0]`, `ALUSrc`, `ALUSrcA`, `MemWrite`, `ResultSrc[1:0]`, `Branch`, `PCSrc[1:0]`, `ALUOp[1:0]`|`ALUSrcA` new; `ImmSrc`/`ResultSrc`/`PCSrc` widened|
|`alu_decoder`|`ALUOp[1:0]`, `funct3[2:0]`, `op5`, `funct7_5`|`ALUControl[3:0]`|`ALUOp=01` now funct3-dependent|
|`control_unit`|`op[6:0]`, `funct3[2:0]`, `funct7_5`, `Zero`, `ALUResult0`|`RegWrite`, `ImmSrc[2:0]`, `ALUSrc`, `ALUSrcA`, `MemWrite`, `ResultSrc[1:0]`, `ALUControl[3:0]`, `PCSrc[1:0]`|`ALUResult0` new input|
|`immediate_generator`|`instr[24:0]`, `ImmSrc[2:0]`|`ImmExt[31:0]`|`ImmSrc` widened, 2 new formats|
|top-level muxes|`ALUSrcA` (new mux), `ResultSrc` (4:1), `PCSrc` (3:1, with bit-0-clear for `jalr`)|—|see §6|