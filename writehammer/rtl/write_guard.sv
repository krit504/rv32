// write_guard: decides, per store, whether the D$ must handle it as a restricted (bypassed) store
// (spec T5.1). Detectors D1 (per-line counters), D2 (hashed counters), D3 (store rate) and the test
// controls NEVER, ALWAYS, PLACEBO.
//
// DETECTOR: 0 NONE   never restricts (the plain cache)
//           1 ALWAYS test control: restricts every store (upper bound)
//           2 D1     one W-bit saturating counter per D$ line, counts data-array writes
//           3 D2     M hashed counters (hash: see bucket() below), counts data-array writes
//           4 D3     one counter of completed stores; above THRESHOLD the whole store stream is restricted
//           5 NEVER  test control: restricts nothing; must match NONE in every metric
//           6 PLACEBO test control: restricts a seeded pseudo-random fraction PLACEBO_RATE/65536 of stores
// ACTION: 0 = A1 (bypass the D$ array). 1 = A2 (stall-throttle) is not implemented: elaboration error.
// MODE (D3 only): 0 STATIC (the restriction latches until reset), 1 ADAPTIVE (re-evaluated each window).
//
// Windowing: a counter of cycles (cycle_strobe) runs to WINDOW_CYCLES; at the end of a window the D1/D2/D3
// counters are CLEARED (so each counter is the count within one window, which is what the calibration
// measures, DEC-011). A counter that exceeds THRESHOLD sets its hot flag at once; at a window end a hot
// flag is released if that window's final count is below THRESHOLD/2 (hysteresis), otherwise it stays.
// D1/D2 count data-array writes (store hits and fills, a bypassed store produces none); D3 counts store
// completions including bypassed ones, so a store-heavy stream stays restricted.
//
// Stability: bypass_store depends on store_valid and on the hot flags only. dcache needs the decision to
// be constant while a store is in the Memory stage, so the hot flags (and the window processing) change
// only in cycles where no store is mid-request (freeze = store_valid && store_busy). Counters keep
// counting meanwhile; a window end that falls in a frozen cycle is processed at the next unfrozen one.
//
// Inputs: store_valid = a store (not MMIO) is in the Memory stage; store_busy = that stage is not
// advancing this cycle; store_line = D$ line index the store targets (address bits); array_write_valid /
// line_idx = the D$ data-array write event of this cycle and its line; cycle_strobe = 1 every cycle.
// Outputs: bypass_store (combinational in store_valid, flags), stall_req (A2, 0), restricted = any
// hot flag / the control's restriction is set. Observation (OBSERVE=1, otherwise tied to 0):
//   obs_cycles_restricted  cycles with restricted = 1
//   obs_first_restrict     cycle count when restricted first became 1 (32'hFFFFFFFF if never)
//   obs_stores             completed stores
//   obs_stores_restricted  completed stores that were bypassed
module write_guard #(
    parameter int DETECTOR      = 0,
    parameter int ACTION        = 0,
    parameter int MODE          = 0,
    parameter int WINDOW_CYCLES = 10000,
    parameter int THRESHOLD     = 1000,
    parameter int M             = 16,          // D2 counters, power of two, at most 64
    parameter int W             = 16,          // counter width
    parameter int LINES         = 128,         // D$ lines (power of two)
    parameter int PLACEBO_RATE  = 0,           // PLACEBO: restricted fraction in 1/65536
    parameter int PLACEBO_SEED  = 1,
    parameter bit OBSERVE       = 1'b1
)(
    input  logic        clk,
    input  logic        rst_n,
    /* verilator lint_off UNUSEDSIGNAL */  // KI-015: each detector uses a subset of the observation inputs
    input  logic        store_valid,
    input  logic        store_busy,
    input  logic [31:0] store_line,
    input  logic        array_write_valid,
    input  logic [31:0] line_idx,
    input  logic        cycle_strobe,
    /* verilator lint_on UNUSEDSIGNAL */
    output logic        bypass_store,
    output logic        stall_req,
    output logic        restricted,
    output logic [31:0] obs_cycles_restricted,
    output logic [31:0] obs_first_restrict,
    output logic [31:0] obs_stores,
    output logic [31:0] obs_stores_restricted
);
    localparam int IDXW = $clog2(LINES);
    localparam int LOGM = $clog2(M);
    localparam logic [W-1:0] SATMAX = '1;
    localparam int HALF = THRESHOLD / 2;

    if (ACTION != 0) begin : g_a2
        $error("write_guard: ACTION %0d (A2 stall-throttle) not implemented", ACTION);
    end
    if (DETECTOR == 3 && (M > LINES / 2 || M > 64 || (M & (M - 1)) != 0)) begin : g_m
        $error("write_guard: D2 needs M a power of two, at most 64 and at most LINES/2");
    end

    // XOR-fold of the index bits (8-bit fold of a 16-bit zero-extended index), multiply by the odd
    // constant 167 (8-bit result), take the top LOGM bits.
    function automatic logic [LOGM > 0 ? LOGM - 1 : 0:0] bucket(input logic [15:0] idx);
        logic [7:0] f;
        /* verilator lint_off UNUSEDSIGNAL */  // low bits of the product are discarded by design
        logic [7:0] p;
        /* verilator lint_on UNUSEDSIGNAL */
        f = idx[7:0] ^ idx[15:8];
        p = 8'(16'(f) * 16'd167);
        bucket = p[7 -: (LOGM > 0 ? LOGM : 1)];
    endfunction

    wire freeze     = store_valid && store_busy;
    wire store_done = store_valid && !store_busy;

    // ---- window timer: counts cycles, processed at the first unfrozen cycle at or after the end ----
    logic [31:0] wtimer;
    logic        win_proc;
    assign win_proc = (wtimer >= 32'(WINDOW_CYCLES - 1)) && !freeze;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)                          wtimer <= '0;
        else if (win_proc)                   wtimer <= '0;
        else if (wtimer < 32'(WINDOW_CYCLES - 1)) wtimer <= wtimer + 32'(cycle_strobe);
    end

    logic hot_store;   // the decision for the store in Memory
    logic any_hot;

    if (DETECTOR == 0 || DETECTOR == 5) begin : g_none
        assign hot_store = 1'b0;
        assign any_hot   = 1'b0;
    end else if (DETECTOR == 1) begin : g_always
        assign hot_store = 1'b1;
        assign any_hot   = 1'b1;
    end else if (DETECTOR == 2 || DETECTOR == 3) begin : g_cnt
        localparam int NC = (DETECTOR == 2) ? LINES : M;
        logic [W-1:0] cnt [NC];
        logic [NC-1:0] hot;
        logic [31:0]  widx;
        if (DETECTOR == 2) begin : g_i
            assign widx = 32'(line_idx[IDXW-1:0]);
        end else begin : g_i
            assign widx = 32'(bucket({{(16-IDXW){1'b0}}, line_idx[IDXW-1:0]}));
        end
        logic [31:0] sidx;
        if (DETECTOR == 2) begin : g_s
            assign sidx = 32'(store_line[IDXW-1:0]);
        end else begin : g_s
            assign sidx = 32'(bucket({{(16-IDXW){1'b0}}, store_line[IDXW-1:0]}));
        end
        for (genvar i = 0; i < NC; i++) begin : g_c
            wire          inc   = array_write_valid && (widx == 32'(i));
            wire [W-1:0]  cnt_n = (inc && cnt[i] != SATMAX) ? cnt[i] + 1'b1 : cnt[i];
            always_ff @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    cnt[i] <= '0;
                    hot[i] <= 1'b0;
                end else if (win_proc) begin
                    cnt[i] <= '0;
                    if (32'(cnt_n) > 32'(THRESHOLD))      hot[i] <= 1'b1;
                    else if (32'(cnt_n) < 32'(HALF))      hot[i] <= 1'b0;
                end else begin
                    cnt[i] <= cnt_n;
                    if (!freeze && 32'(cnt_n) > 32'(THRESHOLD)) hot[i] <= 1'b1;
                end
            end
        end
        assign hot_store = hot[sidx[$clog2(NC) > 0 ? $clog2(NC) - 1 : 0:0]];
        assign any_hot   = |hot;
    end else if (DETECTOR == 4) begin : g_d3
        logic [W-1:0] cnt;
        logic         flag;
        wire [W-1:0]  cnt_n = (store_done && cnt != SATMAX) ? cnt + 1'b1 : cnt;
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                cnt  <= '0;
                flag <= 1'b0;
            end else if (win_proc) begin
                cnt <= '0;
                if (32'(cnt_n) > 32'(THRESHOLD))                          flag <= 1'b1;
                else if (MODE == 1 && 32'(cnt_n) < 32'(HALF))             flag <= 1'b0;
            end else begin
                cnt <= cnt_n;
                if (!freeze && 32'(cnt_n) > 32'(THRESHOLD)) flag <= 1'b1;
            end
        end
        assign hot_store = flag;
        assign any_hot   = flag;
    end else if (DETECTOR == 6) begin : g_placebo
        logic [31:0] rng;
        logic        flag;
        // xorshift32, advanced once per completed store
        wire [31:0] x1 = rng ^ (rng << 13);
        wire [31:0] x2 = x1 ^ (x1 >> 17);
        wire [31:0] x3 = x2 ^ (x2 << 5);
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                rng  <= (PLACEBO_SEED == 0) ? 32'd1 : 32'(PLACEBO_SEED);
                flag <= 1'b0;
            end else if (store_done) begin
                rng  <= x3;
                flag <= (32'(x3[15:0]) < 32'(PLACEBO_RATE));
            end
        end
        assign hot_store = flag;
        assign any_hot   = flag;
    end else begin : g_unimplemented
        $error("write_guard: unknown DETECTOR %0d", DETECTOR);
    end

    assign bypass_store = store_valid && hot_store;
    assign restricted   = any_hot;
    assign stall_req    = 1'b0;

    // ---- observation hooks (T5.9) ----
    if (OBSERVE) begin : g_obs
        logic [31:0] cyc;
        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                cyc                   <= '0;
                obs_cycles_restricted <= '0;
                obs_first_restrict    <= 32'hFFFFFFFF;
                obs_stores            <= '0;
                obs_stores_restricted <= '0;
            end else begin
                cyc <= cyc + 32'(cycle_strobe);
                if (any_hot) begin
                    obs_cycles_restricted <= obs_cycles_restricted + 1'b1;
                    if (obs_first_restrict == 32'hFFFFFFFF) obs_first_restrict <= cyc;
                end
                if (store_done) begin
                    obs_stores <= obs_stores + 1'b1;
                    if (bypass_store) obs_stores_restricted <= obs_stores_restricted + 1'b1;
                end
            end
        end
    end else begin : g_noobs
        assign obs_cycles_restricted = '0;
        assign obs_first_restrict    = '0;
        assign obs_stores            = '0;
        assign obs_stores_restricted = '0;
    end
endmodule
