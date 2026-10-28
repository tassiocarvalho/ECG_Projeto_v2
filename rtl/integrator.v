// Integrador de janela móvel, 32 bits, sem pipeline
// WINDOW_SIZE configurável. Opera apenas quando integrator_en=1
module integrator #(
    parameter WINDOW_SIZE = 30
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        en,
    input  wire [31:0] data_in,
    output reg  [31:0] data_out
);

    reg [31:0] window [0:WINDOW_SIZE-1];
    reg [63:0] window_sum; // 64 bits para suportar soma de 30 valores de 32 bits
    reg [$clog2(WINDOW_SIZE)-1:0] ptr;
    integer i;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            window_sum <= 64'd0;
            ptr        <= 0;
            data_out   <= 32'd0;
            for (i = 0; i < WINDOW_SIZE; i = i + 1)
                window[i] <= 32'd0;
        end else if (en) begin
            window_sum        <= window_sum - window[ptr] + data_in;
            window[ptr]       <= data_in;
            ptr               <= (ptr == WINDOW_SIZE - 1) ? 0 : ptr + 1;
            // Normaliza: divide por WINDOW_SIZE usando shift (aprox. /32 para W=30)
            data_out          <= (window_sum - window[ptr] + data_in) >> 5;
        end
        // Se en=0: mantém valor anterior
    end

endmodule
