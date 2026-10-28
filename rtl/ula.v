// ULA - 32 bits
module ula (
    input  wire [31:0] a,
    input  wire [31:0] b,
    input  wire [2:0]  op_code,
    output reg  [31:0] result
);

    localparam OP_ADD    = 3'b000;
    localparam OP_SUB    = 3'b001;
    localparam OP_AND    = 3'b010;
    localparam OP_OR     = 3'b011;
    localparam OP_XOR    = 3'b100;
    localparam OP_PASS_A = 3'b101;
    localparam OP_PASS_B = 3'b110;

    always @(*) begin
        case (op_code)
            OP_ADD:    result = a + b;
            OP_SUB:    result = a - b;
            OP_AND:    result = a & b;
            OP_OR:     result = a | b;
            OP_XOR:    result = a ^ b;
            OP_PASS_A: result = a;
            OP_PASS_B: result = b;
            default:   result = 32'd0;
        endcase
    end

endmodule
