// ============================================================================
// spi_slave.v  —  Modulo de comunicacao SPI (escravo) para entrada de amostras
// ----------------------------------------------------------------------------
// PAPEL NO PROJETO: e' o "modulo de comunicacao por protocolo digital" exigido
// pela especificacao. Recebe cada amostra de ECG (16 bits) de forma SERIAL,
// pelo protocolo SPI, e a entrega de forma PARALELA ao sistema principal.
//
// IMPORTANTE (equivalencia): o SPI e' apenas TRANSPORTE. Ele nao altera o valor
// da amostra; so' muda a forma como ela chega (serial -> paralela). A palavra
// entregue (data_out) e' identica a' que hoje entra direto. Por isso o pipeline
// recebe exatamente as mesmas amostras, e a equivalencia com o modelo de
// referencia se mantem.
//
// PROTOCOLO SPI (modo 0, padrao):
//   - sclk : clock serial vindo do mestre
//   - cs_n : chip select, ativo em nivel BAIXO (0 = transacao em andamento)
//   - mosi : master-out slave-in (o bit de dado vindo do mestre)
//   - amostra de 16 bits, enviada MSB primeiro (bit 15 ... bit 0)
//
// INTERFACE COM O SISTEMA (lado paralelo):
//   - data_out  : a amostra de 16 bits montada (em palavra de 32 bits)
//   - data_valid: pulso de 1 ciclo de clk quando uma amostra completa chegou
//
// O modulo sincroniza os sinais SPI (que vem de outro dominio de clock) com o
// clock do sistema (clk) usando registradores de sincronizacao, e detecta a
// borda de subida do sclk para amostrar o mosi.
// ============================================================================
module spi_slave (
    input  wire        clk,       // clock do sistema
    input  wire        rst,       // reset assincrono, ativo alto

    // ---- lado SPI (serial) ----
    input  wire        sclk,      // clock serial do mestre
    input  wire        cs_n,      // chip select, ativo baixo
    input  wire        mosi,      // dado serial (master -> slave)

    // ---- lado sistema (paralelo) ----
    output reg  [31:0] data_out,    // amostra de 16 bits (em palavra de 32)
    output reg         data_valid   // pulso: amostra completa disponivel
);

    localparam N_BITS = 16;   // largura da amostra

    // ---- sincronizacao dos sinais SPI para o dominio de clk ----
    // (dois flip-flops em serie para evitar metaestabilidade)
    reg [1:0] sclk_sync;
    reg [1:0] cs_sync;
    reg [1:0] mosi_sync;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            sclk_sync <= 2'b00;
            cs_sync   <= 2'b11;   // cs_n inativo (alto) no reset
            mosi_sync <= 2'b00;
        end else begin
            sclk_sync <= {sclk_sync[0], sclk};
            cs_sync   <= {cs_sync[0],   cs_n};
            mosi_sync <= {mosi_sync[0], mosi};
        end
    end

    // borda de subida do sclk (detectada no dominio de clk)
    wire sclk_rising = (sclk_sync == 2'b01);
    wire cs_ativo    = (cs_sync[1] == 1'b0);   // cs_n baixo = transacao ativa
    wire mosi_bit    =  mosi_sync[1];

    // ---- recepcao serial ----
    reg [N_BITS-1:0] shift_reg;            // monta a palavra bit a bit
    reg [4:0]        bit_count;            // conta bits recebidos (0..16)

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            shift_reg  <= {N_BITS{1'b0}};
            bit_count  <= 5'd0;
            data_out   <= 32'd0;
            data_valid <= 1'b0;
        end else begin
            data_valid <= 1'b0;   // pulso de 1 ciclo por padrao

            if (!cs_ativo) begin
                // fora de transacao: zera o contador (espera novo cs_n baixo)
                bit_count <= 5'd0;
            end else if (sclk_rising) begin
                // a cada borda de subida do sclk, captura 1 bit (MSB primeiro)
                shift_reg <= {shift_reg[N_BITS-2:0], mosi_bit};
                bit_count <= bit_count + 5'd1;

                // quando recebeu os 16 bits, entrega a palavra ao sistema
                if (bit_count == N_BITS-1) begin
                    data_out   <= {16'd0, shift_reg[N_BITS-2:0], mosi_bit};
                    data_valid <= 1'b1;     // pulso: amostra pronta
                    bit_count  <= 5'd0;     // pronto p/ a proxima amostra
                end
            end
        end
    end

endmodule