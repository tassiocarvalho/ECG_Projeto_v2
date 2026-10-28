# -*- coding: utf-8 -*-
# classificador_arvore_v2.py  (GERADO por treinar_v2.py)
# DS1 inteiro, depth=7, pesos N=1 SVEB=1.0 VEB=1.5, 62 comparadores
# Arvore de decisao inteira — identica a rtl/classificador_arvore_v2.v
# Saida: 0=N 1=SVEB 2=VEB 3=F 4=Q (superclasses AAMI EC57)

FEATURES = ['rr_prev', 'rr_next', 'rr_ratio', 'amp_r32', 'sad_t', 'dpol', 'd_w', 'irr_np', 'rr_next_ratio', 'rr_base', 'rr_next_base']

def classificar(rr_prev, rr_next, rr_ratio, amp_r32, sad_t, dpol, d_w, irr_np, rr_next_ratio, rr_base, rr_next_base):
    if sad_t <= 169:
        if rr_base <= 185:
            if irr_np <= 35:
                if rr_prev <= 200:
                    if sad_t <= 103:
                        if rr_next <= 154:
                            return 1
                        else:
                            if rr_next_base <= 171:
                                return 0
                            else:
                                return 1
                    else:
                        if rr_next <= 350:
                            if rr_prev <= 179:
                                return 0
                            else:
                                return 2
                        else:
                            return 2
                else:
                    if rr_ratio <= 213:
                        return 1
                    else:
                        if rr_next <= 167:
                            return 3
                        else:
                            if rr_next_base <= 230:
                                return 0
                            else:
                                return 3
            else:
                if amp_r32 <= 347:
                    if sad_t <= 127:
                        if rr_ratio <= 114:
                            if rr_next <= 314:
                                return 0
                            else:
                                return 1
                        else:
                            return 0
                    else:
                        if rr_next <= 288:
                            return 0
                        else:
                            if rr_next <= 406:
                                return 2
                            else:
                                return 3
                else:
                    if rr_prev <= 186:
                        return 0
                    else:
                        return 3
        else:
            if rr_ratio <= 219:
                if rr_next_ratio <= 270:
                    return 0
                else:
                    if irr_np <= 24:
                        return 1
                    else:
                        return 0
            else:
                if rr_next_base <= 342:
                    if sad_t <= 137:
                        return 0
                    else:
                        if rr_base <= 217:
                            if rr_prev <= 246:
                                return 2
                            else:
                                return 0
                        else:
                            return 0
                else:
                    if rr_next_ratio <= 264:
                        if d_w <= 14:
                            return 0
                        else:
                            if irr_np <= 20:
                                return 2
                            else:
                                return 0
                    else:
                        if d_w <= 17:
                            return 0
                        else:
                            if irr_np <= 14:
                                return 2
                            else:
                                return 0
    else:
        if rr_ratio <= 238:
            if rr_base <= 80:
                if amp_r32 <= 147:
                    return 2
                else:
                    return 0
            else:
                if sad_t <= 420:
                    if rr_next_ratio <= 268:
                        if rr_base <= 195:
                            return 2
                        else:
                            if rr_next <= 404:
                                return 0
                            else:
                                return 2
                    else:
                        if rr_next <= 209:
                            return 0
                        else:
                            if rr_prev <= 97:
                                return 0
                            else:
                                return 2
                else:
                    if rr_next <= 106:
                        if rr_prev <= 93:
                            return 0
                        else:
                            return 2
                    else:
                        if d_w <= 11:
                            if irr_np <= 15:
                                return 2
                            else:
                                return 0
                        else:
                            if rr_next_ratio <= 279:
                                return 0
                            else:
                                return 2
        else:
            if rr_base <= 186:
                if amp_r32 <= 259:
                    if rr_prev <= 171:
                        if dpol <= 64:
                            return 2
                        else:
                            return 0
                    else:
                        if rr_ratio <= 270:
                            return 2
                        else:
                            return 0
                else:
                    if rr_next_ratio <= 168:
                        return 2
                    else:
                        if sad_t <= 254:
                            if dpol <= 44:
                                return 0
                            else:
                                return 3
                        else:
                            return 0
            else:
                if amp_r32 <= 165:
                    if rr_ratio <= 296:
                        if rr_base <= 242:
                            if rr_next_base <= 247:
                                return 0
                            else:
                                return 2
                        else:
                            return 0
                    else:
                        return 0
                else:
                    if rr_next_base <= 184:
                        if irr_np <= 12:
                            if rr_next_base <= 148:
                                return 0
                            else:
                                return 2
                        else:
                            return 0
                    else:
                        if rr_next_base <= 290:
                            return 0
                        else:
                            if irr_np <= 16:
                                return 2
                            else:
                                return 0
