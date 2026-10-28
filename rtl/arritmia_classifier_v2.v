// ============================================================================
// arritmia_classifier_v2.v  —  Classificador de arritmia v2
// ----------------------------------------------------------------------------
// A cada novo pico (p_novo) classifica o pico anterior p0 com 11
// caracteristicas inteiras e causais (python/modelo_v2.py):
//   rr_prev, rr_next, rr_ratio, amp_r32              (como na v1)
//   sad_t, dpol, d_w                                 (motor de morfologia)
//   irr_np         = (media |dRR| dos ultimos 8) * 256 / base, com |dRR| so'
//                    entre batimentos NAO prematuros em relacao a' base
//   rr_next_ratio  = rr_next*256 / media RR
//   rr_base        = rr_prev*256 / base       base = media exponencial lenta
//   rr_next_base   = rr_next*256 / base       (1/128) dos RR nao prematuros
//
// Fluxo (FSM, um divisor serial compartilhado):
//   novo pico -> espera a morfologia de p0 -> 2 divisoes (rr_next) ->
//   arvore -> classe -> insere p0 nos historicos (RR, |dRR|, amplitude, base)
//   -> desloca (p1<=p0, p0<=p_novo) -> pre-calculo das razoes do novo p0
//   (7 divisoes) -> pre_ok (o motor de morfologia usa o rr_ratio de p0 para
//   decidir se atualiza o molde).
// ============================================================================
module arritmia_classifier_v2 #(
    parameter K = 8,         // janela da media de RR e de |dRR|
    parameter K_AMP = 32     // janela da media de amplitude
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        new_peak,
    input  wire [31:0] peak_index,      // indice do pico (convencao do testbench)
    input  wire [31:0] peak_value,      // MWI no pico

    // morfologia
    input  wire        morf_valid,
    input  wire [31:0] morf_k,
    input  wire [31:0] morf_dw,
    input  wire [31:0] morf_sad,
    input  wire [31:0] morf_dpol,

    // pre-calculo de p0 (para o motor de morfologia)
    output reg         pre_ok,
    output reg  [31:0] pre_k,
    output reg  [31:0] pre_rr_ratio,

    output reg  [2:0]  classe_out,
    output reg  [31:0] peak_classificado,
    output reg         classe_valid
);

    localparam AW = 18, ASW = AW + 5, LIM_PREM = 230, SH_BASE = 7;

    // ---------------- picos ----------------
    reg [31:0] p0, p1, pk;
    reg [AW-1:0] v0, vk;
    reg [1:0]  n_peaks;
    reg        pend;

    // ---------------- historicos ----------------
    reg [31:0] rr_hist [0:K-1];
    reg [31:0] rr_sum;
    reg [31:0] np_last;           // ultimo RR nao prematuro
    reg        np_ok;
    reg [3:0]  rr_cnt;
    reg [2:0]  rr_ptr;
    reg [31:0] irr_hist [0:K-1];
    reg [31:0] irr_sum;
    reg [3:0]  irr_cnt;
    reg [2:0]  irr_ptr;
    reg [AW-1:0]  amp_hist [0:K_AMP-1];
    reg [ASW-1:0] amp_sum;
    reg [5:0]  amp_cnt;
    reg [4:0]  amp_ptr;
    reg [31:0] base;
    reg        base_ok;

    // ---------------- razoes do p0 (pre-calculadas) ----------------
    reg [31:0] r_m, r_rr_ratio, r_amp_ratio, r_irr, r_rr_base, r_bref, r_tmp;
    // ---------------- do batimento em classificacao ----------------
    reg [31:0] c_rn, c_rnr, c_rnb, c_dw, c_sad, c_dpol;

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

    // ---------------- arvore ----------------
    wire [31:0] rpj = p0 - p1;
    wire [2:0]  arvore_classe;
    classificador_arvore_v2 i_arvore (
        .rr_prev(rpj), .rr_next(c_rn), .rr_ratio(r_rr_ratio), .amp_r32(r_amp_ratio),
        .sad_t(c_sad), .dpol(c_dpol), .d_w(c_dw), .irr_np(r_irr),
        .rr_next_ratio(c_rnr), .rr_base(r_rr_base), .rr_next_base(c_rnb),
        .classe(arvore_classe)
    );

    // base: atualizacao com o batimento classificado
    wire [31:0] base_dif  = (rpj >= base) ? (rpj - base) : (base - rpj);
    wire [31:0] base_nova = (rpj >= base) ? (base + (base_dif >> SH_BASE)) : (base - (base_dif >> SH_BASE));
    wire        nao_prem  = ({rpj, 8'b0} >= (r_m * LIM_PREM));
    wire [31:0] irr_novo  = (rpj >= np_last) ? (rpj - np_last) : (np_last - rpj);
    wire        np_base   = ({rpj, 8'b0} >= (r_bref * LIM_PREM));   // nao prematuro vs base

    localparam C_IDLE = 5'd0,  C_MORF = 5'd1,  C_N1 = 5'd2,  C_N1W = 5'd3,
               C_N2   = 5'd4,  C_N2W  = 5'd5,  C_CLS = 5'd6, C_DESL = 5'd7,
               P_M    = 5'd8,  P_MW   = 5'd9,  P_RR = 5'd10, P_RRW = 5'd11,
               P_MA   = 5'd12, P_MAW  = 5'd13, P_AMP = 5'd14, P_AMPW = 5'd15,
               P_I1   = 5'd16, P_I1W  = 5'd17, P_I2 = 5'd18, P_I2W = 5'd19,
               P_B    = 5'd20, P_BW   = 5'd21, P_FIM = 5'd22;
    reg [4:0] st;

    integer t;

    always @(posedge clk or posedge rst) begin
        if (rst) begin
            st <= C_IDLE; pend <= 1'b0; dv_start <= 1'b0; dv_num <= 0; dv_den <= 1;
            p0 <= 0; p1 <= 0; pk <= 0; v0 <= 0; vk <= 0; n_peaks <= 0;
            rr_sum <= 0; np_last <= 0; np_ok <= 1'b0; rr_cnt <= 0; rr_ptr <= 0;
            irr_sum <= 0; irr_cnt <= 0; irr_ptr <= 0;
            amp_sum <= 0; amp_cnt <= 0; amp_ptr <= 0;
            for (t = 0; t < K; t = t + 1) begin rr_hist[t] <= 0; irr_hist[t] <= 0; end
            for (t = 0; t < K_AMP; t = t + 1) amp_hist[t] <= 0;
            base <= 0; base_ok <= 1'b0;
            r_m <= 1; r_rr_ratio <= 0; r_amp_ratio <= 0; r_irr <= 0; r_rr_base <= 0; r_bref <= 1; r_tmp <= 0;
            c_rn <= 0; c_rnr <= 0; c_rnb <= 0; c_dw <= 0; c_sad <= 0; c_dpol <= 0;
            pre_ok <= 1'b0; pre_k <= 0; pre_rr_ratio <= 0;
            classe_out <= 0; peak_classificado <= 0; classe_valid <= 1'b0;
        end else begin
            classe_valid <= 1'b0;
            dv_start <= 1'b0;
            if (new_peak) begin
                pend <= 1'b1;
                pk <= peak_index;
                vk <= peak_value[AW-1:0];
            end
            case (st)
                C_IDLE: if (pend) begin
                    pend <= new_peak;          // (novo pico no mesmo ciclo: mantem)
                    st <= (n_peaks >= 2) ? C_MORF : C_DESL;
                end
                // morfologia do p0 disponivel?
                C_MORF: if (morf_valid && morf_k == p0 - 1) begin
                    c_dw <= morf_dw; c_sad <= morf_sad; c_dpol <= morf_dpol;
                    c_rn <= pk - p0;
                    st <= C_N1;
                end
                C_N1: begin
                    dv_num <= {8'b0, c_rn, 8'b0}; dv_den <= r_m; dv_start <= 1'b1; st <= C_N1W;
                end
                C_N1W: if (dv_done) begin c_rnr <= dv_q[31:0]; st <= C_N2; end
                C_N2: begin
                    dv_num <= {8'b0, c_rn, 8'b0}; dv_den <= r_bref; dv_start <= 1'b1; st <= C_N2W;
                end
                C_N2W: if (dv_done) begin c_rnb <= dv_q[31:0]; st <= C_CLS; end
                // classificacao + insercao de p0 nos historicos
                C_CLS: begin
                    classe_out <= arvore_classe;
                    peak_classificado <= p0;
                    classe_valid <= 1'b1;
                    if (np_base) begin
                        if (np_ok) begin
                            irr_sum <= irr_sum - irr_hist[irr_ptr] + irr_novo;
                            irr_hist[irr_ptr] <= irr_novo;
                            irr_ptr <= irr_ptr + 1'b1;
                            if (irr_cnt < K) irr_cnt <= irr_cnt + 1'b1;
                        end
                        np_last <= rpj;
                        np_ok <= 1'b1;
                    end
                    if (!base_ok) begin base <= rpj; base_ok <= 1'b1; end
                    else if (nao_prem) base <= base_nova;
                    rr_sum <= rr_sum - rr_hist[rr_ptr] + rpj;
                    rr_hist[rr_ptr] <= rpj;
                    rr_ptr <= rr_ptr + 1'b1;
                    if (rr_cnt < K) rr_cnt <= rr_cnt + 1'b1;
                    amp_sum <= amp_sum - amp_hist[amp_ptr] + v0;
                    amp_hist[amp_ptr] <= v0;
                    amp_ptr <= amp_ptr + 1'b1;
                    if (amp_cnt < K_AMP) amp_cnt <= amp_cnt + 1'b1;
                    st <= C_DESL;
                end
                // desloca os picos e comeca o pre-calculo do novo p0
                C_DESL: begin
                    p1 <= p0; p0 <= pk; v0 <= vk;
                    if (n_peaks < 3) n_peaks <= n_peaks + 1'b1;
                    pre_ok <= 1'b0;
                    st <= P_M;
                end
                // m = media dos RR (ou o proprio rr_prev)
                P_M: begin
                    if (rr_cnt == 0) begin
                        r_m <= (rpj == 0) ? 32'd1 : rpj; st <= P_RR;
                    end else begin
                        dv_num <= {16'b0, rr_sum}; dv_den <= {28'b0, rr_cnt}; dv_start <= 1'b1; st <= P_MW;
                    end
                end
                P_MW: if (dv_done) begin r_m <= (dv_q[31:0] == 0) ? 32'd1 : dv_q[31:0]; st <= P_RR; end
                P_RR: begin
                    dv_num <= {8'b0, rpj, 8'b0}; dv_den <= r_m; dv_start <= 1'b1; st <= P_RRW;
                end
                P_RRW: if (dv_done) begin r_rr_ratio <= dv_q[31:0]; st <= P_MA; end
                // media de amplitude (ou a propria amplitude)
                P_MA: begin
                    if (amp_cnt == 0) begin
                        r_tmp <= {{(32-AW){1'b0}}, v0}; st <= P_AMP;
                    end else begin
                        dv_num <= {{(48-ASW){1'b0}}, amp_sum}; dv_den <= {26'b0, amp_cnt}; dv_start <= 1'b1; st <= P_MAW;
                    end
                end
                P_MAW: if (dv_done) begin r_tmp <= dv_q[31:0]; st <= P_AMP; end
                P_AMP: begin
                    dv_num <= {{(40-AW){1'b0}}, v0, 8'b0}; dv_den <= (r_tmp == 0) ? 32'd1 : r_tmp;
                    dv_start <= 1'b1; st <= P_AMPW;
                end
                P_AMPW: if (dv_done) begin r_amp_ratio <= dv_q[31:0]; st <= P_B; end
                // irregularidade do ritmo de base: (soma|dRR| / n) * 256 / base
                P_I1: begin
                    if (irr_cnt == 0) begin
                        r_irr <= 0; st <= P_FIM;
                    end else begin
                        dv_num <= {16'b0, irr_sum}; dv_den <= {28'b0, irr_cnt}; dv_start <= 1'b1; st <= P_I1W;
                    end
                end
                P_I1W: if (dv_done) begin r_tmp <= dv_q[31:0]; st <= P_I2; end
                P_I2: begin
                    dv_num <= {8'b0, r_tmp, 8'b0}; dv_den <= r_bref; dv_start <= 1'b1; st <= P_I2W;
                end
                P_I2W: if (dv_done) begin r_irr <= dv_q[31:0]; st <= P_FIM; end
                // rr_base = rr_prev*256 / base (ou o proprio rr_prev)
                P_B: begin
                    r_bref <= base_ok ? ((base == 0) ? 32'd1 : base) : ((rpj == 0) ? 32'd1 : rpj);
                    dv_num <= {8'b0, rpj, 8'b0};
                    dv_den <= base_ok ? base : rpj;
                    dv_start <= 1'b1; st <= P_BW;
                end
                P_BW: if (dv_done) begin r_rr_base <= dv_q[31:0]; st <= P_I1; end
                P_FIM: begin
                    pre_ok <= 1'b1; pre_k <= p0 - 1; pre_rr_ratio <= r_rr_ratio;
                    st <= C_IDLE;
                end
                default: st <= C_IDLE;
            endcase
        end
    end

`ifndef SYNTHESIS
    always @(posedge clk)
        if (!rst && new_peak && (pend || st != C_IDLE))
            $display("ERRO arritmia_classifier_v2: novo pico com o classificador ocupado (t=%0t)", $time);
`endif

endmodule
