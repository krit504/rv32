// mem_model: SIMULATION-ONLY unified main-memory model behind the I$ and D$ (T2.1). Not synthesizable
// logic (behavioural array, $readmemh); the cache system is what T6.5 synthesizes, not this module.
//
// One memory array of WORDS 32-bit words (default 65536 = 256 KiB) shared by both caches, loaded at
// time 0 from INIT_FILE (zero filled first, so words past the image read 0). Addresses wrap modulo the
// size. Two request ports, one request in flight at a time, the D$ port has priority when both
// request in the same idle cycle; a request that arrives while the memory is busy waits for the next
// idle cycle (non-preemptive).
//
// Port protocol (per master): the master holds `valid` and the request fields until `done`.
//   `ready` pulses in the cycle the request is accepted (valid && ready is the handshake).
//   `done` is high for exactly one cycle, LATENCY cycles after acceptance (acceptance cycle = cycle 0,
//   so LATENCY = 1 means done in the next cycle); a read returns the whole line in `rdata` in that
//   cycle; a write takes effect at the clock edge that ends the `done` cycle.
// Latency: fixed LATENCY (>= 1), or with RANDOM_LATENCY = 1 a value drawn per request uniformly from
// 1 .. 2*LATENCY-1 by a seeded 16-bit LFSR (deterministic for a given SEED and request sequence).
// Line transfers: `LINE_BYTES` bytes (16/32/64), word k of a line is rdata[32*k +: 32], word 0 is the
// lowest address. D$ writes carry a full line image and byte enables: byte j of the line is written
// iff d_be[j]; address is the line base (a line write has all enables set, a store that bypasses the
// cache sets only the store's bytes). The instruction port is read-only.
//
// Checks nothing itself (tests/mem_model_test.py with tb/tb_mem_model.sv does). Known limits: no
// misaligned or sub-line-aligned requests (addresses are rounded down to the line), no error responses.
module mem_model #(
    parameter int WORDS = 65536,
    parameter int LINE_BYTES = 16,
    parameter int LATENCY = 20,
    parameter bit RANDOM_LATENCY = 1'b0,
    parameter int SEED = 1,
    parameter INIT_FILE = ""
)(
    input  logic                    clk,
    input  logic                    rst_n,
    // instruction cache port (read only)
    input  logic                    i_valid,
    output logic                    i_ready,
    input  logic [31:0]             i_addr,
    output logic                    i_done,
    output logic [8*LINE_BYTES-1:0] i_rdata,
    // data cache port (priority)
    input  logic                    d_valid,
    output logic                    d_ready,
    input  logic                    d_we,
    input  logic [31:0]             d_addr,
    input  logic [8*LINE_BYTES-1:0] d_wdata,
    input  logic [LINE_BYTES-1:0]   d_be,
    output logic                    d_done,
    output logic [8*LINE_BYTES-1:0] d_rdata
);
    localparam int LINE_BITS  = 8 * LINE_BYTES;
    localparam int WPL        = LINE_BYTES / 4;                 // words per line
    localparam int ADDR_BITS  = $clog2(WORDS);
    localparam int LAT_BITS   = $clog2(2 * LATENCY + 1) + 1;

    logic [31:0] mem [0:WORDS-1];
    initial begin
        for (int i = 0; i < WORDS; i++) mem[i] = 32'b0;
        if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
    end

    typedef enum logic {IDLE, BUSY} state_t;
    state_t state;
    logic                 sel_d;          // the request in flight belongs to the D$
    logic                 we_q;
    /* verilator lint_off UNUSEDSIGNAL */  // KI-013: only the array-index bits of the latched address are used
    logic [31:0]          addr_q;
    /* verilator lint_on UNUSEDSIGNAL */
    logic [LINE_BITS-1:0] wdata_q;
    logic [LINE_BYTES-1:0] be_q;
    logic [LAT_BITS-1:0]  cnt;
    logic [15:0]          lfsr;

    // word index of the first word of the latched line
    logic [ADDR_BITS-1:0] line_w;
    assign line_w = {addr_q[ADDR_BITS+1:$clog2(LINE_BYTES)], {($clog2(LINE_BYTES) - 2){1'b0}}};

    logic done_now;
    assign done_now = (state == BUSY) && (cnt == '0);
    assign i_done = done_now && !sel_d;
    assign d_done = done_now && sel_d;

    // accept: D$ first, then I$, only when idle
    wire take_d = (state == IDLE) && d_valid;
    wire take_i = (state == IDLE) && !d_valid && i_valid;
    assign d_ready = take_d;
    assign i_ready = take_i;

    // the line at the latched address (valid and used in the done cycle of a read)
    logic [LINE_BITS-1:0] line;
    always_comb begin
        for (int k = 0; k < WPL; k++) line[32*k +: 32] = mem[line_w + ADDR_BITS'(k)];
    end
    assign i_rdata = (i_done) ? line : '0;
    assign d_rdata = (d_done && !we_q) ? line : '0;

    // latency for the request being accepted (drawn from the LFSR in random mode)
    logic [LAT_BITS-1:0] lat_new;
    always_comb begin
        if (RANDOM_LATENCY) lat_new = LAT_BITS'(1 + (int'(lfsr) % (2 * LATENCY - 1)));
        else                lat_new = LAT_BITS'(LATENCY);
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE;
            cnt <= '0;
            lfsr <= 16'(SEED == 0 ? 1 : SEED);
        end else begin
            lfsr <= {lfsr[14:0], lfsr[15] ^ lfsr[13] ^ lfsr[12] ^ lfsr[10]};
            case (state)
                IDLE: if (take_d || take_i) begin
                    state <= BUSY;
                    sel_d <= take_d;
                    addr_q <= take_d ? d_addr : i_addr;
                    we_q <= take_d && d_we;
                    wdata_q <= d_wdata;
                    be_q <= d_be;
                    cnt <= lat_new - 1'b1;
                end
                BUSY: begin
                    if (cnt != '0) cnt <= cnt - 1'b1;
                    else begin
                        state <= IDLE;
                        if (we_q)                            // write at the edge ending the done cycle
                            for (int j = 0; j < LINE_BYTES; j++)
                                if (be_q[j]) mem[line_w + ADDR_BITS'(j / 4)][8 * (j % 4) +: 8] <= wdata_q[8 * j +: 8];
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
