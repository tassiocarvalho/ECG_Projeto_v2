// classificador_arvore_v2.v  (GERADO por python/treinar_v2.py)
// DS1 inteiro, depth=7, pesos N=1 SVEB=1.0 VEB=1.5, 62 comparadores
// Arvore de decisao inteira — identica a python/classificador_arvore_v2.py
// Combinacional: comparadores com constantes + multiplexadores.
module classificador_arvore_v2 (
    input  wire [31:0] rr_prev,
    input  wire [31:0] rr_next,
    input  wire [31:0] rr_ratio,
    input  wire [31:0] amp_r32,
    input  wire [31:0] sad_t,
    input  wire [31:0] dpol,
    input  wire [31:0] d_w,
    input  wire [31:0] irr_np,
    input  wire [31:0] rr_next_ratio,
    input  wire [31:0] rr_base,
    input  wire [31:0] rr_next_base,
    output reg  [2:0]  classe
);

    always @(*) begin
        if (sad_t <= 169) begin
            if (rr_base <= 185) begin
                if (irr_np <= 35) begin
                    if (rr_prev <= 200) begin
                        if (sad_t <= 103) begin
                            if (rr_next <= 154) begin
                                classe = 3'd1;
                            end else begin
                                if (rr_next_base <= 171) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd1;
                                end
                            end
                        end else begin
                            if (rr_next <= 350) begin
                                if (rr_prev <= 179) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd2;
                                end
                            end else begin
                                classe = 3'd2;
                            end
                        end
                    end else begin
                        if (rr_ratio <= 213) begin
                            classe = 3'd1;
                        end else begin
                            if (rr_next <= 167) begin
                                classe = 3'd3;
                            end else begin
                                if (rr_next_base <= 230) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd3;
                                end
                            end
                        end
                    end
                end else begin
                    if (amp_r32 <= 347) begin
                        if (sad_t <= 127) begin
                            if (rr_ratio <= 114) begin
                                if (rr_next <= 314) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd1;
                                end
                            end else begin
                                classe = 3'd0;
                            end
                        end else begin
                            if (rr_next <= 288) begin
                                classe = 3'd0;
                            end else begin
                                if (rr_next <= 406) begin
                                    classe = 3'd2;
                                end else begin
                                    classe = 3'd3;
                                end
                            end
                        end
                    end else begin
                        if (rr_prev <= 186) begin
                            classe = 3'd0;
                        end else begin
                            classe = 3'd3;
                        end
                    end
                end
            end else begin
                if (rr_ratio <= 219) begin
                    if (rr_next_ratio <= 270) begin
                        classe = 3'd0;
                    end else begin
                        if (irr_np <= 24) begin
                            classe = 3'd1;
                        end else begin
                            classe = 3'd0;
                        end
                    end
                end else begin
                    if (rr_next_base <= 342) begin
                        if (sad_t <= 137) begin
                            classe = 3'd0;
                        end else begin
                            if (rr_base <= 217) begin
                                if (rr_prev <= 246) begin
                                    classe = 3'd2;
                                end else begin
                                    classe = 3'd0;
                                end
                            end else begin
                                classe = 3'd0;
                            end
                        end
                    end else begin
                        if (rr_next_ratio <= 264) begin
                            if (d_w <= 14) begin
                                classe = 3'd0;
                            end else begin
                                if (irr_np <= 20) begin
                                    classe = 3'd2;
                                end else begin
                                    classe = 3'd0;
                                end
                            end
                        end else begin
                            if (d_w <= 17) begin
                                classe = 3'd0;
                            end else begin
                                if (irr_np <= 14) begin
                                    classe = 3'd2;
                                end else begin
                                    classe = 3'd0;
                                end
                            end
                        end
                    end
                end
            end
        end else begin
            if (rr_ratio <= 238) begin
                if (rr_base <= 80) begin
                    if (amp_r32 <= 147) begin
                        classe = 3'd2;
                    end else begin
                        classe = 3'd0;
                    end
                end else begin
                    if (sad_t <= 420) begin
                        if (rr_next_ratio <= 268) begin
                            if (rr_base <= 195) begin
                                classe = 3'd2;
                            end else begin
                                if (rr_next <= 404) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd2;
                                end
                            end
                        end else begin
                            if (rr_next <= 209) begin
                                classe = 3'd0;
                            end else begin
                                if (rr_prev <= 97) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd2;
                                end
                            end
                        end
                    end else begin
                        if (rr_next <= 106) begin
                            if (rr_prev <= 93) begin
                                classe = 3'd0;
                            end else begin
                                classe = 3'd2;
                            end
                        end else begin
                            if (d_w <= 11) begin
                                if (irr_np <= 15) begin
                                    classe = 3'd2;
                                end else begin
                                    classe = 3'd0;
                                end
                            end else begin
                                if (rr_next_ratio <= 279) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd2;
                                end
                            end
                        end
                    end
                end
            end else begin
                if (rr_base <= 186) begin
                    if (amp_r32 <= 259) begin
                        if (rr_prev <= 171) begin
                            if (dpol <= 64) begin
                                classe = 3'd2;
                            end else begin
                                classe = 3'd0;
                            end
                        end else begin
                            if (rr_ratio <= 270) begin
                                classe = 3'd2;
                            end else begin
                                classe = 3'd0;
                            end
                        end
                    end else begin
                        if (rr_next_ratio <= 168) begin
                            classe = 3'd2;
                        end else begin
                            if (sad_t <= 254) begin
                                if (dpol <= 44) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd3;
                                end
                            end else begin
                                classe = 3'd0;
                            end
                        end
                    end
                end else begin
                    if (amp_r32 <= 165) begin
                        if (rr_ratio <= 296) begin
                            if (rr_base <= 242) begin
                                if (rr_next_base <= 247) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd2;
                                end
                            end else begin
                                classe = 3'd0;
                            end
                        end else begin
                            classe = 3'd0;
                        end
                    end else begin
                        if (rr_next_base <= 184) begin
                            if (irr_np <= 12) begin
                                if (rr_next_base <= 148) begin
                                    classe = 3'd0;
                                end else begin
                                    classe = 3'd2;
                                end
                            end else begin
                                classe = 3'd0;
                            end
                        end else begin
                            if (rr_next_base <= 290) begin
                                classe = 3'd0;
                            end else begin
                                if (irr_np <= 16) begin
                                    classe = 3'd2;
                                end else begin
                                    classe = 3'd0;
                                end
                            end
                        end
                    end
                end
            end
        end
    end

endmodule

