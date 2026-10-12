# RV32I Single-Cycle Core — Spec Sheet (Steps 1–4)

**Scope of this document:** register file, immediate generator, ALU, Main Decoder, ALU Decoder (wrapped together as a Control Unit, matching Figure 7.12's single Control Unit block), PC register, instruction memory, data memory, and top-level integration. Covers exactly four instruction classes — `lw`, `sw`, R-type (`add`, `sub`, `and`, `or`, `slt`), `beq` — end to end, from fetch through writeback. This is a complete, testable single-cycle core for these four classes. `jal`, `jalr`, `lui`, `auipc`, and the remaining ALU operations are not yet covered — those extend this same datapath in a later revision, once worked through in the teaching-doc narrative.

---

## 1. System Overview

```
                    ┌──────────────┐
   op[6:0] ────────►│              │
funct3[2:0] ────────►│ Control Unit │───► RegWrite, ImmSrc[1:0], ALUSrc,
  funct7[5] ────────►│              │     MemWrite, ResultSrc,
       Zero ────────►│              │     ALUControl[2:0], PCSrc
                    └──────────────┘
   Internally: Main Decoder + ALU Decoder + one AND gate (§5, §6, §11).
   ALUOp and Branch are wires strictly internal to this block — neither
   is a port on it, matching Figure 7.12's single "Control Unit" box.

        A1,A2,A3,WD3,WE3 ──► Register File ──► RD1, RD2
        instr[31:7], ImmSrc ──► Immediate Generator ──► ImmExt[31:0]
        SrcA, SrcB, ALUControl ──► ALU ──► ALUResult, Zero

        PCNext ──► PC Register ──► PC ──► Instruction Memory ──► Instr
        ALUResult(addr), RD2(WD), MemWrite ──► Data Memory ──► ReadData

        PC + 4 = PCPlus4
        PC + ImmExt = PCTarget
        PCSrc ? PCTarget : PCPlus4 = PCNext   (feeds back into PC Register)
        ALUSrc ? ImmExt : RD2 = SrcB
        ResultSrc ? ReadData : ALUResult = Result   (feeds back into WD3)

        Seven blocks are instantiated as top-level siblings (§11): Register
        File, Immediate Generator, ALU, Control Unit, PC Register, Instruction
        Memory, Data Memory — matching Figure 7.12's block layout and signal
        names exactly. This is a complete single-cycle core for the four
        instruction classes in scope — see the instruction table below.
```

**Instruction scope for this document:**

|Instruction|Format|op|funct3|funct7[5]|
|---|---|---|---|---|
|`lw`|I|`0000011`|`010`|—|
|`sw`|S|`0100011`|`010`|—|
|`add`|R|`0110011`|`000`|`0`|
|`sub`|R|`0110011`|`000`|`1`|
|`and`|R|`0110011`|`111`|`0`|
|`or`|R|`0110011`|`110`|`0`|
|`slt`|R|`0110011`|`010`|`0`|
|`beq`|B|`1100011`|`000`|—|

---

## 2. Block: Register File (`regfile`)

**Purpose:** 32 general-purpose 32-bit registers, `x0` architecturally hardwired to zero, two combinational read ports and one clocked write port — matching the register file shown feeding the ALU in every datapath figure covered so far.

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`clk`|in|1|system clock|
|`rst_n`|in|1|async active-low reset|
|`A1`|in|5|read address 1 (`rs1`, `Instr[19:15]`)|
|`A2`|in|5|read address 2 (`rs2`, `Instr[24:20]`)|
|`A3`|in|5|write address (`rd`, `Instr[11:7]`)|
|`WD3`|in|32|write data (`Result`)|
|`WE3`|in|1|write enable (`RegWrite`)|
|`RD1`|out|32|read data 1|
|`RD2`|out|32|read data 2|

**Internal signals:**

|Signal|Type|Purpose|
|---|---|---|
|`regs`|`[31:0]` array of 32-bit, `always_ff`|register storage; index 0 need not be physically stored|

**Functional behavior:**

- `RD1` and `RD2` are purely combinational reads: `RD1 = (A1 == 5'd0) ? 32'b0 : regs[A1]`, and identically for `RD2`/`A2`. The zero-force on index 0 is enforced **at the read mux**, not merely by refusing to write it — this is the detail that actually guarantees `x0` reads as zero under every circumstance, including before reset has run or if a write to `A3==0` is ever attempted.
- Writes are synchronous: on `posedge clk`, `if (WE3 && A3 != 5'd0) regs[A3] <= WD3`. The `A3 != 5'd0` guard prevents storage from being disturbed by a write targeting `x0` — redundant with the read-side zero-force, but keeping both means the design is correct even if one guard were ever removed by mistake.
- **Same-cycle read/write ordering:** within a single clock cycle, `RD1`/`RD2` reflect the register contents _before_ the current cycle's write commits. The write via `WD3`/`WE3` only takes effect at the next `posedge clk`. This is what makes the single-cycle datapath correct without extra hazard logic — a register being written this cycle is never simultaneously required as a read source by the same instruction, because a single instruction reads its source registers and writes its destination register in the same cycle, but the destination write doesn't visibly change `RD1`/`RD2` until the _next_ instruction's cycle begins.
- Reset (`!rst_n`) clears all 32 storage locations to `0`. This isn't architecturally required by the ISA — a real register file's contents are undefined until written — but it removes `x` propagation in simulation and makes waveform debugging tractable.

**What "done" looks like for this block:** simulate standalone — write a known value to a register `1–31`, read it back on the next cycle, confirm the value matches. Attempt a write to `x0` with `WE3=1`, `A3=0`; confirm `RD1`/`RD2` still return `0` when addressed at `A1=0`/`A2=0` on the same and following cycles. Confirm a write and a read of the _same_ register on the same cycle returns the pre-write value on `RD1`/`RD2`, and the new value only appears starting the following cycle.

---

## 3. Block: Immediate Generator (`immediate_generator`)

**Note:** implemented as module `immediate_generator` (not `imm_gen` — that name is used only informally in this document's prose and diagrams).

**Purpose:** reassemble and sign-extend the instruction's immediate field, in whichever of the three formats covered so far is selected by `ImmSrc`.

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`instr`|in|25 (`[31:7]`)|upper 25 bits of the instruction; bits `[6:0]` (opcode) never contribute to any immediate field and are not needed here|
|`ImmSrc`|in|2|selects immediate format|
|`ImmExt`|out|32|sign-extended immediate|

**Parameters:** none. **Internal signals:** none — pure combinational, no state.

**ImmSrc encoding (as specified):**

|ImmSrc|Type|Bit reassembly|Used by|
|---|---|---|---|
|`00`|I|`{{20{instr[31]}}, instr[31:20]}`|`lw`|
|`01`|S|`{{20{instr[31]}}, instr[31:25], instr[11:7]}`|`sw`|
|`10`|B|`{{20{instr[31]}}, instr[7], instr[30:25], instr[11:8], 1'b0}`|`beq`|

**Functional behavior:**

- Purely combinational (`always_comb`), stateless — the same instruction word always produces the same `ImmExt` regardless of what happened on any previous cycle.
- **I-type:** the 12-bit field `instr[31:20]` is contiguous — no reassembly needed, only sign extension. Bit 31 (the field's own sign bit) is replicated into bits `[31:12]`.
- **S-type:** the 12-bit immediate is split across two non-adjacent instruction ranges — `instr[31:25]` supplies the upper 7 bits, `instr[11:7]` supplies the lower 5 — because the S-type encoding puts `rs2` (`instr[24:20]`) in the middle of the word, where the I-type immediate's middle bits would otherwise sit. Bit 31 is still the sign bit and is replicated the same way.
- **B-type:** the 13-bit branch offset is the most scrambled of the three — `instr[7]`, `instr[30:25]`, `instr[11:8]`, and a hardwired `1'b0` in bit 0. The hardwired zero exists because branch targets are always instruction-aligned (even byte addresses); encoding bit 0 explicitly would waste an encoding bit to always store `0`. Bit 31 remains the sign bit for a 13-bit signed value, replicated into bits `[31:12]` — note this means bit 31 is copied 20 times regardless of format, which is a fixed, format-independent replication.
- **Optimization available but not required for correctness:** bits `ImmExt[31:12]` are always `{20{instr[31]}}` no matter which of the three formats is selected. A hardware implementation can factor this replication out as a single fixed connection, and use a narrower 3:1 mux only for the lower 12 bits' formatting. The specification above describes the full 32-bit result per format for clarity; this optimization changes the gate-level structure, not the truth table.

**What "done" looks like for this block:** one directed test per format — feed a known instruction word for `lw`, `sw`, and `beq`, hand-compute the expected `ImmExt`, and confirm the module's output matches exactly, including the sign bit for both positive and negative immediates in each format.

---

## 4. Block: ALU (`alu`)

**Purpose:** performs the operation selected by `ALUControl` on two 32-bit operands, and reports whether the result is zero — the single piece of hardware reused for every arithmetic operation, every address computation, and every branch comparison covered so far.

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`SrcA`|in|32|first operand|
|`SrcB`|in|32|second operand|
|`ALUControl`|in|3|operation select|
|`ALUResult`|out|32|operation result|
|`Zero`|out|1|`1` iff `ALUResult == 0`|

**Parameters:** none. **Internal signals:** none — pure combinational.

**ALUControl encoding (as specified, five operations covered):**

|ALUControl|Operation|Result|Used by|
|---|---|---|---|
|`000`|add|`SrcA + SrcB`|`lw`, `sw` (address), `add`|
|`001`|subtract|`SrcA - SrcB`|`beq` (comparison), `sub`|
|`010`|and|`SrcA & SrcB`|`and`|
|`011`|or|`SrcA \| SrcB`|`or`|
|`101`|set less than|`($signed(SrcA) < $signed(SrcB)) ? 32'd1 : 32'd0`|`slt`|

`ALUControl` values `100`, `110`, `111` are unused by the instruction set covered so far (reserved for `sltu`, `sll`/`srl`, `sra` once those are added).

**Functional behavior:**

- Purely combinational (`always_comb`), single `case` statement on `ALUControl`.
- `Zero = (ALUResult == 32'b0)` is computed **unconditionally**, on every cycle, regardless of what `ALUControl` currently is. The datapath only _uses_ `Zero` when the current instruction is a branch, but the ALU itself has no way to know that — gating the computation would require feeding branch-specific control information into a block that's supposed to stay a pure function of its two data inputs and the operation select. It costs nothing extra to compute a 32-bit zero-comparison every cycle, so it's simplest to always do it and let the downstream `PCSrc` AND gate decide whether the value is meaningful.
- **`slt` must use a signed comparison, not an unsigned one.** If `SrcA`/`SrcB` are declared as plain unsigned `logic [31:0]` and compared with a bare `<`, SystemVerilog performs an _unsigned_ comparison — which gives the wrong answer whenever either operand is negative. Concrete failure case: `SrcA = 32'hFFFFFFFF` (−1 as two's complement), `SrcB = 32'h00000001` (+1). Signed comparison: `−1 < 1` → true → result should be `1`. Unsigned comparison: `0xFFFFFFFF < 0x00000001` → false, since `0xFFFFFFFF` is the largest possible unsigned value → result would incorrectly come out `0`. The fix is an explicit `$signed()` cast on both operands for this one operation only — `sub`, `add`, `and`, `or` are unaffected by signedness since they aren't magnitude comparisons.

**What "done" looks like for this block:** directed test per operation — `add` and `sub` with both positive-only and mixed-sign operands (confirming two's complement wraparound behaves as plain modulo-2³² addition), `and`/`or` with a pattern that exercises every bit position, and `slt` specifically re-tested with the `0xFFFFFFFF` vs `0x00000001` case above to confirm the signed comparison is actually wired correctly and not silently doing unsigned comparison.

---

## 5. Block: Main Decoder (`main_decoder`)

**Purpose:** produce every control signal that depends on `op` alone, plus the 2-bit `ALUOp` signal handed to the ALU Decoder for the one class of decode (R-type) that needs finer-grained information.

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`op`|in|7|`Instr[6:0]`|
|`RegWrite`|out|1|write enable, register file|
|`ImmSrc`|out|2|immediate format select, feeds `immediate_generator`|
|`ALUSrc`|out|1|ALU `SrcB` select: register (`0`) or immediate (`1`)|
|`MemWrite`|out|1|write enable, data memory (not yet instantiated — output exists now for forward compatibility)|
|`ResultSrc`|out|1|writeback source: ALU result (`0`) or memory data (`1`)|
|`Branch`|out|1|is the current instruction a branch|
|`ALUOp`|out|2|passed to `alu_decoder`|

**Parameters:** none. **Internal signals:** none — pure combinational.

**Main Decoder truth table (as specified):**

|Instruction|op|RegWrite|ImmSrc|ALUSrc|MemWrite|ResultSrc|Branch|ALUOp|
|---|---|---|---|---|---|---|---|---|
|`lw`|`0000011`|`1`|`00`|`1`|`0`|`1`|`0`|`00`|
|`sw`|`0100011`|`0`|`01`|`1`|`1`|`x`|`0`|`00`|
|R-type|`0110011`|`1`|`xx`|`0`|`0`|`0`|`0`|`10`|
|`beq`|`1100011`|`0`|`10`|`0`|`0`|`x`|`1`|`01`|

**Per-row justification:**

- **`lw`**: writes a register; needs the I-type immediate as a memory offset; that offset must reach the ALU (`ALUSrc=1`); doesn't write memory; the value written back comes from memory, not the ALU (`ResultSrc=1`); not a branch; address computation is unconditionally addition (`ALUOp=00`).
- **`sw`**: writes no register at all — `ResultSrc` is a genuine don't-care here, not merely unused, because `RegWrite=0` means the register file's write port never activates regardless of what value the Result mux would have produced; needs the S-type immediate; that immediate reaches the ALU; does write memory; address computation is addition, same `ALUOp=00` as `lw`.
- **R-type**: writes a register; `ImmSrc` is don't-care (`xx`) because R-type never reads `ImmExt` at all — both ALU operands come from the register file; `ALUSrc=0` selects `RD2` instead of the immediate; doesn't write memory; not a branch; `ALUOp=10` defers the exact operation to the ALU Decoder, since this is the one instruction class where the operation genuinely varies by `funct3`.
- **`beq`**: writes no register — `ResultSrc` don't-care for the same reason as `sw`; needs the B-type immediate for the branch offset; ALU operands are two registers, not an immediate (`ALUSrc=0`); doesn't write memory; `Branch=1` flags this instruction downstream; `ALUOp=01` — a branch comparison is unconditionally a subtraction, independent of `funct3`.

**Control-flow note:** every output is defined for every recognized `op` value above. Any `op` value **not** in this table (all future/unsupported opcodes, for now) must still produce defined outputs — every signal defaulted to `0` at the top of the `always_comb` block, before the `case` statement, exactly as required to prevent inferred latches in any wide combinational decoder. This matters more here than it might first appear: only 4 of 128 possible `op` values are handled by this table so far, so the default-assignment discipline is carrying nearly the entire address space right now, not just an edge case.

**What "done" looks like for this block:** one directed test per instruction in the table — drive each `op` value, confirm every output signal matches its row exactly. Additionally, drive at least one `op` value **not** in the table (e.g. `7'b1111111`) and confirm every output defaults to a defined `0` rather than holding a stale or unknown value.

---

## 6. Block: ALU Decoder (`alu_decoder`)

**Purpose:** produce the final `ALUControl` signal, consuming `ALUOp` from the Main Decoder together with `funct3` and `{op[5], funct7[5]}` — the only two instruction-word bits beyond `op` that any control decision in this document needs.

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`ALUOp`|in|2|from `main_decoder`|
|`funct3`|in|3|`Instr[14:12]`|
|`op5`|in|1|`Instr[5]`|
|`funct7_5`|in|1|`Instr[30]`|
|`ALUControl`|out|3|final ALU operation select|

**Parameters:** none. **Internal signals:** none — pure combinational.

**ALU Decoder truth table (as specified):**

|ALUOp|funct3|{op5,funct7_5}|ALUControl|Instruction|
|---|---|---|---|---|
|`00`|`x`|`x`|`000` (add)|`lw`, `sw`|
|`01`|`x`|`x`|`001` (subtract)|`beq`|
|`10`|`000`|`00`, `01`, `10`|`000` (add)|`add`|
|`10`|`000`|`11`|`001` (subtract)|`sub`|
|`10`|`010`|`x`|`101` (set less than)|`slt`|
|`10`|`110`|`x`|`011` (or)|`or`|
|`10`|`111`|`x`|`010` (and)|`and`|

**Functional behavior:**

- `ALUOp=00` and `ALUOp=01` ignore `funct3` entirely (`x` in the table) — the Main Decoder already fully determined the operation for these cases; there's nothing left for this block to resolve.
    
- `ALUOp=10` reads `funct3` to disambiguate R-type. Five of the seven `funct3` values map to exactly one instruction each (`010→slt`, `110→or`, `111→and`); only `funct3=000` is shared between two instructions (`add`/`sub`), which is why `{op5,funct7_5}` only appears on that one row.
    
- **Why `{op5, funct7_5}` must be read as a 2-bit concatenation and not `funct7_5` in isolation:** `funct3=000` is also the value for `addi`, an I-type instruction with no genuine `funct7` field — its top instruction bits are part of a 12-bit immediate, so whatever bit pattern happens to sit at `Instr[30]` for a given `addi` is arbitrary immediate data, not a subtract flag. `op5` (`1` for R-type `op=0110011`, `0` for I-type-ALU `op=0010011`) distinguishes which situation is actually occurring:
    
    - `{op5=0, funct7_5=0}` = `00` → `addi`, bit is meaningless immediate data → add
    - `{op5=0, funct7_5=1}` = `01` → `addi` again, different immediate bit, still meaningless → add
    - `{op5=1, funct7_5=0}` = `10` → genuine R-type, bit really is `funct7[5]`, value `0` → add
    - `{op5=1, funct7_5=1}` = `11` → genuine R-type, `funct7[5]=1` → subtract
    
    Only the last case, where both "this is truly R-type" and "the bit reads 1" hold simultaneously, produces `subtract`. This is what the table's `00, 01, 10 → add` / `11 → subtract` grouping encodes.
    

**What "done" looks like for this block:** directed test per row of the table, including deliberately constructing an `addi`-shaped input (`ALUOp=10` would not even apply here since `addi` produces `ALUOp=00` from the Main Decoder — but as an internal robustness check, confirm that if `op5=0` is ever paired with `funct7_5=1` under `ALUOp=10`, the result is still `add`, not `subtract`) and confirming `sub` only ever results from the `op5=1, funct7_5=1` combination.

---

## 7. Decode Failure-Mode Notes

**Note 1 — reading `funct7[5]` alone instead of `{op5, funct7[5]}` silently misdecodes `addi` as `sub`.**

If the ALU Decoder's add/sub distinction were implemented as a bare `funct7_5 ? sub : add` — omitting the `op5` check — trace what happens for `addi x5, x6, -1` (`op=0010011`, `funct3=000`, and whatever bit pattern the assembler placed at `Instr[30]` as part of the immediate `-1`, which in two's complement has `Instr[30]=1`):

|Signal|Correct value|Bare-`funct7_5` behavior|
|---|---|---|
|`op5`|`0` (I-type)|not read|
|`funct7_5` (= `Instr[30]`, part of the `-1` immediate)|`1`|`1`|
|`ALUOp` from Main Decoder|`00` (addi always adds) — this note applies to a future extension where `addi` is folded into the same `ALUOp=10` path as R-type; under the current table `addi` isn't yet added, so this trap is latent, not yet triggered|—|
|Resulting `ALUControl` if the trap fires|`000` (add)|`001` (subtract)|

This is not yet reachable under the four instructions in this document's scope — `addi` isn't in the table yet — but it becomes reachable the moment `addi` is added in the next round of instructions, and the fix (`op5` gating) needs to already be in place before that happens, not retrofitted after a failing test.

**Note 2 — a missing default in the Main Decoder's `always_comb` block produces inferred latches for unrecognized opcodes.**

Only 4 of 128 possible 7-bit `op` values are handled by Table in §5. If the `case` statement has no `default` branch, and no defaults are assigned before the `case`, then for any of the other 124 `op` values, every output signal keeps whatever value it last held — which is exactly the defining behavior of a latch, not a combinational function of `op`. Concretely: drive `op = 0110011` (R-type, `RegWrite=1`), then drive `op = 7'b1111111` (unrecognized) — a correctly defaulted decoder outputs `RegWrite=0` (or whatever the chosen default is) on the very next evaluation; a decoder missing defaults keeps outputting `RegWrite=1`, silently carrying the previous instruction's control state into an instruction that should have produced entirely different (defined, safe) behavior. The fix, already stated in §5: assign every output to a safe default at the top of the block, before the `case`.

**Note 3 — implementing `slt` with an unsigned comparison instead of a signed one.**

Already covered in §4's ALU behavior section in full detail — repeated here because it is a decode-adjacent trap (the control signals correctly select `ALUControl=101` for `slt`; the bug lives entirely inside how the ALU itself interprets that select value) and is easy to miss since the control-signal tables give no indication that signedness matters — nothing in Tables in §5 or §6 encodes "and by the way, this operation needs a signed comparison." That information exists only in the ALU's own specification.

---

## 8. Block: PC Register (`pc`)

**Note:** implemented as module `pc` (not `pc_reg`), with output port named `PCOut` (not `PC` — see ports table below).

**Purpose:** holds the address of the instruction currently being fetched. Purely a storage element — it makes no decisions about what value it holds next; that decision is entirely external (§11).

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`clk`|in|1|system clock|
|`rst_n`|in|1|async active-low reset|
|`PCNext`|in|32|the value to capture on the next clock edge|
|`PCOut`|out|32|current instruction address|

**Internal signals:** none beyond `PCOut` itself, which is both the module's output and its only piece of state.

**Functional behavior:**

- Single `always_ff @(posedge clk or negedge rst_n)` block: `if (!rst_n) PCOut <= 32'b0; else PCOut <= PCNext;`
- The reset value `0` is a convention, not an ISA requirement — it only needs to match whatever address the instruction memory image is loaded to start at. A real chip's reset vector may differ; `0` is chosen here because §9's instruction memory is also indexed starting from word `0`.
- This module never computes `PCPlus4`, `PCTarget`, or `PCSrc` itself. All three live in the top-level integration (§11) as combinational logic feeding `PCNext`. `pc_reg` only ever does one thing: capture whatever is on `PCNext` at the clock edge.

**What "done" looks like for this block:** simulate standalone — drive `PCNext` to a sequence of known values, confirm `PC` updates to each one exactly one cycle later. Confirm `rst_n` asserted low forces `PC` to `0` regardless of what `PCNext` currently holds.

---

## 9. Block: Instruction Memory (`imem`)

**Purpose:** combinational instruction fetch — given the current `PC`, return the 32-bit instruction word stored at that address.

**Parameters:**

|Parameter|Default|Purpose|
|---|---|---|
|`DEPTH`|`256`|number of 32-bit instruction words this memory holds. Not an ISA value — it's sized to whatever test program is currently loaded, unlike `regfile`'s `32`, which is fixed by the instruction encoding (`rs1`/`rs2`/`rd` are 5-bit fields, `2^5=32`).|

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`A`|in|32|fetch address (= `PC`)|
|`RD`|out|32|instruction word (= `Instr`)|

**Internal signals:**

|Signal|Type|Purpose|
|---|---|---|
|`mem`|`[31:0]` array of 32-bit, `[0:DEPTH-1]`, initialized via `$readmemh` in an `initial` block|program storage|

**Functional behavior:**

- Combinational read only — no clock, no state beyond the initialized array contents: `RD = mem[A[$clog2(DEPTH)+1 : 2]]`.
- **Why bits `[1:0]` are always dropped:** instructions are stored 4 bytes at a time, so every valid instruction address is a multiple of `4` (`0`, `4`, `8`, `12`, ...), and in binary any multiple of `4` always ends in `00`. Those two bits never carry useful information for indexing, so they're always excluded from the slice, regardless of how large or small the memory is.
- **Why the slice's upper end depends on `DEPTH`, not on the full 32-bit address:** `mem` only has `DEPTH` slots, so the index into it only needs enough bits to count from `0` to `DEPTH-1`. That bit count is `$clog2(DEPTH)`. For the default `DEPTH=256`, `$clog2(256)=8`, so the slice needs 8 bits — starting at bit `2` (right after the two dropped bits) and running up to bit `9` (`2 + 8 - 1 = 9`), giving `A[9:2]`. Using the full `A[31:2]` against a 256-entry array would mean indexing with a 30-bit number into a range that only has 8 bits' worth of valid slots — almost every real address would land outside the array. The general, parameterized form `A[$clog2(DEPTH)+1 : 2]` is what stays correct as `DEPTH` changes; a literal `A[31:2]` or a literal `A[9:2]` is only correct for one specific `DEPTH` value.
- Bits of `A` above the slice actually used (`A[31:10]` for `DEPTH=256`) are simply never read by this module — expected and harmless for a small test memory, not a bug.
- Loaded once, via `$readmemh("program.hex", mem)` inside an `initial` block — without this, `mem` starts completely uninitialized (`x` in simulation) regardless of whether the indexing is correct.

**What "done" looks like for this block:** load a small known program, drive `A` with the byte addresses of the first several instructions (`0x0`, `0x4`, `0x8`, ...), confirm `RD` returns the correct 32-bit instruction word at each address, matching the assembled machine code exactly.

---

## 10. Block: Data Memory (`dmem`)

**Purpose:** word-addressed load/store storage for `lw`/`sw`. Combinational read, synchronous write — matching the register file's split, but for memory instead of registers.

**Parameters:**

|Parameter|Default|Purpose|
|---|---|---|
|`DEPTH`|`256`|number of 32-bit data words this memory holds. Same reasoning as `imem`'s `DEPTH` — sized to whatever test program's data footprint is currently in use, not an ISA-fixed value.|

**Ports (as specified):**

|Signal|Dir|Width|Purpose|
|---|---|---|---|
|`clk`|in|1|system clock|
|`A`|in|32|memory address (= `ALUResult`)|
|`WD`|in|32|write data (= `RD2`)|
|`WE`|in|1|write enable (= `MemWrite`)|
|`RD`|out|32|read data (= `ReadData`)|

**Internal signals:**

|Signal|Type|Purpose|
|---|---|---|
|`mem`|`[31:0]` array of 32-bit, `[0:DEPTH-1]`, `always_ff`|data storage|

**Functional behavior:**

- Read is combinational and unconditional: `RD = mem[A[$clog2(DEPTH)+1 : 2]]`, computed every cycle regardless of `WE`. Identical indexing formula and reasoning as `imem` — bits `[1:0]` dropped because they're always `00` for a word-aligned address, and the slice's upper bound set by `$clog2(DEPTH)` rather than the full address width, for the same reason `imem`'s does.
- Write is synchronous: `if (WE) mem[A[$clog2(DEPTH)+1 : 2]] <= WD` on `posedge clk` — same index expression as the read, since both must always agree on which slot a given address maps to.
- **Scope limitation, intentional:** this specification is word-only. `lb`/`lh`/`sb`/`sh` need byte-enables and sub-word alignment logic that aren't part of this document's four instruction classes — `lw`/`sw` are the only load/store instructions covered so far, and both always operate on full, 4-byte-aligned words. This will need revisiting once byte/half-word loads and stores are added.
- Matching the reasoning already established for `sw` in §5: `RD` is computed every cycle whether or not the current instruction actually wants it. For a `sw` instruction, `RD` still comes out as whatever was previously stored at the target address, but it goes nowhere, since `ResultSrc` is a don't-care and the register file's `WE3` is `0` for `sw`.

**What "done" looks like for this block:** write a known value to a known address, confirm reading that same address on a later cycle returns it. Confirm reading a _different_ address after that write returns that address's own (separately verified) contents, not the just-written value — i.e. confirm the write actually targeted only the intended word.

---

## 11. Top-Level Integration (`rv32_top`)

**Note:** implemented as module `rv32_top` (not `rv32i_single_cycle`).

**Purpose:** wire the seven top-level blocks — Register File, Immediate Generator, ALU, Control Unit, PC Register, Instruction Memory, Data Memory — into one complete single-cycle core, matching Figure 7.12's block layout and signal names exactly.

**Control Unit wrapper (`control_unit`):** at the top level, `main_decoder` and `alu_decoder` (§5, §6) are not instantiated as separate siblings — they're wrapped inside one `control_unit` module, matching the single "Control Unit" box in Figure 7.12. The top level connects only to this wrapper's ports:

|Signal|Dir|Width|Source / destination|
|---|---|---|---|
|`op`|in|7|`Instr[6:0]`|
|`funct3`|in|3|`Instr[14:12]`|
|`funct7_5`|in|1|`Instr[30]`|
|`Zero`|in|1|`alu.Zero`|
|`RegWrite`|out|1|→ `regfile.WE3`|
|`ImmSrc`|out|2|→ `immediate_generator.ImmSrc`|
|`ALUSrc`|out|1|→ `SrcB` mux select (below)|
|`MemWrite`|out|1|→ `dmem.WE`|
|`ResultSrc`|out|1|→ `Result` mux select (below)|
|`ALUControl`|out|3|→ `alu.ALUControl`|
|`PCSrc`|out|1|→ `PCNext` mux select (below)|

Internally, `control_unit` instantiates `main_decoder` and `alu_decoder` exactly as specified in §5/§6, plus one AND gate: `PCSrc = Branch & Zero`. `ALUOp` (Main Decoder → ALU Decoder) and `Branch` (Main Decoder → the AND gate) are wires strictly internal to `control_unit` — neither is a port on the wrapper, and neither is connected to anything at the top level. `op5`, needed internally by `alu_decoder`, is derived inside `control_unit` as `op[5]`, taken from the `op` input already listed above — it is not a separate top-level-sliced signal, since Figure 7.12 shows only one `op[6:0]` line entering the Control Unit box, not a separate `op5` line.

**Instruction field connections**, all sliced directly from `Instr` (`imem`'s `RD` output):

|Field|Bits|Feeds|
|---|---|---|
|`op`|`Instr[6:0]`|`control_unit.op`|
|`rs1`|`Instr[19:15]`|`regfile.A1`|
|`rs2`|`Instr[24:20]`|`regfile.A2`|
|`rd`|`Instr[11:7]`|`regfile.A3`|
|`funct3`|`Instr[14:12]`|`control_unit.funct3`|
|`funct7_5`|`Instr[30]`|`control_unit.funct7_5`|
|`Instr[31:7]`|—|`immediate_generator.instr`|

**Combinational connections (muxes and adders), all `assign` — no dedicated module for any of these:**

- `PCPlus4 = PC + 32'd4`
- `PCTarget = PC + ImmExt`
- `PCNext = PCSrc ? PCTarget : PCPlus4` → `pc.PCNext`
- `SrcA = RD1` → `alu.SrcA`
- `SrcB = ALUSrc ? ImmExt : RD2` → `alu.SrcB`
- `Result = ResultSrc ? ReadData : ALUResult` → `regfile.WD3`

**Direct port-to-port connections, no logic:**

- `pc.PCOut` → `imem.A`
- `imem.RD` → `Instr` (source of every field slice above)
- `alu.ALUResult` → `dmem.A`
- `alu.Zero` → `control_unit.Zero`
- `regfile.RD2` → `dmem.WD`
- `control_unit.MemWrite` → `dmem.WE`
- `dmem.RD` → `ReadData` (input to the `Result` mux above)
- `control_unit.RegWrite` → `regfile.WE3`
- `control_unit.ImmSrc` → `immediate_generator.ImmSrc`
- `control_unit.ALUControl` → `alu.ALUControl`
- `control_unit.PCSrc` → `PCNext` mux select (above)

**What "done" looks like for the integrated core:** every module above already has its own standalone "done" criteria — this level of testing is about the _interactions_ between them, not re-verifying any single block. Assemble a short program mixing all four instruction classes: several `add`/`sub`/`and`/`or`/`slt` instructions establishing known register values, an `sw` storing one of those values to memory, a `lw` reading it back into a different register, and a `beq` whose outcome (taken or not taken) is controlled by values already set up earlier in the program. Step cycle by cycle and confirm `PC`, `Instr`, `RD1`/`RD2`, `ImmExt`, `ALUResult`, `Zero`, `ReadData`, and the final register file contents all match hand-computed expectations at every cycle — not just at the end of the program.

---

## 12. Control Signal Reference

|Signal|Width|Produced by|Meaning|
|---|---|---|---|
|`RegWrite`|1|Control Unit (Main Decoder, §5)|write enable, register file|
|`ImmSrc`|2|Control Unit (Main Decoder, §5)|immediate format select (`00`=I, `01`=S, `10`=B)|
|`ALUSrc`|1|Control Unit (Main Decoder, §5)|ALU `SrcB`: register (`0`) or immediate (`1`)|
|`MemWrite`|1|Control Unit (Main Decoder, §5)|write enable, data memory (`dmem.WE`)|
|`ResultSrc`|1|Control Unit (Main Decoder, §5)|writeback source: ALU (`0`) or memory (`1`) — selects `Result` (§11)|
|`Branch`|1|Main Decoder (§5) — **internal to Control Unit only, not a top-level port**|flags a branch instruction to the internal AND gate that produces `PCSrc`|
|`ALUOp`|2|Main Decoder (§5) — **internal to Control Unit only, not a top-level port**|how much decode work the ALU Decoder still needs to do|
|`ALUControl`|3|Control Unit (ALU Decoder, §6)|final ALU operation select|
|`Zero`|1|ALU|`1` iff `ALUResult==0`; feeds back into Control Unit as an input|
|`PCSrc`|1|Control Unit (internal AND of `Branch` and `Zero`, §11)|next-PC mux select: `PCPlus4` (`0`) or `PCTarget` (`1`)|

---

## 13. Signals Checklist (quick reference while coding)

|Block|Inputs|Outputs|Internal state|
|---|---|---|---|
|`regfile`|`clk`, `rst_n`, `A1[4:0]`, `A2[4:0]`, `A3[4:0]`, `WD3[31:0]`, `WE3`|`RD1[31:0]`, `RD2[31:0]`|`regs` (32×32-bit array)|
|`immediate_generator`|`instr[31:7]`, `ImmSrc[1:0]`|`ImmExt[31:0]`|none (combinational)|
|`alu`|`SrcA[31:0]`, `SrcB[31:0]`, `ALUControl[2:0]`|`ALUResult[31:0]`, `Zero`|none (combinational)|
|`main_decoder`|`op[6:0]`|`RegWrite`, `ImmSrc[1:0]`, `ALUSrc`, `MemWrite`, `ResultSrc`, `Branch`, `ALUOp[1:0]`|none (combinational) — instantiated inside `control_unit`, not a top-level sibling|
|`alu_decoder`|`ALUOp[1:0]`, `funct3[2:0]`, `op5`, `funct7_5`|`ALUControl[2:0]`|none (combinational) — instantiated inside `control_unit`, not a top-level sibling|
|`control_unit`|`op[6:0]`, `funct3[2:0]`, `funct7_5`, `Zero`|`RegWrite`, `ImmSrc[1:0]`, `ALUSrc`, `MemWrite`, `ResultSrc`, `ALUControl[2:0]`, `PCSrc`|none directly (combinational) — wraps `main_decoder` + `alu_decoder` + one AND gate (`PCSrc = Branch & Zero`); matches Figure 7.12's single Control Unit block|
|`pc`|`clk`, `rst_n`, `PCNext[31:0]`|`PCOut[31:0]`|`PCOut` itself|
|`imem`|`A[31:0]`|`RD[31:0]`|`mem` (`[0:DEPTH-1]` program storage, `DEPTH` parameter, default 256, initialized via `$readmemh`)|
|`dmem`|`clk`, `A[31:0]`, `WD[31:0]`, `WE`|`RD[31:0]`|`mem` (`[0:DEPTH-1]` data storage, `DEPTH` parameter, default 256)|
|`rv32_top` (top)|`clk`, `rst_n`|none (self-contained; add I/O ports as needed for testing)|instantiates the seven top-level siblings — `regfile`, `immediate_generator`, `alu`, `control_unit`, `pc`, `imem`, `dmem` — matching Figure 7.12, plus the combinational connections in §11|