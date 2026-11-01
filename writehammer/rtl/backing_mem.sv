module backing_mem#(parameter DEPTH=256, parameter LATENCY=10, parameter INIT_FILE="")(
    input logic clk,
    input logic rst_n,
    input logic req,
    input logic we,
    /* verilator lint_off UNUSEDSIGNAL */  // KI-003: addr bits outside the array unused (wraps, as imem/dmem) (docs/KNOWN_ISSUES.md)
    input logic [31:0] addr,
    /* verilator lint_on UNUSEDSIGNAL */
    input logic [31:0] wdata,
    input logic [3:0] be,      // byte enables for a word write (lane k = bits [8k+7:8k])
    output logic [127:0] rdata,
    output logic done
);

typedef enum logic {IDLE, BUSY  } c_state;


c_state state;
c_state next_state;

logic [31:0] mem [0:DEPTH-1];
logic [$clog2(LATENCY)+1:0] cnt;

// Zero first, then overlay the file: words past the end of the file stay 0, not x.
initial begin
    for (int i = 0; i < DEPTH; i++) mem[i] = 32'b0;
    if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
end

always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        state<=IDLE;
    end
    else begin
        state<=next_state;
        case(state) 
            IDLE: begin
                if(req) cnt<=LATENCY-1;
            end
            BUSY: begin
                if(cnt!=0) cnt<=cnt-1;
                if(done && we)
                    for (int k = 0; k < 4; k++)
                        if (be[k]) mem[addr[$clog2(DEPTH)+1:2]][8*k +: 8] <= wdata[8*k +: 8];
            end
        endcase
    end
end

logic [$clog2(DEPTH)-1:0] b;   // word index of the block's first word
assign b={addr[$clog2(DEPTH)+1:4],2'b00};
assign rdata=done? {mem[b+3],mem[b+2],mem[b+1],mem[b]} : 0;           

always_comb begin
    next_state=IDLE;
    done=(state==BUSY && cnt==0);
    
    case(state) 
        IDLE: begin
            if(req) begin
                next_state=BUSY;
            end
            else begin
                next_state=IDLE;
            end
        end
        BUSY: begin
            if(cnt==0) begin
                next_state=IDLE;
            end
            else begin
                next_state=BUSY;
            end
        end
    endcase
end

endmodule
