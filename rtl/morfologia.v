// ============================================================================
// morfologia.v  —  Motor de morfologia do batimento (v2)
// ----------------------------------------------------------------------------
// Para cada pico detectado (amostra k), le a derivada com sinal guardada na
// RAM (endereco = indice da amostra mod 256) e calcula, de forma sequencial:
//   d_w   : largura do QRS (amostras contiguas com |d| > max/8)
//   sad_t : distancia ao molde do paciente = sum|S-T|*256 / sum|T|
//   dpol  : |polaridade(S) - polaridade(T)|
// e atualiza o molde T (64 amostras) se o batimento nao for prematuro.
// Semantica identica a classe Morfologia de python/modelo_v2.py.
//
// Fluxo por pico (FSM):
//   espera amostra k+40 gravada -> varre [k-80, k+39] buscando max|d| (r)
//   -> espera amostra r+40 -> largura para a esquerda e para a direita
//   -> espera o rr_ratio do pico (pre-calculo do classificador)
//   -> segmento S = d[r-24 .. r+39] contra o molde (64 ciclos)
//   -> 3 divisoes seriais (pol, pol do molde, sad_t) -> resultado valido.
// Fila de 2 picos pendentes; o resultado fica registrado (morf_k identifica
// o pico) ate' o proximo ser calculado.
// ============================================================================
module morfologia (
    input  wire        clk,
    input  wire        rst,

    // pedido: pico detectado na amostra pico_k (indice desde 0)
    input  wire        pico_novo,
    input  wire [31:0] pico_k,
    input  wire [31:0] n_grav,          // amostras ja' gravadas na RAM

    // leitura da RAM (2a porta, assincrona)
    output reg  [7:0]  rd_addr,
    input  wire [31:0] rd_data,

    // rr_ratio do pico (pre-calculo do classificador)
    input  wire        pre_ok,
    input  wire [31:0] pre_k,
    input  wire [31:0] pre_rr_ratio,

    // resultado
    output reg         morf_valid,
    output reg  [31:0] morf_k,
    output reg  [31:0] morf_dw,
    output reg  [31:0] morf_sad,
    output reg  [31:0] morf_dpol
);

    localparam PRE = 80, POS = 40, SA = 24, NS = 64, LIM_PREM = 230;

    // ---------------- fila de picos pendentes (2 entradas) ----------------
    reg [31:0] fila0, fila1;
    reg [1:0]  nfila;
    reg        pega;                       // FSM retira a cabeca da fila

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            fila0 <= 0; fila1 <= 0; nfila <= 0;
        end else begin
            case ({pico_novo, pega})
                2'b10: begin
                    if (nfila == 0) fila0 <= pico_k; else fila1 <= pico_k;
                    if (nfila != 2) nfila <= nfila + 1'b1;
                end
                2'b01: begin fila0 <= fila1; nfila <= nfila - 1'b1; end
                2'b11: begin
                    if (nfila == 1) fila0 <= pico_k;
                    else begin fila0 <= fila1; fila1 <= pico_k; end
                end
                default: ;
            endcase
        end
    end

    // ---------------- molde ----------------
    reg signed [19:0] T [0:NS-1];
    reg [2:0]  nT;                         // moldes acumulados (satura em 4)

    // ---------------- divisor ----------------
    reg         dv_start;
    reg  [47:0] dv_num;
    reg  [31:0] dv_den;
    wire [47:0] dv_q;
    wire        dv_done, dv_busy;

    div_serial #(.DW(48), .SW(32)) i_div (
        .clk(clk), .rst(rst), .start(dv_start),
        .dividendo(dv_num), .divisor(dv_den),
        .quociente(dv_q), .done(dv_done), .busy(dv_busy)
    );

    // ---------------- estado do calculo ----------------
    localparam S_IDLE = 4'd0, S_ESP1 = 4'd1, S_SCAN = 4'd2, S_ESP2 = 4'd3,
               S_LE   = 4'd4, S_LD   = 4'd5, S_PRE  = 4'd6, S_SEG  = 4'd7,
               S_D1   = 4'd8, S_D1W  = 4'd9, S_D2 = 4'd10, S_D2W = 4'd11,
               S_D3   = 4'd12, S_D3W = 4'd13, S_FIM = 4'd14;

    reg [3:0]  st;
    reg signed [33:0] k, j, r, a, b;       // indices de amostra (podem ser < 0)
    reg [31:0] best;                       // max |d|
    reg [31:0] lim;
    reg        prem;
    reg [6:0]  js;                         // indice no segmento 0..63
    reg signed [31:0] smax, smin, tmax, tmin;
    reg [31:0] sad, tsum;
    reg        neg_pol, neg_polt;
    reg [31:0] pol_mag, polt_mag;

    // amostra lida (indice negativo = 0: antes do inicio do registro)
    wire signed [31:0] dval = (j < 0) ? 32'sd0 : $signed(rd_data);
    wire [31:0] dabs = dval[31] ? (~dval + 1'b1) : dval;

    // deslocamento do molde
    wire [1:0] sh = (nT == 3'd1) ? 2'd1 : ((nT <= 3'd3) ? 2'd2 : 2'd3);
    wire signed [19:0] tcur = T[js[5:0]];
    wire signed [31:0] tcur32 = tcur;
    wire signed [32:0] dif = dval - tcur32;
    wire [32:0] dif_abs = dif[32] ? (~dif + 1'b1) : dif;
    wire signed [32:0] dif_sh = dif >>> sh;
    wire [31:0] tabs = tcur32[31] ? (~tcur32 + 1'b1) : tcur32;

    // polaridade: num = smax - (-min) = smax + min ; den = smax + (-min)
    wire signed [33:0] p_num  = smax + smin;      // smin guarda o MINIMO (com sinal)
    wire signed [33:0] p_den  = smax - smin;
    wire signed [33:0] pt_num = tmax + tmin;
    wire signed [33:0] pt_den = tmax - tmin;
    wire [33:0] p_num_abs  = p_num[33]  ? (~p_num + 1'b1)  : p_num;
    wire [33:0] pt_num_abs = pt_num[33] ? (~pt_num + 1'b1) : pt_num;

    // polaridades com sinal (resultado das divisoes)
    wire signed [33:0] pol_s  = neg_pol  ? -$signed({2'b0, pol_mag})  : $signed({2'b0, pol_mag});
    wire signed [33:0] polt_s = neg_polt ? -$signed({2'b0, polt_mag}) : $signed({2'b0, polt_mag});
    wire signed [33:0] dpol_s = pol_s - polt_s;

    always @(*) begin
        rd_addr = j[7:0];
    end

`ifndef SYNTHESIS
    // Seguranca do buffer circular: toda leitura usada (varredura, largura,
    // segmento) deve pegar uma amostra ja' gravada (j < n_grav) e ainda nao
    // sobrescrita (n_grav - j <= 256). Registra a maior idade observada.
    integer idade_max = 0;
    wire le_ram = (st == S_SCAN) || (st == S_LE) || (st == S_LD) || (st == S_SEG);
    wire signed [33:0] idade = $signed({2'b0, n_grav}) - j;
    always @(posedge clk) if (!rst && le_ram && j >= 0) begin
        if (idade < 1 || idade > 256)
            $display("ERRO morfologia: leitura da amostra %0d com %0d gravadas", j, n_grav);
        if (idade > idade_max) begin
            idade_max = idade;
            $display("IDADE_MAX %0d", idade_max);
        end
    end
`endif

    integer t;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            st <= S_IDLE; pega <= 1'b0; dv_start <= 1'b0;
            k <= 0; j <= 0; r <= 0; a <= 0; b <= 0;
            best <= 0; lim <= 0; prem <= 1'b0; js <= 0;
            smax <= 0; smin <= 0; tmax <= 0; tmin <= 0; sad <= 0; tsum <= 0;
            neg_pol <= 1'b0; neg_polt <= 1'b0; pol_mag <= 0; polt_mag <= 0;
            dv_num <= 0; dv_den <= 0;
            nT <= 0;
            for (t = 0; t < NS; t = t + 1) T[t] <= 0;
            morf_valid <= 1'b0; morf_k <= 0; morf_dw <= 0; morf_sad <= 0; morf_dpol <= 0;
        end else begin
            pega <= 1'b0;
            dv_start <= 1'b0;
            case (st)
                S_IDLE: if (nfila != 0 && !pega) begin
                    k <= $signed({2'b0, fila0});
                    pega <= 1'b1;
                    st <= S_ESP1;
                end
                // amostras ate' k+39 gravadas
                S_ESP1: if ($signed({2'b0, n_grav}) >= k + POS) begin
                    j <= k - PRE; best <= 0; r <= k - PRE;
                    st <= S_SCAN;
                end
                // varredura: 1o indice de max |d| em [k-80, k+39]
                S_SCAN: begin
                    if (dabs > best) begin best <= dabs; r <= j; end
                    if (j == k + POS - 1) st <= S_ESP2;
                    else j <= j + 1;
                end
                // segmento precisa ate' r+39
                S_ESP2: if ($signed({2'b0, n_grav}) >= r + NS - SA) begin
                    lim <= best >> 3;
                    a <= r; j <= r - 1;
                    st <= S_LE;
                end
                // largura para a esquerda: enquanto a > lo e |d(a-1)| > lim
                S_LE: begin
                    if (a > k - PRE && dabs > lim) begin
                        a <= a - 1; j <= j - 1;
                    end else begin
                        b <= r; j <= r + 1;
                        st <= S_LD;
                    end
                end
                // largura para a direita: enquanto b < hi-1 e |d(b+1)| > lim
                S_LD: begin
                    if (b < k + POS - 1 && dabs > lim) begin
                        b <= b + 1; j <= j + 1;
                    end else begin
                        st <= S_PRE;
                    end
                end
                // espera o rr_ratio deste pico
                S_PRE: if (pre_ok && $signed({2'b0, pre_k}) == k) begin
                    prem <= (pre_rr_ratio < LIM_PREM);
                    js <= 0; j <= r - SA;
                    sad <= 0; tsum <= 0;
                    st <= S_SEG;
                end
                // segmento S contra o molde (e atualizacao do molde)
                S_SEG: begin
                    if (js == 0) begin
                        smax <= dval; smin <= dval; tmax <= tcur32; tmin <= tcur32;
                    end else begin
                        if (dval > smax) smax <= dval;
                        if (dval < smin) smin <= dval;
                        if (tcur32 > tmax) tmax <= tcur32;
                        if (tcur32 < tmin) tmin <= tcur32;
                    end
                    sad  <= sad + dif_abs[31:0];
                    tsum <= tsum + tabs;
                    if (nT == 0)
                        T[js[5:0]] <= dval[19:0];
                    else if (!prem)
                        T[js[5:0]] <= tcur + dif_sh[19:0];
                    if (js == NS - 1) st <= S_D1;
                    else begin js <= js + 1; j <= j + 1; end
                end
                // pol = sinal(num) * |num|*256 / max(den,1)
                S_D1: begin
                    neg_pol <= p_num[33];
                    dv_num <= {6'b0, p_num_abs, 8'b0};
                    dv_den <= (p_den == 0) ? 32'd1 : p_den[31:0];
                    dv_start <= 1'b1;
                    st <= S_D1W;
                end
                S_D1W: if (dv_done) begin
                    pol_mag <= dv_q[31:0];
                    st <= (nT == 0) ? S_FIM : S_D2;
                end
                S_D2: begin
                    neg_polt <= pt_num[33];
                    dv_num <= {6'b0, pt_num_abs, 8'b0};
                    dv_den <= (pt_den == 0) ? 32'd1 : pt_den[31:0];
                    dv_start <= 1'b1;
                    st <= S_D2W;
                end
                S_D2W: if (dv_done) begin
                    polt_mag <= dv_q[31:0];
                    st <= S_D3;
                end
                S_D3: begin
                    dv_num <= {8'b0, sad, 8'b0};
                    dv_den <= (tsum == 0) ? 32'd1 : tsum;
                    dv_start <= 1'b1;
                    st <= S_D3W;
                end
                S_D3W: if (dv_done) begin
                    morf_sad <= dv_q[31:0];
                    st <= S_FIM;
                end
                S_FIM: begin
                    morf_valid <= 1'b1;
                    morf_k <= k[31:0];
                    morf_dw <= b - a + 1;
                    if (nT == 0) begin
                        morf_sad <= 0;
                        morf_dpol <= 0;
                        nT <= 3'd1;
                    end else begin
                        morf_dpol <= dpol_s[33] ? (~dpol_s[31:0] + 1'b1) : dpol_s[31:0];
                        if (!prem && nT < 3'd4) nT <= nT + 1'b1;
                    end
                    st <= S_IDLE;
                end
                default: st <= S_IDLE;
            endcase
        end
    end

endmodule
