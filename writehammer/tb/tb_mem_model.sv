`timescale 1ns/1ps
// tb_mem_model: unit test of mem_model (T2.1). Prints "MEMMODEL errors=<n>" and each failure.
// Parameters: LAT, LINE_BYTES, RANDOM (1 = random latency), SEED.
// Checks: done exactly LAT cycles after acceptance (fixed mode), latency in [1, 2*LAT-1] and
// reproducible (random mode), line word packing (word k = rdata[32k +: 32]), byte-enable writes
// (only enabled bytes change), a write is visible to a read issued after it and not before its done
// edge, D$ priority when both masters request in the same cycle, the I$ request waits for the D$
// request in flight and is served right after it, done is a one-cycle pulse, INIT_FILE words land at
// address 0 and words past the image read 0, the instruction port never writes.
// Does not check: requests with misaligned addresses (unsupported).
module tb_mem_model #(
    parameter int LAT = 3,
    parameter int LINE_BYTES = 16,
    parameter bit RANDOM = 1'b0,
    parameter int SEED = 5
);
    localparam int LB = 8 * LINE_BYTES;
    logic clk = 1'b0, rst_n = 1'b0;
    always #5 clk = ~clk;

    logic i_valid = 0, d_valid = 0, d_we = 0;
    logic [31:0] i_addr = 0, d_addr = 0;
    logic [LB-1:0] d_wdata = 0;
    logic [LINE_BYTES-1:0] d_be = 0;
    wire i_ready, d_ready, i_done, d_done;
    wire [LB-1:0] i_rdata, d_rdata;

    mem_model #(.WORDS(1024), .LINE_BYTES(LINE_BYTES), .LATENCY(LAT), .RANDOM_LATENCY(RANDOM), .SEED(SEED), .INIT_FILE("init.hex")) dut (
        .clk(clk), .rst_n(rst_n),
        .i_valid(i_valid), .i_ready(i_ready), .i_addr(i_addr), .i_done(i_done), .i_rdata(i_rdata),
        .d_valid(d_valid), .d_ready(d_ready), .d_we(d_we), .d_addr(d_addr), .d_wdata(d_wdata), .d_be(d_be),
        .d_done(d_done), .d_rdata(d_rdata));

    int errors = 0;
    int cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    task automatic fail(string m); begin errors++; $display("FAIL %s", m); end endtask

    // one request on the D$ port; returns the latency (accept to done) and the data
    task automatic d_req(input bit we, input [31:0] addr, input [LB-1:0] wd, input [LINE_BYTES-1:0] be,
                         output int lat, output [LB-1:0] rd);
        int acc, don, pulses;
        begin
            @(negedge clk); d_valid = 1; d_we = we; d_addr = addr; d_wdata = wd; d_be = be;
            acc = -1; don = -1; pulses = 0;
            while (don < 0) begin
                @(posedge clk);
                if (d_valid && d_ready && acc < 0) acc = cyc;
                if (d_done) begin don = cyc; rd = d_rdata; pulses++; end
                #1;
            end
            @(negedge clk); d_valid = 0; d_we = 0;
            @(posedge clk); #1;
            if (d_done) fail("d_done high for more than one cycle");
            lat = don - acc;
        end
    endtask

    function automatic [LB-1:0] pattern(input [31:0] base);
        for (int k = 0; k < LINE_BYTES / 4; k++) pattern[32*k +: 32] = base + 32'h1111 * (k + 1);
    endfunction

    int lat; logic [LB-1:0] rd, wr;
    int lats [0:15];
    initial begin
        repeat (3) @(posedge clk); #1 rst_n = 1'b1;

        // INIT_FILE: words 0..3 = a0..a3, rest 0
        d_req(0, 0, 0, 0, lat, rd);
        begin
            logic [31:0] expw;                      // assigned per iteration: an initializer on a
            for (int k = 0; k < LINE_BYTES / 4; k++) begin   // declaration in a loop runs only once
                expw = (k < 4) ? 32'ha0 + k : 32'h0;
                if (rd[32*k +: 32] !== expw) fail($sformatf("init word %0d = %h expected %h", k, rd[32*k +: 32], expw));
            end
        end
        if (!RANDOM && lat != LAT) fail($sformatf("read latency %0d expected %0d", lat, LAT));
        if (RANDOM && (lat < 1 || lat > 2 * LAT - 1)) fail($sformatf("random latency %0d outside 1..%0d", lat, 2 * LAT - 1));

        // full line write then read back (packing and lane order)
        wr = pattern(32'h1000);
        d_req(1, 32'h40, wr, {LINE_BYTES{1'b1}}, lat, rd);
        d_req(0, 32'h40, 0, 0, lat, rd);
        if (rd !== wr) fail($sformatf("line readback %h expected %h", rd, wr));
        for (int k = 0; k < LINE_BYTES / 4; k++)
            if (dut.mem[(32'h40 >> 2) + k] !== 32'h1000 + 32'h1111 * (k + 1)) fail($sformatf("array word %0d wrong", k));

        // byte-enable write: only enabled bytes change (bytes 1, 5 and the last byte)
        begin
            logic [LINE_BYTES-1:0] be;
            logic [LB-1:0] orig, neww, expd;
            be = '0; be[1] = 1; be[5] = 1; be[LINE_BYTES-1] = 1;
            orig = rd; neww = {LINE_BYTES{8'hEE}};     // procedural: initializers on declarations run once at time 0
            d_req(1, 32'h40, neww, be, lat, rd);
            d_req(0, 32'h40, 0, 0, lat, rd);
            expd = orig;
            for (int j = 0; j < LINE_BYTES; j++) if (be[j]) expd[8*j +: 8] = 8'hEE;
            if (rd !== expd) fail($sformatf("byte-enable write: %h expected %h", rd, expd));
        end

        // a write is not visible before its done edge: the read issued after is
        d_req(1, 32'h80, pattern(32'h2000), {LINE_BYTES{1'b1}}, lat, rd);
        if (dut.mem[32'h80 >> 2] !== 32'h2000 + 32'h1111) fail("write not in the array after its done cycle");

        // I$ port: read, and it is read-only (no write path exists); latency exact in fixed mode
        @(negedge clk); i_valid = 1; i_addr = 32'h40;
        begin
            int acc = -1, don = -1;
            while (don < 0) begin
                @(posedge clk);
                if (i_valid && i_ready && acc < 0) acc = cyc;
                if (i_done) begin don = cyc; if (i_rdata[31:0] !== dut.mem[32'h40 >> 2]) fail("i_rdata word 0 wrong"); end
                #1;
            end
            if (!RANDOM && don - acc != LAT) fail($sformatf("I$ latency %0d expected %0d", don - acc, LAT));
            @(negedge clk); i_valid = 0;
        end

        // priority and waiting: both request in the same cycle; D$ is served first, I$ right after it
        begin
            int d_acc = -1, d_don = -1, i_acc = -1, i_don = -1;
            @(negedge clk); d_valid = 1; d_we = 0; d_addr = 32'h40; i_valid = 1; i_addr = 32'h80;
            while (i_don < 0) begin
                @(posedge clk);
                if (d_valid && d_ready && d_acc < 0) d_acc = cyc;
                if (i_valid && i_ready && i_acc < 0) i_acc = cyc;
                if (d_done) begin d_don = cyc; #1 d_valid = 0; end
                if (i_done) i_don = cyc;
                #1;
            end
            @(negedge clk); i_valid = 0;
            if (d_acc < 0 || i_acc < 0) fail("a request was never accepted");
            if (!(d_acc < i_acc)) fail($sformatf("D$ not served first (d accept %0d, i accept %0d)", d_acc, i_acc));
            if (i_acc <= d_don) fail($sformatf("I$ accepted (%0d) before D$ done (%0d): not non-preemptive", i_acc, d_don));
            if (i_acc != d_don + 1) fail($sformatf("I$ not served right after D$: accept %0d, D$ done %0d", i_acc, d_don));
        end

        // latency sequence (random mode: bounds and spread; fixed mode: constant)
        for (int n = 0; n < 16; n++) begin
            d_req(0, 32'h40, 0, 0, lat, rd);
            lats[n] = lat;
            if (!RANDOM && lat != LAT) fail($sformatf("latency %0d expected %0d", lat, LAT));
            if (RANDOM && (lat < 1 || lat > 2 * LAT - 1)) fail($sformatf("random latency %0d outside 1..%0d", lat, 2 * LAT - 1));
        end
        if (RANDOM && LAT > 1) begin
            int distinct = 0;
            for (int a = 0; a < 16; a++) begin int seen = 0; for (int b = 0; b < a; b++) if (lats[b] == lats[a]) seen = 1; if (!seen) distinct++; end
            if (distinct < 2) fail("random latency never varied");
        end
        $write("LATSEQ"); for (int n = 0; n < 16; n++) $write(" %0d", lats[n]); $write("\n");

        $display("MEMMODEL errors=%0d", errors);
        $finish;
    end
endmodule
