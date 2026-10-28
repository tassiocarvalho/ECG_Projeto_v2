// ============================================================================
// fsm.v  —  COM HANDSHAKE valid/ready na fronteira de entrada
// ----------------------------------------------------------------------------
// MUDANCA vs versao com done_out/enable:
//   - Entrada por handshake: data_valid (produtor->FSM) / data_ready (FSM->produtor).
//     A FSM espera em READ_DATA/IDLE ate' data_valid=1; ao capturar a amostra
//     pulsa data_ready por 1 ciclo. Sem corrida: o produtor so' troca a amostra
//     depois de ver data_ready.
//   - O nucleo de processamento (FILTERING..CHECK_ALERT) e' IDENTICO ao anterior,
//     entao a relacao amostra<->alerta (e o total de picos) NAO muda.
//   - done_out continua existindo (pulso em FINISHED) p/ compatibilidade/relatorio.
//   - enable removido; o controle de fluxo agora e' o handshake. rst zera tudo.
// ============================================================================
module fsm (
    input wire clk,
    input wire rst,

    // Handshake de entrada
    input  wire data_valid,      // produtor: amostra disponivel em spi_data_in
    output reg  data_ready,      // FSM: amostra consumida, pode trocar

    input wire peak_detected_in,

    output reg read_en,
    output reg filter_en,
    output reg derivator_en,
    output reg integrator_en,
    output reg peak_detector_en,
    output reg [2:0] ula_op_code_out,
    output reg ram_we,
    output reg [7:0] ram_addr_out,
    output reg alert_out,
    output reg done_out
);

    localparam IDLE           = 4'd0;
    localparam READ_DATA      = 4'd1;
    localparam FILTERING      = 4'd2;
    localparam WAIT_FILTER    = 4'd3;
    localparam DERIVATING     = 4'd4;
    localparam WAIT_DERIV     = 4'd5;
    localparam INTEGRATING    = 4'd6;
    localparam WAIT_INTEG     = 4'd7;
    localparam PEAK_DETECTING = 4'd8;
    localparam STORE_RESULT   = 4'd9;
    localparam CHECK_ALERT    = 4'd10;
    localparam FINISHED       = 4'd11;

    reg [3:0] current_state, next_state;
    reg [7:0] ram_addr_counter;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            current_state    <= IDLE;
            ram_addr_counter <= 8'd0;
        end else begin
            current_state <= next_state;
            if (current_state == STORE_RESULT)
                ram_addr_counter <= ram_addr_counter + 8'd1;
        end
    end

    always @(*) begin
        next_state = current_state;
        case (current_state)
            IDLE:           if (data_valid) next_state = READ_DATA;
            READ_DATA:                      next_state = FILTERING;
            FILTERING:                      next_state = WAIT_FILTER;
            WAIT_FILTER:                    next_state = DERIVATING;
            DERIVATING:                     next_state = WAIT_DERIV;
            WAIT_DERIV:                     next_state = INTEGRATING;
            INTEGRATING:                    next_state = WAIT_INTEG;
            WAIT_INTEG:                     next_state = PEAK_DETECTING;
            PEAK_DETECTING:                 next_state = STORE_RESULT;
            STORE_RESULT:                   next_state = CHECK_ALERT;
            CHECK_ALERT:                    next_state = FINISHED;
            FINISHED: begin
                if (data_valid) next_state = READ_DATA;
                else            next_state = IDLE;
            end
            default: next_state = IDLE;
        endcase
    end

    always @(*) begin
        read_en          = 1'b0;
        filter_en        = 1'b0;
        derivator_en     = 1'b0;
        integrator_en    = 1'b0;
        peak_detector_en = 1'b0;
        ula_op_code_out  = 3'b000;
        ram_we           = 1'b0;
        ram_addr_out     = ram_addr_counter;
        alert_out        = 1'b0;
        done_out         = 1'b0;
        data_ready       = 1'b0;

        case (current_state)
            READ_DATA: begin
                read_en    = 1'b1;
                data_ready = 1'b1;   // pulso: amostra consumida neste ciclo
            end
            FILTERING:      filter_en        = 1'b1;
            DERIVATING:     derivator_en     = 1'b1;
            INTEGRATING:    integrator_en    = 1'b1;
            PEAK_DETECTING: peak_detector_en = 1'b1;
            STORE_RESULT: begin
                ram_we          = 1'b1;
                ula_op_code_out = 3'b101;
            end
            CHECK_ALERT: begin
                if (peak_detected_in) alert_out = 1'b1;
            end
            FINISHED: begin
                done_out = 1'b1;
                // NOTA: alert_out NAO e' levantado aqui. O pulso de alerta
                // ocorre exclusivamente em CHECK_ALERT (1 pulso por pico).
                // Levantar tambem aqui contava cada pico 2x (bug corrigido).
            end
            default: ;
        endcase
    end

endmodule
