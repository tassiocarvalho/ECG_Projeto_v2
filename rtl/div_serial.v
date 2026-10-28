// ============================================================================
// div_serial.v  —  Divisor inteiro sem sinal, restaurador, 1 bit por ciclo
// ----------------------------------------------------------------------------
// start (pulso) com dividendo/divisor estaveis -> 'done' pulsa DW ciclos depois
// com quociente = floor(dividendo / divisor). Divisor 0 e' tratado como 1.
// Bit-exato com a divisao inteira '//' do Python para operandos >= 0.
// ============================================================================
module div_serial #(
    parameter DW = 48,      // largura do dividendo (e do quociente)
    parameter SW = 32       // largura do divisor
) (
    input  wire          clk,
    input  wire          rst,
    input  wire          start,
    input  wire [DW-1:0] dividendo,
    input  wire [SW-1:0] divisor,
    output reg  [DW-1:0] quociente,
    output reg           done,
    output wire          busy
);

    reg [DW-1:0] q;          // dividendo -> quociente (deslocamento)
    reg [SW:0]   r;          // resto parcial
    reg [SW-1:0] d;
    reg [6:0]    n;          // bits restantes
    reg          ativo;

    wire [SW:0]  r_sh  = {r[SW-1:0], q[DW-1]};
    wire         cabe  = (r_sh >= {1'b0, d});

    assign busy = ativo;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            q <= 0; r <= 0; d <= 0; n <= 0; ativo <= 1'b0;
            quociente <= 0; done <= 1'b0;
        end else begin
            done <= 1'b0;
            if (start) begin
                q <= dividendo;
                r <= 0;
                d <= (divisor == 0) ? {{(SW-1){1'b0}}, 1'b1} : divisor;
                n <= DW;
                ativo <= 1'b1;
            end else if (ativo) begin
                r <= cabe ? (r_sh - {1'b0, d}) : r_sh;
                q <= {q[DW-2:0], cabe};
                n <= n - 1'b1;
                if (n == 7'd1) begin
                    ativo <= 1'b0;
                    done  <= 1'b1;
                    quociente <= {q[DW-2:0], cabe};
                end
            end
        end
    end

endmodule
