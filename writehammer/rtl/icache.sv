// icache: direct-mapped, read-only instruction cache with a line-fill FSM (T2.3).
//
// Geometry: CACHE_BYTES (default 2048) with LINE_BYTES-byte lines (16/32/64): NUM_LINES = CACHE_BYTES /
// LINE_BYTES (default 128). Address split: [offset: log2(LINE_BYTES)] [index: log2(NUM_LINES)] [tag: rest];
// the word inside the line is addr[offset-1:2]. valid is reset; tags and data are not.
//
// Lookup is combinational: on a hit rdata is the instruction at addr in the same cycle and imiss = 0.
// On a miss the cache raises imiss and refills the whole line from the memory: LOOKUP (miss) -> REFILL
// (hold mem_valid until mem_done) -> LOOKUP (hit). imiss stays 1 through the whole refill, including
// the mem_done cycle (the line is written at the end of that cycle). Cost: L + 2 cycles with imiss = 1
// per miss (L = memory latency).
// The refill uses the index and tag captured at the miss, not the live addr: addr is PCF, and a taken
// branch can change it while the refill runs; the line must be filled with the block that was
// requested, under that block's own tag. If PCF changes during a refill the refill finishes and the new
// address is looked up afterwards as a normal LOOKUP. rdata is don't-care while imiss = 1.
//
// Memory side: mem_valid is held (with mem_addr, the line-aligned address) until mem_done; the memory
// accepts when idle. Read only: no write path exists.
// Counters (simulation): cnt_lookup = cycles in LOOKUP (a fetch repeated while the pipeline is stalled
// counts each cycle), cnt_miss = misses = fills started (refill_cnt is the same number, kept for the
// earlier tests), cnt_stall = cycles with imiss = 1. Hits = lookups that did not miss.
// Does not model: self-modifying code or fence.i (code and data regions are disjoint, T2.5).
module icache #(
    parameter int CACHE_BYTES = 2048,
    parameter int LINE_BYTES = 16
)(
    input  logic                    clk,
    input  logic                    rst_n,
    /* verilator lint_off UNUSEDSIGNAL */  // KI-001: addr[1:0] unused, fetch is word-aligned
    input  logic [31:0]             addr,
    /* verilator lint_on UNUSEDSIGNAL */
    output logic [31:0]             rdata,
    output logic                    imiss,
    output logic                    mem_valid,
    output logic [31:0]             mem_addr,
    input  logic [8*LINE_BYTES-1:0] mem_rdata,
    input  logic                    mem_done,
    output logic [31:0]             refill_cnt,
    output logic [31:0]             cnt_lookup,
    output logic [31:0]             cnt_miss,
    output logic [31:0]             cnt_stall
);
    localparam int LINE_BITS   = 8 * LINE_BYTES;
    localparam int NUM_LINES   = CACHE_BYTES / LINE_BYTES;
    localparam int OFFSET_BITS = $clog2(LINE_BYTES);
    localparam int INDEX_BITS  = $clog2(NUM_LINES);
    localparam int TAG_BITS    = 32 - INDEX_BITS - OFFSET_BITS;
    localparam int WSEL_BITS   = OFFSET_BITS - 2;

    logic [NUM_LINES-1:0] valid;
    logic [TAG_BITS-1:0]  tags [NUM_LINES];
    logic [LINE_BITS-1:0] data [NUM_LINES];

    typedef enum logic {LOOKUP, REFILL} state_t;
    state_t state;

    logic [INDEX_BITS-1:0] miss_index;
    logic [TAG_BITS-1:0]   miss_tag;
    logic [INDEX_BITS-1:0] index;
    logic [TAG_BITS-1:0]   tag;
    logic [WSEL_BITS-1:0]  wordsel;
    logic                  hit;

    always_comb begin
        index    = addr[OFFSET_BITS +: INDEX_BITS];
        tag      = addr[31 -: TAG_BITS];
        wordsel  = addr[2 +: WSEL_BITS];
        hit      = valid[index] && (tags[index] == tag);

        imiss     = (state == LOOKUP) ? ~hit : 1'b1;
        rdata     = data[index][32 * wordsel +: 32];
        mem_valid = (state == REFILL);
        mem_addr  = {miss_tag, miss_index, {OFFSET_BITS{1'b0}}};
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= LOOKUP;
            valid <= '0;
            refill_cnt <= 0;
            cnt_lookup <= 0;
            cnt_miss <= 0;
            cnt_stall <= 0;
        end else begin
            if (state == LOOKUP) cnt_lookup <= cnt_lookup + 1;
            if (imiss) cnt_stall <= cnt_stall + 1;
            case (state)
                LOOKUP: begin
                    if (~hit) begin
                        miss_index <= index;
                        miss_tag <= tag;
                        refill_cnt <= refill_cnt + 1;
                        cnt_miss <= cnt_miss + 1;
                        state <= REFILL;
                    end
                end
                REFILL: begin
                    if (mem_done) begin
                        valid[miss_index] <= 1'b1;
                        state <= LOOKUP;
                    end
                end
                default: state <= LOOKUP;
            endcase
        end
    end

    // storage block: tags and data have no reset
    always_ff @(posedge clk) begin
        if (state == REFILL && mem_done) begin
            data[miss_index] <= mem_rdata;
            tags[miss_index] <= miss_tag;
        end
    end
endmodule
