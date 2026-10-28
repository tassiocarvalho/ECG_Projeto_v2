// ============================================================================
// peak_detector.v  —  Detector de QRS: refratario + limiar adaptativo + learning
// ----------------------------------------------------------------------------
// CORRECOES vs versao original (que superdetectava ~9x e disparava no inicio):
//   1. REFRATARIO real de 200 ms (REFRACTORY=72 @360Hz). Apos um pico, ignora
//      72 amostras — cobre todo o QRS, sem recontar o mesmo batimento.
//   2. LIMIAR adaptativo estavel (Pan-Tompkins), sem o "-1/ciclo" sem sentido:
//        threshold = noise_level + (signal_level - noise_level) >> 2
//      signal_level e noise_level via media exponencial (>>3 = 1/8).
//   3. LEARNING PHASE: nos primeiros LEARNING ciclos (2 s = 720 @360Hz) NAO
//      detecta; apenas acumula o maximo do MWI para inicializar signal_level
//      (e noise_level = signal_level/2). Sem isso, com niveis zerados, o limiar
//      comeca em 0 e dispara em todo ruido ate' estabilizar.
//
// 32 bits, sem pipeline, habilitado por en (FSM). Espelhado em pan_tompkins_hw.py.
// ============================================================================
module peak_detector #(
    parameter REFRACTORY = 72,     // 200 ms @ 360 Hz
    parameter LEARNING   = 720,    // 2 s   @ 360 Hz
    parameter SETTLE     = 64      // amostras iniciais fora do learn_max
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        en,
    input  wire [31:0] data_in,
    output reg         peak_detected,
    output reg  [31:0] peak_value
);

    reg [31:0] prev_data;
    reg [31:0] signal_level;
    reg [31:0] noise_level;
    reg [31:0] threshold;
    reg [7:0]  refr_cnt;
    reg [31:0] learn_cnt;
    reg [31:0] learn_max;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            prev_data     <= 32'd0;
            signal_level  <= 32'd0;
            noise_level   <= 32'd0;
            threshold     <= 32'd0;
            refr_cnt      <= 8'd0;
            learn_cnt     <= 32'd0;
            learn_max     <= 32'd0;
            peak_detected <= 1'b0;
            peak_value    <= 32'd0;
        end else if (en) begin
            peak_detected <= 1'b0;

            if (learn_cnt < LEARNING) begin
                // ---- fase de aprendizado: so' rastreia o maximo, nao detecta ----
                // o transitorio de partida (registradores do filtro em zero
                // x primeira amostra) nao entra no maximo aprendido
                if (learn_cnt >= SETTLE && data_in > learn_max)
                    learn_max <= data_in;
                learn_cnt <= learn_cnt + 1'b1;
                if (learn_cnt == LEARNING - 1) begin
                    // inicializa niveis a partir do maximo observado
                    signal_level <= learn_max;
                    noise_level  <= learn_max >> 2;          // ruido ~ 1/4 do pico
                    threshold    <= (learn_max >> 2)
                                  + ((learn_max - (learn_max>>2)) >> 2);
                end
            end else if (refr_cnt > 0) begin
                refr_cnt <= refr_cnt - 1'b1;
            end else begin
                if (prev_data > data_in && prev_data > threshold) begin
                    // ---- pico aceito ----
                    peak_detected <= 1'b1;
                    peak_value    <= prev_data;
                    signal_level  <= signal_level - (signal_level >> 3)
                                                  + (prev_data   >> 3);
                    threshold     <= noise_level
                                   + (((signal_level - (signal_level>>3)
                                       + (prev_data>>3)) - noise_level) >> 2);
                    refr_cnt      <= REFRACTORY[7:0];
                end else if (data_in <= threshold) begin
                    // ---- amostra de ruido ----
                    noise_level   <= noise_level - (noise_level >> 3)
                                                 + (data_in     >> 3);
                    threshold     <= (noise_level - (noise_level>>3)
                                      + (data_in>>3))
                                   + ((signal_level - (noise_level - (noise_level>>3)
                                      + (data_in>>3))) >> 2);
                end
            end

            prev_data <= data_in;
        end
    end

endmodule
