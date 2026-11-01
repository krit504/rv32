module dcache#(parameter NUM_LINES=64)(
    input logic clk,
    input logic rst_n,
    /* verilator lint_off UNUSEDSIGNAL */  // KI-002: addr[1:0] unused, word accesses only until T2.4 (docs/KNOWN_ISSUES.md)
    input logic [31:0] addr,
    /* verilator lint_on UNUSEDSIGNAL */
    input logic [31:0] wdata,
    input logic [3:0] be,      // byte enables of the store in Memory (lane-aligned with wdata)
    input logic we,
    input logic re,
    output logic [31:0] rdata,
    output logic dmiss,
    output logic mem_req,
    output logic mem_we,
    output logic [31:0] mem_addr,
    output logic [31:0] mem_wdata,
    output logic [3:0] mem_be,
    input logic [127:0] mem_rdata,
    input logic mem_done,
    output logic [31:0] write_cnt,
    output logic [31:0] refill_cnt
);

localparam  INDEX_BITS =  $clog2(NUM_LINES) ;
localparam TAG_BITS= 32-INDEX_BITS-4 ;


logic [NUM_LINES-1:0] valid;
logic [TAG_BITS-1:0] tags [NUM_LINES];
logic [127:0] data [NUM_LINES];


typedef enum logic [1:0] {LOOKUP,REFILL, WRITE  } state_t;
state_t state;


logic [INDEX_BITS-1:0] index;
logic [TAG_BITS-1:0] tag;
logic [1:0] wordsel;
logic hit;


always_comb begin
    index    = addr[INDEX_BITS+3:4];
    tag      = addr[31:INDEX_BITS+4];
    wordsel  = addr[3:2];
    hit      = valid[index] && (tags[index] == tag);

    dmiss    = (state == LOOKUP) ? ((re & ~hit) | we) :
               (state == REFILL) ? 1'b1 :
                                   ~mem_done;                // WRITE

    rdata     = data[index][32*wordsel +: 32];
    mem_req   = (state != LOOKUP);
    mem_we    = (state == WRITE);
    mem_addr  = (state == WRITE) ? {addr[31:2], 2'b00} : {addr[31:4], 4'b0};
    mem_wdata = wdata;
    mem_be    = be;
end

always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        state<=LOOKUP;
        valid<='0;
        refill_cnt<=0;
        write_cnt<=0;
    end
    else begin
        case(state)
        LOOKUP: begin
            if(~hit & re) begin
                refill_cnt<=refill_cnt+1;
                state<=REFILL;
            end
            else if(we) begin
                write_cnt<=write_cnt+1;
                state<=WRITE;
            end
        end
        REFILL: begin
            if(mem_done) begin
                valid[index] <= 1'b1;
                state<=LOOKUP;
            end
        end
        WRITE: begin
            if(mem_done) begin
                state<=LOOKUP;
            end
        end
        default: state<=LOOKUP;   // 2'b11 is unused
        endcase
    end
end

always_ff @(posedge clk) begin
    if(state==REFILL && mem_done) begin
        data[index] <= mem_rdata;
        tags[index] <=tag;
    end
    else if(state==LOOKUP && we && hit) begin
        for (int k = 0; k < 4; k++)
            if (be[k]) data[index][32*wordsel + 8*k +: 8] <= wdata[8*k +: 8];
    end
end


endmodule
