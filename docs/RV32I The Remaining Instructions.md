
This continues directly from the existing `lw`/`sw`/R-type(5)/`beq` datapath. Same module boundaries, same signal names. Nothing here is quoted from Harris & Harris — it's built from the same design principles, applied to what's left.

**State of the datapath before this document, exactly as built:**

- `ALUControl`: 3 bits. Codes in use: `000` add, `001` subtract, `010` and, `011` or, `101` slt.
- `ImmSrc`: 2 bits. Codes in use: `00` I-type, `01` S-type, `10` B-type. Code `11` unused.
- `ResultSrc`: 1 bit. `0` selects `ALUResult`, `1` selects `ReadData`.
- `PCSrc`: 1 bit. `0` selects `PCPlus4`, `1` selects `PCTarget` (`PC + ImmExt`), driven by `Branch & Zero`.
- The ALU's first operand, `SrcA`, is wired directly to `RD1`. No mux — every instruction so far uses `RD1` there.

Every change below is a change to one of these five things, or a new instruction that reuses them unchanged.

---

## 0. Full names of every mnemonic

**Already built (baseline):**

|Mnemonic|Full name|
|---|---|
|`lw`|Load Word|
|`sw`|Store Word|
|`add`|Add|
|`sub`|Subtract|
|`and`|AND|
|`or`|OR|
|`slt`|Set Less Than|
|`beq`|Branch if Equal|

**Covered in this document:**

|Mnemonic|Full name|
|---|---|
|`sltu`|Set Less Than Unsigned|
|`sll`|Shift Left Logical|
|`srl`|Shift Right Logical|
|`sra`|Shift Right Arithmetic|
|`xor`|Exclusive OR|
|`addi`|Add Immediate|
|`slti`|Set Less Than Immediate|
|`sltiu`|Set Less Than Immediate Unsigned|
|`xori`|Exclusive OR Immediate|
|`ori`|OR Immediate|
|`andi`|AND Immediate|
|`slli`|Shift Left Logical Immediate|
|`srli`|Shift Right Logical Immediate|
|`srai`|Shift Right Arithmetic Immediate|
|`bne`|Branch if Not Equal|
|`blt`|Branch if Less Than|
|`bge`|Branch if Greater than or Equal|
|`bltu`|Branch if Less Than Unsigned|
|`bgeu`|Branch if Greater than or Equal Unsigned|
|`lui`|Load Upper Immediate|
|`auipc`|Add Upper Immediate to PC|
|`jal`|Jump And Link|
|`jalr`|Jump And Link Register|

The `i` suffix means "immediate" — one operand is an encoded constant instead of a register. The `u` suffix on comparisons and branches means "unsigned" — same operation, unsigned interpretation of the bits.

---

## 1. R-type: `sltu`, `sll`, `srl`, `sra`, `xor`

**Definition.** Same opcode as the existing R-type instructions, `0110011`. Same control signals: `RegWrite=1`, `ALUSrc=0`, `MemWrite=0`, `ResultSrc=00`, `Branch=0`, `ALUOp=10`. Both operands come from the register file, exactly as with `add`/`sub`/`and`/`or`/`slt`. Nothing changes outside the ALU.

**Why `ALUControl` must widen.** The five existing operations use codes `000`, `001`, `010`, `011`, `101`. In a 3-bit space, the only unused codes are `100`, `110`, `111` — three slots. Five new operations don't fit in three slots. `ALUControl` widens from 3 bits to 4 bits. Every existing code keeps its exact bit pattern with a `0` prepended, so no existing behavior changes — only the port width changes.

|ALUControl|Operation|
|---|---|
|`0000`|add|
|`0001`|subtract|
|`0010`|and|
|`0011`|or|
|`0100`|sltu|
|`0101`|slt|
|`0110`|sll|
|`0111`|srl|
|`1000`|xor|
|`1001`|sra|

**`sltu`.** `ALUResult = (SrcA < SrcB) ? 32'd1 : 32'd0`, using SystemVerilog's default unsigned comparison — no `$signed()` cast. `slt` and `sltu` are not the same comparison run on different-typed inputs; they are two separate comparison circuits, selected by two separate `ALUControl` codes.

Example: `SrcA = 32'hFFFFFFFF`, `SrcB = 32'd1`. `slt` (signed): `−1 < 1` → true → result `1`. `sltu` (unsigned): `4294967295 < 1` → false → result `0`. Same bits, opposite results, because the two codes select different comparison logic.

**`sll`, `srl`, `sra`.** `sll`: `ALUResult = SrcA << SrcB[4:0]`. `srl`: `ALUResult = SrcA >> SrcB[4:0]` — logical, zero-fill. `sra`: `ALUResult = SrcA >>> SrcB[4:0]` — arithmetic, sign-extend. SystemVerilog's `>>>` only sign-extends if `SrcA` is signed.

**Why `>>` and `>>>` are not "logical" and "arithmetic" by themselves.** `>>` is always zero-fill, regardless of the operand's type — casting the operand signed has no effect on `>>`. `>>>`'s fill behavior depends on the operand's declared or cast type: if the operand is unsigned, `>>>` zero-fills, identical to `>>`; only if the operand is signed does `>>>` sign-extend, copying the original top bit into the vacated top bits. So `$signed(SrcA) >> SrcB[4:0]` still zero-fills — the `$signed()` cast is wasted on that operator, since `>>` never sign-extends no matter what. It is the _combination_ of operator and operand type that determines the fill, not either alone:

|Operator|Operand type|Fill|
|---|---|---|
|`>>`|signed or unsigned|zero|
|`>>>`|unsigned|zero|
|`>>>`|signed|sign-extend|

`sra`/`srai` require both: `>>>` as the operator, and `SrcA` cast signed. Either one alone gives zero-fill — the behavior of `srl`, not `sra`.

Only `SrcB[4:0]` is used as the shift amount. `SrcB[31:5]` is not zeroed and not checked — it is simply not connected to anything the shift operation reads, regardless of what bits are in it. A 32-bit register can only need a shift amount from `0` to `31`, which is exactly what 5 bits encode.

Example: `x1 = 5`. `slli x2, x1, 3` → shift amount `3` → `x2 = 5 << 3 = 40`.

Example, `srl` vs `sra`: `x1 = 32'hFFFFFFF0` (−16). `srli x2, x1, 2` (logical): `0xFFFFFFF0 >> 2`, zero-filled → `0x3FFFFFFC` (a large positive number). `srai x3, x1, 2` (arithmetic): `−16 >>> 2`, sign-extended → `−4 = 0xFFFFFFFC`. Same input, same shift amount, different result, because the two instructions select different right-shift circuits.

**Bit-level walkthrough.** `0xFFFFFFF0` is `1111 1111 1111 1111 1111 1111 1111 0000`. A right shift by 2 drops the bottom 2 bits and inserts 2 new bits at the top; the two shift types differ only in what those 2 new bits are.

`srl` inserts `0`s: `00` + `1111...111100` = `0011 1111 1111 1111 1111 1111 1111 1100` = `0x3FFFFFFC`. Bit 31 is now `0` → positive → `1,073,741,820`.

`sra` copies the original bit 31 (`1`) into the new bits: `11` + `1111...111100` = `1111 1111 1111 1111 1111 1111 1111 1100` = `0xFFFFFFFC`. Bit 31 is still `1` → negative. Invert (`00000003`), add `1` (`00000004`) → magnitude `4` → value `−4`, matching `⌊−16 / 4⌋ = −4`, the definition of arithmetic right shift.

Both shifts do the identical mechanical step — drop the bottom 2 bits, insert 2 at the top. `srl` always inserts `0`. `sra` copies whatever bit 31 was before the shift. That single difference in fill bits is why the two results land on opposite sides of zero.

---

## 2. I-type ALU immediates: `addi`, `slti`, `sltiu`, `xori`, `ori`, `andi`, `slli`, `srli`, `srai`

**Definition.** Opcode `0010011` — distinct from `lw`'s `0000011`. Both are I-type format. `ALUSrc=1`, using the exact I-type immediate path already built for `lw`.

**Main Decoder row:** `RegWrite=1`, `ImmSrc=00` (I-type), `ALUSrc=1`, `MemWrite=0`, `ResultSrc=00`, `Branch=0`, `ALUOp=10`.

**Why `slli`/`srli`/`srai` need no change to `imm_gen`.** The shift amount for these three instructions lives in `Instr[24:20]`. That field is already a subset of the I-type immediate field, `Instr[31:20]`. `imm_gen` already sign-extends `Instr[31:20]` into `ImmExt` for every I-type instruction, so `Instr[24:20]` already sits, unchanged, in `ImmExt[4:0]`. Since the ALU only reads `SrcB[4:0]` for shift amount (Section 1), `imm_gen`'s existing output is already correct for these three instructions. No new logic needed here.

**The `funct3=101` tie-break is not the same rule as the `funct3=000` tie-break.** For `add`/`sub`/`addi` (`funct3=000`), the existing rule checks `op[5]` before trusting `Instr[30]`: when `op[5]=0` (I-type), the instruction is forced to add, because `Instr[30]` is meaningless immediate data in `addi`, not a real tie-break bit. That rule does not carry over to `funct3=101`. For `srl`/`sra`/`srli`/`srai`, `Instr[30]` is real, meaningful data in both the R-type and I-type encodings — RV32I reserves this exact bit for this exact purpose in both forms. So for `funct3=101`, `Instr[30]` is read directly and unconditionally, with no `op[5]` check: `Instr[30]=0` → `srl`/`srli`, `Instr[30]=1` → `sra`/`srai`.

**ALU Decoder, `ALUOp=10`, full table:**

|funct3|Extra bits consulted|ALUControl|Instructions|
|---|---|---|---|
|`000`|`{op[5], Instr[30]}`: `00`,`01`,`10`→add; `11`→subtract|`0000` / `0001`|`add`, `addi`, `sub`|
|`001`|none|`0110`|`sll`, `slli`|
|`010`|none|`0101`|`slt`, `slti`|
|`011`|none|`0100`|`sltu`, `sltiu`|
|`100`|none|`1000`|`xor`, `xori`|
|`101`|`Instr[30]` alone, unconditionally|`0111` / `1001`|`srl`, `srli`, `sra`, `srai`|
|`110`|none|`0011`|`or`, `ori`|
|`111`|none|`0010`|`and`, `andi`|

---

## 3. Remaining branches: `bne`, `blt`, `bge`, `bltu`, `bgeu`

**Definition.** Same opcode as `beq`, `1100011`. Same B-type immediate. Same `Branch=1` flag. What differs per branch: which `ALUControl` code runs, and which result bit decides "taken."

**`bne`.** Same operation as `beq`: subtract, `ALUControl=0001`. Opposite polarity: taken when `Zero=0`, not `Zero=1`.

**`blt`/`bge`.** Reuse `slt`, `ALUControl=0101`. `ALUResult[0] = 1` when `SrcA < SrcB` signed, `0` otherwise. `blt` taken when `ALUResult[0]=1`. `bge` taken when `ALUResult[0]=0`.

**`bltu`/`bgeu`.** Same as `blt`/`bge`, but reuse `sltu`, `ALUControl=0100` — unsigned comparison.

|funct3|ALUControl|Taken condition|
|---|---|---|
|`000` (`beq`)|`0001`|`Zero=1`|
|`001` (`bne`)|`0001`|`Zero=0`|
|`100` (`blt`)|`0101`|`ALUResult[0]=1`|
|`101` (`bge`)|`0101`|`ALUResult[0]=0`|
|`110` (`bltu`)|`0100`|`ALUResult[0]=1`|
|`111` (`bgeu`)|`0100`|`ALUResult[0]=0`|

**Consequence for `control_unit`.** With only `beq`, the taken decision was `Branch & Zero` — one AND gate. With all six branches, the decision needs `funct3` as an input, not just `Zero`/`ALUResult[0]`, to pick the right row above. It is still combinational logic in the same place, just no longer a single gate.

Example: `x1 = 32'hFFFFFFFB` (−5), `x2 = 3`. `blt x1, x2, offset`: signed, `−5 < 3` → true → taken. `bltu x1, x2, offset`, same registers: unsigned, `0xFFFFFFFB < 3` → false (`0xFFFFFFFB` is a large unsigned value) → not taken. Same bits in both registers, opposite outcomes, because `blt` and `bltu` select different comparison circuits.

---

## 4. `lui` — Load Upper Immediate

**Definition.** Opcode `0110111`, U-type format. Writes a 20-bit immediate into the upper 20 bits of `rd`, with the lower 12 bits zeroed. `lui` does not use the ALU at all — this is not a computation, it's a direct immediate-to-register write.

**Why `ResultSrc` must widen.** Every prior instruction chose between exactly two writeback values: `ALUResult` or `ReadData` — one bit is enough for two choices. `lui`'s writeback value is a third, distinct value: `ImmExt` itself. One bit cannot select among three sources. `ResultSrc` widens to 2 bits, which gives four codes; three are assigned now, one (`11`) stays unused until Section 6.

|ResultSrc|Source|
|---|---|
|`00`|`ALUResult`|
|`01`|`ReadData`|
|`10`|`ImmExt`|

**Main Decoder row:** `RegWrite=1`, `ImmSrc=11` (U-type — the previously spare code in the existing 2-bit `ImmSrc` field), `ALUSrc=0` (functionally don't-care, driven to a defined `0` rather than `x`), `MemWrite=0`, `ResultSrc=10`, `Branch=0`.

Example: `lui x5, 0x12345` → `ImmExt = 0x12345000` (the field `0x12345` placed in bits `[31:12]`, zeros in `[11:0]`) → `x5 = 0x12345000` directly, with no ALU step.

---

## 5. `auipc` — Add Upper Immediate to PC

**Definition.** Opcode `0010111`, U-type format, same immediate shape as `lui`. Computes `PC + ImmExt` and writes the result into `rd`. Unlike `lui`, `auipc` does go through the ALU.

**Why a new mux, `ALUSrcA`, is required.** `auipc`'s computation is `PC + ImmExt`. Every instruction up to this point has `SrcA` wired directly to `RD1` — there has never been a case where the ALU's first operand is anything else. `auipc` needs `PC` in that position instead of `RD1`. This is not a `ResultSrc` question — it's a new input path into the ALU. A new mux, `ALUSrcA`, is added ahead of the ALU's `SrcA` port:

|ALUSrcA|Source|
|---|---|
|`0`|`RD1`|
|`1`|`PC`|

`SrcA = ALUSrcA ? PC : RD1`.

**Main Decoder row:** `RegWrite=1`, `ImmSrc=11` (U-type), `ALUSrc=1` (`SrcB = ImmExt`), `ALUSrcA=1` (`SrcA = PC`), `MemWrite=0`, `ResultSrc=00` (`ALUResult`), `Branch=0`, `ALUOp=00` (add).

Example: `PC = 0x2000`. `auipc x6, 0x1` → `ImmExt = 0x00001000` → `ALUResult = 0x2000 + 0x1000 = 0x3000` → `x6 = 0x3000`.

---

## 6. `jal` — Jump and Link

**Definition.** Opcode `1101111`, J-type format. Unconditionally redirects the PC to `PC + ImmExt`, using the same `PCTarget` adder already built for branches — that adder computes `PC + ImmExt` regardless of which immediate format produced `ImmExt`. Writes `PCPlus4` (the return address) into `rd`.

**Why `ImmSrc` must widen.** Before `jal`, `ImmSrc` needs 2 bits for four formats: I (`00`), S (`01`), B (`10`), U (`11`) — all four codes now used. J-type is a fifth distinct format. Four codes are not enough for five formats. `ImmSrc` widens to 3 bits.

|ImmSrc|Format|Used by|
|---|---|---|
|`000`|I|`lw`, I-type ALU, `jalr`|
|`001`|S|`sw`|
|`010`|B|branches|
|`011`|U|`lui`, `auipc`|
|`100`|J|`jal`|

**Why `ResultSrc`'s unused code now gets assigned.** `jal` needs `PCPlus4` as the writeback value — a fourth distinct source. The spare code from Section 4, `11`, is assigned to it. No further widening; `ResultSrc` stays at 2 bits.

|ResultSrc|Source|
|---|---|
|`00`|`ALUResult`|
|`01`|`ReadData`|
|`10`|`ImmExt`|
|`11`|`PCPlus4`|

**`PCSrc` does not need to change yet.** `jal` uses the same two `PCNext` sources that already exist — `PCPlus4` and `PCTarget` — it just forces `PCTarget` unconditionally rather than depending on `Zero`. This is opcode-determined: `control_unit` recognizes the `jal` opcode and outputs `PCSrc=1` directly, with no comparison involved, unlike an actual branch where `PCSrc` depends on `Zero` at runtime.

**Main Decoder row:** `RegWrite=1`, `ImmSrc=100` (J-type), `ALUSrc=0`/`ALUSrcA=0` (functionally don't-care, driven to defined `0`s rather than `x`: the ALU is not involved — `PCTarget` is the dedicated adder), `MemWrite=0`, `ResultSrc=11` (`PCPlus4`), `PCSrc` forced to `1`.

Example: `PC = 0x1000`. `jal x1, +16`: `ImmExt = 16` → `PCTarget = 0x1000 + 16 = 0x1010` → next PC is `0x1010` unconditionally → `x1 = PCPlus4 = 0x1004`.

---

## 7. `jalr` — Jump and Link Register

**Definition.** Opcode `1100111`, I-type format, reusing the exact I-type immediate path built for `lw`. Redirects the PC to `(rs1 + ImmExt)` with bit 0 forced to `0`. Writes `PCPlus4` into `rd` — same writeback behavior as `jal`, different target computation.

Two separate things happen in the same cycle: a new PC gets computed from `rs1 + ImmExt`, and the old `PCPlus4` gets written into `rd`. These are independent operations using two different pieces of hardware.

**Why `jalr` reuses the ALU instead of the `PCTarget` adder.** `PCTarget` takes exactly two inputs, wired in directly: `PC` and `ImmExt`. It has no way to take `rs1` as an input — there's no mux on it. `jalr` needs `rs1 + ImmExt`, and `rs1`'s value only reaches the datapath as `RD1`, the register file's output — the same signal already wired into the ALU's `SrcA`. Rather than build a second adder, `jalr` is routed through the ALU, which already has `RD1` available on one input:

`SrcA = RD1` (`ALUSrcA=0`, the same setting every instruction except `auipc` uses) `SrcB = ImmExt` (`ALUSrc=1`, the same I-type immediate path `lw` and `addi` already use) `ALUControl = 0000` (add)

Result: `ALUResult = rs1 + ImmExt`. No new adder is needed, because the ALU doing ordinary addition already computes this — it only needs its existing inputs set the same way `addi` sets them.

**Why bit 0 gets cleared.** RISC-V instructions are always aligned to an even address — a valid instruction address always has bit 0 equal to `0`. `rs1 + ImmExt` is ordinary binary addition, and addition gives no guarantee that bit 0 comes out `0`. The rule "force bit 0 to `0` before using this as the next PC" is imposed by the ISA on top of the addition — it is not a property the addition happens to have. In hardware this is one AND gate: `ALUResult[0]` ANDed with `0`; every other bit, `[31:1]`, passes through unchanged.

**Why `PCSrc` must widen.** Before `jalr`, `PCNext` selects between exactly two sources — `PCPlus4` and `PCTarget` — one bit is enough. `jalr` introduces a third source: `ALUResult` with bit 0 cleared. One bit cannot select among three sources. `PCSrc` widens to 2 bits.

|PCSrc|Source|Selected when|
|---|---|---|
|`00`|`PCPlus4`|default|
|`01`|`PCTarget`|branch taken, or `jal`|
|`10`|`ALUResult` with bit 0 cleared|`jalr`|

The one new piece of logic this instruction adds is exactly that AND gate on `ALUResult[0]`, active on the path selected by `PCSrc=10`. Nothing else is new.

**Main Decoder row:** `RegWrite=1`, `ImmSrc=000` (I-type), `ALUSrc=1`, `ALUSrcA=0`, `MemWrite=0`, `ResultSrc=11` (`PCPlus4`), `PCSrc` forced to `10`, `ALUOp=00` (add).

Example, continuing directly from the `jal` example above: `PC = 0x2000`, `x1 = 0x1004` (the return address `jal` saved). `jalr x0, 0(x1)`: `ALUResult = 0x1004 + 0 = 0x1004`, bit 0 is already `0` → next PC is `0x1004`. `rd = x0` means the return-address write (`PCPlus4 = 0x2004`) is discarded, since writes to `x0` are always discarded. This is the `jalr x0, 0(x1)` return idiom, worked through with concrete values — but the immediate here is `0`, so the AND gate has nothing to do in this example.

**A second example where bit-0 clearing actually changes the result:** `x1 = 0x1005`, immediate `= 2`. `jalr x2, 2(x1)`: `ALUResult = 0x1005 + 2 = 0x1007`. In binary, `0x1007` ends `...0111` — bit 0 is `1`. The AND gate forces it to `0`: `0x1007 → 0x1006`. Next PC is `0x1006`, not `0x1007`. `x2 = PCPlus4`, unaffected by any of this. The addition itself has no notion of alignment; the AND gate is the only thing enforcing it, and it touches bit 0 only — bits `[31:1]` pass through unchanged even here.

---

## 8. Consolidated Main Decoder

|Instruction(s)|op|RegWrite|ImmSrc|ALUSrc|ALUSrcA|MemWrite|ResultSrc|Branch|PCSrc (forced)|ALUOp|
|---|---|---|---|---|---|---|---|---|---|---|
|`lw`|`0000011`|1|`000`|1|0|0|`01`|0|—|`00`|
|`sw`|`0100011`|0|`001`|1|0|1|`00`|0|—|`00`|
|R-type (10)|`0110011`|1|`000`|0|0|0|`00`|0|—|`10`|
|I-type ALU (9)|`0010011`|1|`000`|1|0|0|`00`|0|—|`10`|
|branches (6)|`1100011`|0|`010`|0|0|0|`00`|1|runtime|`01`|
|`jal`|`1101111`|1|`100`|0|0|0|`11`|0|`01`|`00`|
|`jalr`|`1100111`|1|`000`|1|0|0|`11`|0|`10`|`00`|
|`lui`|`0110111`|1|`011`|0|0|0|`10`|0|—|`00`|
|`auipc`|`0010111`|1|`011`|1|1|0|`00`|0|—|`00`|

Every entry here is a defined value: outputs that are functionally don't-care are driven to `0` rather than `x`, because an `x` that crosses a pipeline register can reach a hazard decision (pipelined spec §18, Note 9).

ALU Decoder tables: `ALUOp=10` in Section 2, `ALUOp=01` in Section 3.

---

## 9. Checklist against existing RTL

- `alu.sv`: `ALUControl` port `[2:0]` → `[3:0]`. Existing five cases get a leading `0`, unchanged behavior. Five new cases added.
- `imm_gen.sv`: `ImmSrc` port `[1:0]` → `[2:0]`. I/S/B keep their existing bit patterns with a leading `0`. Two new cases (U, J) added.
- `main_decoder.sv`: five new opcode rows. Two new output ports (`ALUSrcA`; `ResultSrc` and `PCSrc` widen from 1 bit to 2 bits each).
- `alu_decoder.sv`: `ALUOp=10` branch gains the `funct3=101` tie-break, which is unconditional on `Instr[30]` — distinct from the `funct3=000` tie-break, which is gated by `op[5]`. `ALUOp=01` branch changes from `funct3`-independent to `funct3`-dependent.
- `control_unit.sv`: internal `PCSrc` logic changes from a single AND gate to a small structure reading `funct3`, `Zero`, `ALUResult[0]`, plus the two opcode-forced outputs for `jal` and `jalr`.
- Top-level: new `ALUSrcA` mux on the ALU's `SrcA` input. `Result` mux widens 2:1 → 4:1. `PCNext` mux widens 2:1 → 3:1, with the new bit-0-cleared path.

---

**The core fact:** across every instruction in this document, exactly two pieces of hardware are genuinely new — the `ALUSrcA` mux (giving the ALU's first operand a second possible source, `PC`, used only by `auipc`) and the bit-0-clear AND gate on `jalr`'s target. Every other change is an existing signal (`ALUControl`, `ImmSrc`, `ResultSrc`, `PCSrc`) being given more bits because it now has to distinguish more cases than it used to — not new circuitry, just wider selection.