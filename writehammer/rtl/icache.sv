module icache#(parameter NUM_LINES=64)(
    input logic clk,
    input logic rst_n,
    /* verilator lint_off UNUSEDSIGNAL */  // KI-001: addr[1:0] unused, fetch is word-aligned (docs/KNOWN_ISSUES.md)
    input logic [31:0] addr,
    /* verilator lint_on UNUSEDSIGNAL */
    output logic [31:0] rdata,
    output logic imiss,
    output logic mem_req,
    output logic [31:0] mem_addr,
    input logic [127:0] mem_rdata,
    input logic mem_done,
    output logic [31:0] refill_cnt
);

localparam  INDEX_BITS =  $clog2(NUM_LINES) ;
localparam TAG_BITS= 32-INDEX_BITS-4 ;

logic [NUM_LINES-1:0] valid;
logic [TAG_BITS-1:0] tags [NUM_LINES];
logic [127:0] data [NUM_LINES];

typedef enum logic {LOOKUP,REFILL  } state_t;
state_t state;

logic [INDEX_BITS-1:0] miss_index;

logic [TAG_BITS-1:0] miss_tag;

logic [INDEX_BITS-1:0] index;

logic [TAG_BITS-1:0] tag;
logic [1:0] wordsel;
logic hit;


always_comb begin
    index    = addr[INDEX_BITS+3:4];
    tag      = addr[31:INDEX_BITS+4];
    wordsel  = addr[3:2];
    hit      = valid[index] && (tags[index] == tag);

    imiss    = (state == LOOKUP) ? ~hit : 1'b1;
    rdata    = data[index][32*wordsel +: 32];
    mem_req  = (state == REFILL);
    mem_addr = {miss_tag, miss_index, 4'b0};
end

always_ff @(posedge clk or negedge rst_n) begin
    if(!rst_n) begin
        state<=LOOKUP;
        valid<='0;
        refill_cnt<=0;
    end
    else begin
        case(state)
        LOOKUP: begin
            if(~hit) begin
                miss_index<=index; 
                miss_tag<=tag;
                refill_cnt<=refill_cnt+1;
                state<=REFILL;
            end
        end
        REFILL: begin
            if(mem_done) begin
                valid[miss_index] <= 1'b1;
                state<=LOOKUP;
            end
        end
        endcase
    end
end

always_ff @(posedge clk) begin
    if(state==REFILL && mem_done) begin
        data[miss_index] <= mem_rdata;
        tags[miss_index] <=miss_tag;
    end
end


endmodule
