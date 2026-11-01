`timescale 1ns/1ps
// sys_monitor: simulation-only MMIO device and performance counters (T1.3).
//
// MMIO map (stores only; base 0xF000_0000, decoded by the core, see rv32_top_pipelined mmio_*):
//   +0x00 HALT      write exit code; prints "HALT <code>" and the PERF line, then ends the run
//   +0x04 START     clears the counters and (re)starts the measurement window
//   +0x08 STOP      ends the window
//   +0x0C PHASE     write a marker value; prints "PHASE <value> cycle=<n>" (n = cycles since reset)
//   +0x10 PUTCHAR   write a character (low byte); prints "CHR <code>" (the Python side joins them)
//
// Window: counting is on from reset (a program that never writes START is measured whole) and is
// restarted by START. The window holds the cycles after the START store's Memory cycle up to and
// including the STOP store's Memory cycle. The START store itself is counted as retired (it leaves
// Writeback in the first window cycle); the STOP store is not.
// Boundary rule: a stall or redirect is counted when its signal is high in a window cycle. One
// that fires in or before the START store's Memory cycle has its bubbles inside the window but
// its signal outside it, so it is not counted. With at least one instruction between START and the
// first hazard, N retired instructions, s load-use stalls and f redirects give exactly
// N + s + 2f cycles. The HALT report is printed one cycle after the HALT store so the counters
// include the cycle that store spent in Memory.
//
// PERF line, printed once at HALT, CSV (columns in this order):
//   PERF,cycles,instret,stall_loaduse,flush_cycles,imiss_cycles,dmiss_cycles
//   cycles        clock cycles in the window
//   instret       instructions that left Writeback in the window (flushed bubbles do not count)
//   stall_loaduse cycles where the hazard unit holds F/D for a dependency (load-use, or any
//                 dependency with FORWARDING=0), excluding cycles frozen by a D$ miss
//   flush_cycles  2 per taken redirect (the two wrong-path instructions), redirects seen while a
//                 D$ miss freezes the pipeline are counted once, when the freeze ends
//   imiss_cycles  cycles with imiss = 1 (can overlap other stalls)
//   dmiss_cycles  cycles with dmiss = 1
//
// Retirement uses a shadow valid bit per stage, shifted with the same hold and clear controls as
// the real pipeline registers, so bubbles are never counted as instructions.
// Checks: nothing itself. Does not model: loads from the MMIO window (unsupported).
module sys_monitor (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        mmio_we,
    input  logic [31:0] mmio_addr,
    input  logic [31:0] mmio_wdata,
    input  logic        imiss,
    input  logic        dmiss,
    input  logic        StallD,
    input  logic        StallE,
    input  logic        StallM,
    input  logic        StallW,
    input  logic        FlushD,
    input  logic        FlushE,
    input  logic        stallCond,
    input  logic        redirectE,
    output logic        halted,
    output logic [31:0] exit_code
);
    logic validD, validE, validM, validW;
    logic active;
    logic halt_pend;
    logic [31:0] cycles, instret, stall_loaduse, redirects, imiss_cycles, dmiss_cycles, total_cycles;

    wire retire = validW && !StallW;     // leaves Writeback this cycle
    wire [7:0] reg_sel = mmio_addr[7:0];

    task automatic print_perf;
        $display("PERF,%0d,%0d,%0d,%0d,%0d,%0d", cycles, instret, stall_loaduse, 2 * redirects,
                 imiss_cycles, dmiss_cycles);
    endtask

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            {validD, validE, validM, validW} <= '0;
            active <= 1'b1;
            {cycles, instret, stall_loaduse, redirects, imiss_cycles, dmiss_cycles, total_cycles} <= '0;
            halted <= 1'b0;
            halt_pend <= 1'b0;
            exit_code <= '0;
        end else begin
            validD <= StallD ? validD : (FlushD ? 1'b0 : !imiss);
            validE <= StallE ? validE : (FlushE ? 1'b0 : validD);
            validM <= StallM ? validM : validE;
            validW <= StallW ? validW : validM;

            total_cycles <= total_cycles + 1;
            if (active) begin
                cycles <= cycles + 1;
                if (retire) instret <= instret + 1;
                if (stallCond && !dmiss)  stall_loaduse <= stall_loaduse + 1;
                if (redirectE && !dmiss)  redirects <= redirects + 1;
                if (imiss)                imiss_cycles <= imiss_cycles + 1;
                if (dmiss)                dmiss_cycles <= dmiss_cycles + 1;
            end

            if (halt_pend && !halted) begin
                halted <= 1'b1;
                $display("HALT %0d", exit_code);
                print_perf();
            end

            if (mmio_we && !halt_pend && !halted) begin
                case (reg_sel)
                    8'h00: begin
                        halt_pend <= 1'b1;
                        exit_code <= mmio_wdata;
                    end
                    8'h04: begin
                        {cycles, instret, stall_loaduse, redirects, imiss_cycles, dmiss_cycles} <= '0;
                        active <= 1'b1;
                    end
                    8'h08: active <= 1'b0;
                    8'h0C: $display("PHASE %0d cycle=%0d", mmio_wdata, total_cycles);
                    8'h10: $display("CHR %0d", mmio_wdata[7:0]);
                    default: ;
                endcase
            end
        end
    end
endmodule
