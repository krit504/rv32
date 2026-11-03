// cache_system: I$ + D$ + write_guard, the part of the system the T6 cost study synthesizes (spec T6.5).
// No memory model: both caches present line-granule requests on the memory-side ports (one shared
// memory with D$ priority is the system integrator's job, see rv32_top_pipelined and rtl/mem_model.sv).
//
// Core side: i_addr -> i_rdata / imiss (fetch); d_addr/d_wdata/d_be/d_we/d_re -> d_rdata / dmiss (the
// Memory stage). d_stall is the effective stall of the Memory stage (dmiss plus any test freeze), used
// by write_guard as store_busy; connect it to the D$'s dmiss when there is no injected freeze.
// OBSERVE = 0 compiles the observation logic out: every observation output (cache counters, array-write
// and request trace, peek port, write_guard counters) is tied to 0 so synthesis removes the logic behind
// it; the functional behavior is identical (checked by the whole test suite through rv32_top_pipelined,
// which uses this module). Guard parameters: see rtl/write_guard.sv and docs/T5_INTERFACE.md.
module cache_system #(
    parameter int ICACHE_BYTES  = 2048,
    parameter int DCACHE_BYTES  = 2048,
    parameter int LINE_BYTES    = 16,
    parameter int DC_WRITE_LATENCY = 1,
    parameter int DETECTOR      = 0,
    parameter int WG_ACTION     = 0,
    parameter int WG_MODE       = 0,
    parameter int WG_WINDOW     = 10000,
    parameter int WG_THRESHOLD  = 1000,
    parameter int WG_M          = 16,
    parameter int WG_W          = 16,
    parameter int WG_PLACEBO_RATE = 0,
    parameter int WG_PLACEBO_SEED = 1,
    parameter bit OBSERVE       = 1'b1
)(
    input  logic        clk,
    input  logic        rst_n,
    // core side: instruction fetch
    input  logic [31:0] i_addr,
    output logic [31:0] i_rdata,
    output logic        imiss,
    // core side: data access (Memory stage)
    input  logic [31:0] d_addr,
    input  logic [31:0] d_wdata,
    input  logic [3:0]  d_be,
    input  logic        d_we,
    input  logic        d_re,
    input  logic        d_stall,
    output logic [31:0] d_rdata,
    output logic        dmiss,
    // memory side
    output logic                  ic_mem_valid,
    output logic [31:0]           ic_mem_addr,
    input  logic [8*LINE_BYTES-1:0] ic_mem_rdata,
    input  logic                  ic_mem_done,
    output logic                  dc_mem_valid,
    output logic                  dc_mem_we,
    output logic [31:0]           dc_mem_addr,
    output logic [8*LINE_BYTES-1:0] dc_mem_wdata,
    output logic [LINE_BYTES-1:0] dc_mem_be,
    input  logic                  dc_mem_done,
    input  logic [8*LINE_BYTES-1:0] dc_mem_rdata,
    // observation (zero when OBSERVE = 0)
    output logic        stall_req,          // write_guard action A2 request (always 0, A2 not implemented)
    output logic        wg_restricted,
    output logic [31:0] wg_cycles_restricted,
    output logic [31:0] wg_first_restrict,
    output logic [31:0] wg_stores,
    output logic [31:0] wg_stores_restricted,
    output logic [31:0] ic_refill_cnt,
    output logic [31:0] ic_cnt_lookup,
    output logic [31:0] ic_cnt_miss,
    output logic [31:0] ic_cnt_stall,
    output logic [31:0] dc_refill_cnt,
    output logic [31:0] dc_write_cnt,
    output logic        dc_aw_valid,
    output logic [31:0] dc_aw_line,
    output logic        dc_aw_kind,
    output logic        dc_tr_valid,
    output logic        dc_tr_we,
    output logic [31:0] dc_tr_addr,
    output logic [2:0]  dc_tr_size,
    output logic        dc_tr_bypass,
    output logic [31:0] dc_cnt_access,
    output logic [31:0] dc_cnt_hit,
    output logic [31:0] dc_cnt_miss,
    output logic [31:0] dc_cnt_wb,
    output logic [31:0] dc_cnt_bypass,
    output logic [31:0] dc_cnt_rab,
    output logic [31:0] dc_cnt_stall,
    input  logic [29:0] peek_word,          // word index to read through the D$ (debug)
    output logic [4:0]  peek_hit,           // port 0 = peek_word, ports 1..4 = words 0..3
    output logic [159:0] peek_data
);
    localparam int LINES = DCACHE_BYTES / LINE_BYTES;
    localparam int IDXW  = $clog2(LINES);

    logic        bypass_w;
    logic        aw_valid_w;
    logic [IDXW-1:0] aw_line_w;
    logic        aw_kind_w, tr_valid_w, tr_we_w, tr_bypass_w;
    logic [31:0] tr_addr_w;
    logic [2:0]  tr_size_w;
    logic [31:0] ic_refill_w, ic_lookup_w, ic_miss_w, ic_stall_w;
    logic [31:0] c_access, c_hit, c_miss, c_fill, c_wb, c_bypass, c_rab, c_stall, c_write;
    logic [4:0]  peek_hit_w;
    logic [159:0] peek_data_w;
    logic        wg_restr_w;
    logic [31:0] wg_cr_w, wg_fr_w, wg_st_w, wg_sr_w;

    write_guard #(.DETECTOR(DETECTOR), .ACTION(WG_ACTION), .MODE(WG_MODE), .WINDOW_CYCLES(WG_WINDOW),
                  .THRESHOLD(WG_THRESHOLD), .M(WG_M), .W(WG_W), .LINES(LINES),
                  .PLACEBO_RATE(WG_PLACEBO_RATE), .PLACEBO_SEED(WG_PLACEBO_SEED), .OBSERVE(OBSERVE)) u_write_guard(
        .clk(clk),
        .rst_n(rst_n),
        .store_valid(d_we),
        .store_busy(d_stall),
        .store_line(32'(d_addr[$clog2(LINE_BYTES) +: IDXW])),
        .array_write_valid(aw_valid_w),
        .line_idx(32'(aw_line_w)),
        .cycle_strobe(1'b1),
        .bypass_store(bypass_w),
        .stall_req(stall_req),
        .restricted(wg_restr_w),
        .obs_cycles_restricted(wg_cr_w),
        .obs_first_restrict(wg_fr_w),
        .obs_stores(wg_st_w),
        .obs_stores_restricted(wg_sr_w)
    );

    icache #(.CACHE_BYTES(ICACHE_BYTES), .LINE_BYTES(LINE_BYTES)) u_icache(
        .clk(clk),
        .rst_n(rst_n),
        .addr(i_addr),
        .rdata(i_rdata),
        .imiss(imiss),
        .mem_valid(ic_mem_valid),
        .mem_addr(ic_mem_addr),
        .mem_rdata(ic_mem_rdata),
        .mem_done(ic_mem_done),
        .refill_cnt(ic_refill_w),
        .cnt_lookup(ic_lookup_w),
        .cnt_miss(ic_miss_w),
        .cnt_stall(ic_stall_w)
    );

    dcache #(.CACHE_BYTES(DCACHE_BYTES), .LINE_BYTES(LINE_BYTES), .DC_WRITE_LATENCY(DC_WRITE_LATENCY), .NPEEK(5)) u_dcache(
        .clk(clk),
        .rst_n(rst_n),
        .addr(d_addr),
        .wdata(d_wdata),
        .be(d_be),
        .we(d_we),
        .re(d_re),
        .bypass(bypass_w),
        .rdata(d_rdata),
        .dmiss(dmiss),
        .mem_valid(dc_mem_valid),
        .mem_we(dc_mem_we),
        .mem_addr(dc_mem_addr),
        .mem_wdata(dc_mem_wdata),
        .mem_be(dc_mem_be),
        .mem_done(dc_mem_done),
        .mem_rdata(dc_mem_rdata),
        .aw_valid(aw_valid_w),
        .aw_line(aw_line_w),
        .aw_kind(aw_kind_w),
        .tr_valid(tr_valid_w),
        .tr_we(tr_we_w),
        .tr_addr(tr_addr_w),
        .tr_size(tr_size_w),
        .tr_bypass(tr_bypass_w),
        .cnt_access(c_access),
        .cnt_hit(c_hit),
        .cnt_miss(c_miss),
        .cnt_fill(c_fill),
        .cnt_wb(c_wb),
        .cnt_bypass(c_bypass),
        .cnt_refill_after_bypass(c_rab),
        .cnt_stall(c_stall),
        .cnt_write(c_write),
        .peek_addr(OBSERVE ? {32'd12, 32'd8, 32'd4, 32'd0, peek_word, 2'b00} : '0),
        .peek_hit(peek_hit_w),
        .peek_data(peek_data_w)
    );

    if (OBSERVE) begin : g_obs
        assign wg_restricted        = wg_restr_w;
        assign wg_cycles_restricted = wg_cr_w;
        assign wg_first_restrict    = wg_fr_w;
        assign wg_stores            = wg_st_w;
        assign wg_stores_restricted = wg_sr_w;
        assign ic_refill_cnt = ic_refill_w;  assign ic_cnt_lookup = ic_lookup_w;
        assign ic_cnt_miss = ic_miss_w;      assign ic_cnt_stall = ic_stall_w;
        assign dc_refill_cnt = c_fill;       assign dc_write_cnt = c_write;
        assign dc_aw_valid = aw_valid_w;     assign dc_aw_line = 32'(aw_line_w);  assign dc_aw_kind = aw_kind_w;
        assign dc_tr_valid = tr_valid_w;     assign dc_tr_we = tr_we_w;           assign dc_tr_addr = tr_addr_w;
        assign dc_tr_size = tr_size_w;       assign dc_tr_bypass = tr_bypass_w;
        assign dc_cnt_access = c_access;     assign dc_cnt_hit = c_hit;           assign dc_cnt_miss = c_miss;
        assign dc_cnt_wb = c_wb;             assign dc_cnt_bypass = c_bypass;     assign dc_cnt_rab = c_rab;
        assign dc_cnt_stall = c_stall;
        assign peek_hit = peek_hit_w;        assign peek_data = peek_data_w;
    end else begin : g_noobs
        /* verilator lint_off UNUSEDSIGNAL */  // the observation signals are intentionally dropped
        logic unused_obs;
        assign unused_obs = wg_restr_w ^ (^wg_cr_w) ^ (^wg_fr_w) ^ (^wg_st_w) ^ (^wg_sr_w) ^ (^ic_refill_w) ^ (^ic_lookup_w)
                          ^ (^ic_miss_w) ^ (^ic_stall_w) ^ (^c_access) ^ (^c_hit) ^ (^c_miss) ^ (^c_fill) ^ (^c_wb)
                          ^ (^c_bypass) ^ (^c_rab) ^ (^c_stall) ^ (^c_write) ^ aw_kind_w ^ tr_valid_w ^ tr_we_w
                          ^ tr_bypass_w ^ (^tr_addr_w) ^ (^tr_size_w) ^ (^peek_hit_w) ^ (^peek_data_w) ^ (^peek_word);
        /* verilator lint_on UNUSEDSIGNAL */
        assign wg_restricted = 1'b0;  assign wg_cycles_restricted = '0;  assign wg_first_restrict = '0;
        assign wg_stores = '0;        assign wg_stores_restricted = '0;
        assign ic_refill_cnt = '0;    assign ic_cnt_lookup = '0;  assign ic_cnt_miss = '0;  assign ic_cnt_stall = '0;
        assign dc_refill_cnt = '0;    assign dc_write_cnt = '0;
        assign dc_aw_valid = 1'b0;    assign dc_aw_line = '0;     assign dc_aw_kind = 1'b0;
        assign dc_tr_valid = 1'b0;    assign dc_tr_we = 1'b0;     assign dc_tr_addr = '0;
        assign dc_tr_size = '0;       assign dc_tr_bypass = 1'b0;
        assign dc_cnt_access = '0;    assign dc_cnt_hit = '0;     assign dc_cnt_miss = '0;
        assign dc_cnt_wb = '0;        assign dc_cnt_bypass = '0;  assign dc_cnt_rab = '0;  assign dc_cnt_stall = '0;
        assign peek_hit = '0;         assign peek_data = '0;
    end
endmodule
