// dcache: direct-mapped data cache, write-back + write-allocate, with the restricted-store path (T2.4).
//
// Geometry: CACHE_BYTES (default 2048) with LINE_BYTES-byte lines (16/32/64): NUM_LINES = CACHE_BYTES /
// LINE_BYTES (default 128). Address split: [offset: log2(LINE_BYTES)] [index: log2(NUM_LINES)] [tag: rest].
// Storage per line: valid, dirty, tag, one LINE_BYTES data block. valid and dirty are reset; tags and
// data are not.
//
// Core side (Memory stage). One request at a time: re (load) or we (store, byte enables `be`,
// data lane-aligned in `wdata`), never both. The pipeline is frozen while dmiss = 1, so addr, wdata,
// be, re, we, bypass are stable for the whole request; the cache uses them live (no capture).
//   load hit            dmiss = 0, rdata = the addressed word (the core extends sub-words)
//   store hit           merges the enabled bytes into the line, sets dirty, dmiss = 0 (no memory access)
//   miss (load/store)   dirty victim: write the line back (WB), then read the line (FILL); a store then
//                       finds the line and merges (store miss = fill + store hit, two array writes)
//   store with bypass   the restricted store (spec Section 4): if the line is present, write it back when
//                       dirty, invalidate it, then write the store's bytes to memory; if absent, memory
//                       only. It never writes the data array. A later load of the line misses and refills.
// dmiss stays 1 through the whole request, including the cycle the fill completes; the cycle after is a
// LOOKUP that hits.
// Stall cycles (dmiss = 1), L = memory latency (fixed): a hit costs 0. A miss with a clean or empty
// victim costs L+2 (1 lookup + L+1 fill cycles, the cycle the fill completes included); with a dirty
// victim 2L+3 (+ the write-back's L+1). A bypassed store completes in the memory's done cycle: L+1 when
// the line is clean or absent, 2L+2 when it was dirty (the write-back's L+1 first).
// DC_WRITE_LATENCY = N >= 1 models a slower array: every array write (store hit or fill) holds the
// pipeline N-1 extra cycles. 1 (default) = SRAM-like, no extra cycle.
//
// Memory side: the cache holds mem_valid (and the request fields) until mem_done. Line transfers use
// line-aligned addresses; a store that bypasses the cache is a write of one word's bytes (mem_be) at the
// word's lane inside the line image. Acceptance is implicit (the memory accepts when idle and the cache
// waits for mem_done), so there is no ready input.
//
// Observation (simulation and the wear monitor, T3):
//   aw_*        one pulse per data-array write event: aw_line = line index, aw_kind 0 = store hit
//               (including partial-word merges), 1 = line fill. Metadata writes (tag, valid, dirty) are
//               not array writes. Array reads (hits, write-back reads) are not writes.
//   tr_*        one pulse per completed request: type (tr_we), address, size (1/2/4 from the byte enables),
//               tr_bypass. A Python model replays this stream (tests/cache_model.py) and must reproduce the
//               counters below exactly.
//   cnt_*       access (completed requests), hit (first lookup hit, bypassed stores excluded), miss,
//               fill, wb (dirty write-backs, eviction or bypass), bypass (restricted stores),
//               refill_after_bypass (fills into a line whose last invalidation was a bypass), stall
//               (cycles with dmiss = 1), write (stores completed, any path).
//   peek_*      NPEEK debug reads of the word at peek_addr[k] (peek_hit[k] says the cache holds it; otherwise
//               read main memory), because with write-back the memory alone is not the truth.
// Does not model: misaligned accesses, MMIO (decoded before this module), instruction fetch coherence
// (code and data regions are disjoint, T2.5).
module dcache #(
    parameter int CACHE_BYTES = 2048,
    parameter int LINE_BYTES = 16,
    parameter int DC_WRITE_LATENCY = 1,
    parameter int NPEEK = 5          // number of independent debug peek ports
)(
    input  logic                     clk,
    input  logic                     rst_n,
    // core side
    /* verilator lint_off UNUSEDSIGNAL */  // KI-014: addr[1:0] and peek_addr[1:0] are unused (word accesses, lanes come from be)
    input  logic [31:0]              addr,
    /* verilator lint_on UNUSEDSIGNAL */
    input  logic [31:0]              wdata,
    input  logic [3:0]               be,
    input  logic                     we,
    input  logic                     re,
    input  logic                     bypass,
    output logic [31:0]              rdata,
    output logic                     dmiss,
    // memory side
    output logic                     mem_valid,
    output logic                     mem_we,
    output logic [31:0]              mem_addr,
    output logic [8*LINE_BYTES-1:0]  mem_wdata,
    output logic [LINE_BYTES-1:0]    mem_be,
    input  logic                     mem_done,
    input  logic [8*LINE_BYTES-1:0]  mem_rdata,
    // wear and trace observation
    output logic                     aw_valid,
    output logic [$clog2(CACHE_BYTES/LINE_BYTES)-1:0] aw_line,
    output logic                     aw_kind,
    output logic                     tr_valid,
    output logic                     tr_we,
    output logic [31:0]              tr_addr,
    output logic [2:0]               tr_size,
    output logic                     tr_bypass,
    // counters
    output logic [31:0]              cnt_access,
    output logic [31:0]              cnt_hit,
    output logic [31:0]              cnt_miss,
    output logic [31:0]              cnt_fill,
    output logic [31:0]              cnt_wb,
    output logic [31:0]              cnt_bypass,
    output logic [31:0]              cnt_refill_after_bypass,
    output logic [31:0]              cnt_stall,
    output logic [31:0]              cnt_write,
    // debug peek
    /* verilator lint_off UNUSEDSIGNAL */
    input  logic [32*NPEEK-1:0]      peek_addr,      // NPEEK byte addresses, port k = peek_addr[32k +: 32]
    /* verilator lint_on UNUSEDSIGNAL */
    output logic [NPEEK-1:0]         peek_hit,
    output logic [32*NPEEK-1:0]      peek_data
);
    localparam int LINE_BITS   = 8 * LINE_BYTES;
    localparam int NUM_LINES   = CACHE_BYTES / LINE_BYTES;
    localparam int OFFSET_BITS = $clog2(LINE_BYTES);
    localparam int INDEX_BITS  = $clog2(NUM_LINES);
    localparam int TAG_BITS    = 32 - INDEX_BITS - OFFSET_BITS;
    localparam int WSEL_BITS   = OFFSET_BITS - 2;

    typedef enum logic [2:0] {LOOKUP, WB, FILL, BYP_WB, BYP_WR, WAIT_ST, WAIT_FILL} state_t;
    state_t state;

    logic [NUM_LINES-1:0]  valid, dirty, byp_inv;
    logic [TAG_BITS-1:0]   tags [NUM_LINES];
    logic [LINE_BITS-1:0]  data [NUM_LINES];
    logic [31:0]           wait_cnt;
    logic                  had_miss;            // the current request's first lookup missed (or it was bypassed)

    // ---- address fields and lookup ----
    logic [INDEX_BITS-1:0] index;
    logic [TAG_BITS-1:0]   tag;
    logic [WSEL_BITS-1:0]  wsel;
    logic                  hit, victim_dirty;
    assign index = addr[OFFSET_BITS +: INDEX_BITS];
    assign tag   = addr[31 -: TAG_BITS];
    assign wsel  = addr[2 +: WSEL_BITS];
    assign hit   = valid[index] && (tags[index] == tag);
    assign victim_dirty = valid[index] && dirty[index] && !hit;

    assign rdata = data[index][32 * wsel +: 32];

    // ---- core-facing response ----
    logic req;
    assign req = re || we;
    always_comb begin
        dmiss = 1'b0;
        case (state)
            LOOKUP: begin
                if (re)                    dmiss = !hit;
                else if (we && bypass)     dmiss = 1'b1;
                else if (we)               dmiss = !hit || (DC_WRITE_LATENCY > 1);
            end
            WB, FILL, BYP_WB, WAIT_FILL:   dmiss = 1'b1;
            BYP_WR:                        dmiss = !mem_done;
            WAIT_ST:                       dmiss = (wait_cnt != 0);
            default:                       dmiss = 1'b0;
        endcase
    end

    // ---- memory-side request ----
    logic [31:0] line_base, victim_base;
    assign line_base   = {addr[31:OFFSET_BITS], {OFFSET_BITS{1'b0}}};
    assign victim_base = {tags[index], index, {OFFSET_BITS{1'b0}}};
    always_comb begin
        mem_valid = 1'b0;
        mem_we    = 1'b0;
        mem_addr  = line_base;
        mem_wdata = '0;
        mem_be    = '0;
        case (state)
            WB, BYP_WB: begin
                mem_valid = 1'b1; mem_we = 1'b1; mem_addr = victim_base;
                mem_wdata = data[index]; mem_be = {LINE_BYTES{1'b1}};
            end
            FILL: begin
                mem_valid = 1'b1;
            end
            BYP_WR: begin
                mem_valid = 1'b1; mem_we = 1'b1;
                mem_wdata[32 * wsel +: 32] = wdata;
                mem_be[4 * wsel +: 4] = be;
            end
            default: ;
        endcase
    end

    // ---- completion of the request in M (one pulse per instruction) ----
    logic completing;
    always_comb begin
        completing = req && !dmiss;
    end
    assign tr_valid  = completing;
    assign tr_we     = we;
    assign tr_addr   = addr;
    assign tr_bypass = we && bypass;
    always_comb begin
        if (!we)                       tr_size = 3'd4;       // loads: the width is not visible here, count the word
        else case (be)
            4'b1111: tr_size = 3'd4;
            4'b0011, 4'b1100: tr_size = 3'd2;
            default: tr_size = 3'd1;
        endcase
    end

    // ---- array-write events ----
    wire store_hit_write = (state == LOOKUP) && we && !bypass && hit;
    wire fill_write      = ((state == FILL) && mem_done);
    assign aw_valid = store_hit_write || fill_write;
    assign aw_line  = index;
    assign aw_kind  = fill_write;

    // ---- sequential ----
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= LOOKUP;
            valid <= '0; dirty <= '0; byp_inv <= '0;
            wait_cnt <= '0; had_miss <= 1'b0;
            cnt_access <= '0; cnt_hit <= '0; cnt_miss <= '0; cnt_fill <= '0; cnt_wb <= '0;
            cnt_bypass <= '0; cnt_refill_after_bypass <= '0; cnt_stall <= '0; cnt_write <= '0;
        end else begin
            if (dmiss) cnt_stall <= cnt_stall + 1;
            if (completing) begin
                cnt_access <= cnt_access + 1;
                if (we) cnt_write <= cnt_write + 1;
                if (we && bypass)        cnt_bypass <= cnt_bypass + 1;
                else if (had_miss)       cnt_miss <= cnt_miss + 1;
                else                     cnt_hit <= cnt_hit + 1;
                had_miss <= 1'b0;
            end
            case (state)
                LOOKUP: begin
                    if (re && !hit) begin
                        had_miss <= 1'b1;
                        state <= victim_dirty ? WB : FILL;
                        if (victim_dirty) cnt_wb <= cnt_wb + 1;
                        else              cnt_fill <= cnt_fill + 1;
                    end else if (we && bypass) begin
                        had_miss <= 1'b1;
                        if (hit && dirty[index]) begin
                            state <= BYP_WB; cnt_wb <= cnt_wb + 1;
                        end else begin
                            if (hit) begin valid[index] <= 1'b0; byp_inv[index] <= 1'b1; end
                            state <= BYP_WR;
                        end
                    end else if (we && !hit) begin
                        had_miss <= 1'b1;
                        state <= victim_dirty ? WB : FILL;
                        if (victim_dirty) cnt_wb <= cnt_wb + 1;
                        else              cnt_fill <= cnt_fill + 1;
                    end else if (we && hit) begin               // store hit: merge, set dirty
                        dirty[index] <= 1'b1;
                        if (DC_WRITE_LATENCY > 1) begin
                            state <= WAIT_ST;
                            wait_cnt <= 32'(DC_WRITE_LATENCY - 2);
                        end
                    end
                end
                WB: if (mem_done) begin
                    state <= FILL;
                    cnt_fill <= cnt_fill + 1;
                end
                BYP_WB: if (mem_done) begin
                    valid[index] <= 1'b0; dirty[index] <= 1'b0; byp_inv[index] <= 1'b1;
                    state <= BYP_WR;
                end
                FILL: if (mem_done) begin
                    valid[index] <= 1'b1; dirty[index] <= 1'b0;
                    if (byp_inv[index]) begin
                        cnt_refill_after_bypass <= cnt_refill_after_bypass + 1;
                        byp_inv[index] <= 1'b0;
                    end
                    if (DC_WRITE_LATENCY > 1) begin
                        state <= WAIT_FILL;
                        wait_cnt <= 32'(DC_WRITE_LATENCY - 2);
                    end else state <= LOOKUP;
                end
                BYP_WR: if (mem_done) state <= LOOKUP;
                WAIT_ST: begin
                    if (wait_cnt == 0) state <= LOOKUP;
                    else wait_cnt <= wait_cnt - 1;
                end
                WAIT_FILL: begin
                    if (wait_cnt == 0) state <= LOOKUP;
                    else wait_cnt <= wait_cnt - 1;
                end
                default: state <= LOOKUP;
            endcase
        end
    end

    // storage block: data and tags have no reset
    always_ff @(posedge clk) begin
        if (state == FILL && mem_done) begin
            data[index] <= mem_rdata;
            tags[index] <= tag;
        end else if (store_hit_write) begin
            for (int k = 0; k < 4; k++)
                if (be[k]) data[index][32 * wsel + 8 * k +: 8] <= wdata[8 * k +: 8];
        end
    end

    // ---- debug peek: NPEEK independent combinational lookups (no effect on the cache) ----
    for (genvar k = 0; k < NPEEK; k++) begin : g_peek
        logic [INDEX_BITS-1:0] pindex;
        logic [TAG_BITS-1:0]   ptag;
        logic [WSEL_BITS-1:0]  pwsel;
        assign pindex = peek_addr[32 * k + OFFSET_BITS +: INDEX_BITS];
        assign ptag   = peek_addr[32 * k + 31 -: TAG_BITS];
        assign pwsel  = peek_addr[32 * k + 2 +: WSEL_BITS];
        assign peek_hit[k]            = valid[pindex] && (tags[pindex] == ptag);
        assign peek_data[32 * k +: 32] = data[pindex][32 * pwsel +: 32];
    end
endmodule
