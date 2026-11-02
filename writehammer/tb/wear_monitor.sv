`timescale 1ns/1ps
// wear_monitor: simulation-only D$ data-array write observer.
// WINDOW_CYCLES and NLINES define the CSV geometry. Count one event for each asserted
// aw_valid pulse; aw_kind distinguishes a store/merge (0) from a fill (1).
// Outputs in the run directory: wear_windows.csv, wear_lines.csv, wear_phases.csv,
// and dc_trace.csv. The trace records completed non-MMIO D$ requests.
// Assumptions: reset precedes traffic; the testbench calls finish_run once after HALT.
// Does not check architectural results or model cache behavior.
module wear_monitor #(
    parameter int NLINES = 128,
    parameter int WINDOW_CYCLES = 10000
) (
    input logic clk, rst_n,
    input logic aw_valid,
    input logic [31:0] aw_line,
    input logic aw_kind,
    input logic tr_valid, tr_we,
    input logic [31:0] tr_addr,
    input logic [2:0] tr_size,
    input logic tr_bypass,
    input logic mmio_we,
    input logic [31:0] mmio_addr, mmio_wdata
);
    integer total [0:NLINES-1];
    integer bucket [0:NLINES-1];
    integer fwin, fline, fphase, ftrace;
    integer cycle_no = 0;
    integer window_no = 0;
    integer fill_events = 0;
    integer store_events = 0;
    bit finished = 0;

    initial begin
        fwin = $fopen("wear_windows.csv", "w");
        fline = $fopen("wear_lines.csv", "w");
        fphase = $fopen("wear_phases.csv", "w");
        ftrace = $fopen("dc_trace.csv", "w");
        if (!fwin || !fline || !fphase || !ftrace) $fatal(1, "wear monitor: CSV open failed");
        $fdisplay(fwin, "window,line,count");
        $fdisplay(fline, "line,count");
        $fdisplay(fphase, "cycle,phase");
        $fdisplay(ftrace, "cycle,type,address,size,bypass");
        for (int i = 0; i < NLINES; i++) begin
            total[i] = 0;
            bucket[i] = 0;
        end
    end

    task automatic flush_window;
        for (int i = 0; i < NLINES; i++) begin
            $fdisplay(fwin, "%0d,%0d,%0d", window_no, i, bucket[i]);
            bucket[i] = 0;
        end
        window_no = window_no + 1;
    endtask

    always @(posedge clk) begin
        if (!rst_n) begin
            cycle_no = 0;
        end else if (!finished) begin
            if (cycle_no > 0 && cycle_no % WINDOW_CYCLES == 0) flush_window();
            if (aw_valid) begin
                if (aw_line >= NLINES) $fatal(1, "wear monitor: line out of range %0d", aw_line);
                total[aw_line] = total[aw_line] + 1;
                bucket[aw_line] = bucket[aw_line] + 1;
                if (aw_kind) fill_events = fill_events + 1;
                else store_events = store_events + 1;
            end
            if (tr_valid)
                $fdisplay(ftrace, "%0d,%s,%0d,%0d,%0d", cycle_no,
                          tr_we ? "S" : "L", tr_addr, tr_size, tr_bypass);
            if (mmio_we && mmio_addr[7:0] == 8'h0c)
                $fdisplay(fphase, "%0d,%0d", cycle_no, mmio_wdata);
            cycle_no = cycle_no + 1;
        end
    end

    task automatic finish_run;
        if (!finished) begin
            finished = 1;
            flush_window();
            for (int i = 0; i < NLINES; i++)
                $fdisplay(fline, "%0d,%0d", i, total[i]);
            $fclose(fwin);
            $fclose(fline);
            $fclose(fphase);
            $fclose(ftrace);
            $display("WEAR cycles=%0d fills=%0d stores=%0d", cycle_no, fill_events, store_events);
        end
    endtask
endmodule
