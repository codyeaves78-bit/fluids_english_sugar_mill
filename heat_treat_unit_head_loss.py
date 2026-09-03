# I will base everything in terms of 2" sch 40 pipe
from fluids_english import h_L, Re, v_ft_s, vel_head, K_L, P_from_H, bhp, f, K_formula_1

# 2" hose losses
flow = 200 # gpm
d_hose = 2
rho = 62.4 # lb/ft3
mu = 1 # cps
eta = 0.00015
L_hose = 10 # ft
hose_rey = Re(Q=flow, rho=rho, d=d_hose, mu=mu) # hose Re
hose_f = f(eta=eta, d=d_hose, Re=hose_rey) # hose f
K_hose = K_L(f=hose_f, L=L_hose, D=d_hose/12) # 10 ft length, 2" ID
print(f"flowrate {flow} gpm of water")
print(f"Hose ID {d_hose} inches")
print(f"Re of hose {hose_rey:,.0f}")
print(f"f of hose {hose_f:.3f}")
print(f"K of the hose length {K_hose:.3f}")

# 2" king nipples
K_nipples = 2 * 0.78 # from the book, 2 of them
print(f"K for 2 king nipples {K_nipples}")

# 2" Tee straight thru
K_tee = 0.55 # from earlier hand calc
print(f"K for the Tee {K_tee}")

# 2" ball valve
f_t_2 = 0.019 # friction factor for full turbulent flow on 2" sch 40 pipe
K_ball_valve = 3 * f_t_2
print(f"f_t of 2 inch fittings {f_t_2}")
print(f"K for ball valve {K_ball_valve:.3f}")

# 2" manifold with 16 3/4" holes 12" spacing
K_manifold = 0.72 # earlier hand calc
print(f"K of perforated pipe {K_manifold}")

# K total
K_total = K_hose + K_nipples + K_tee + K_ball_valve + K_manifold
print(f"Sum of Ks {K_total:.3f}")

# Head loss and pressure loss
head_loss = h_L(K=K_total, Q=flow, d=d_hose)
print(f"head loss {head_loss:.2f} ft")

delta_P = P_from_H(rho=62.4, H=head_loss)
print(f"pressure loss {delta_P:.2f} psi")

# Elevation
elevation = 3 # feet above pump CL
print(f"Elevation of water surface above pump cL {elevation} ft")

# Total Head Required
v1 = v_ft_s(Q=flow, d=2) # hose
v2 = v_ft_s(Q=flow, d=2.157) # manifold
v_head_1 = vel_head(v1) # hose
v_head_2 = vel_head(v2) # manifold
print(f"Velocity head 1 {v_head_1:.2f} ft | Velocity Head 2 {v_head_2:.2f} ft")
head_req = elevation + (v_head_2 - v_head_1) + head_loss # discharge head
print(f"Total Head Required {head_req:.2f} ft")

# brake horse power
hp_req = bhp(Q=flow, H=head_req, rho=62.4, eff=0.75)
print(f"Pump brake HP req {hp_req:.2f}")

print(f"{'-' * 20}")
print("Now solving for 3 inch suction losses")

# 3" manifold treat as entrance
K_3_man = 0.78
print(f"K of 3inch {K_manifold:.2f}")

# 3 inch ball valve
f_t_3 = 0.017
print(f"ft of 3 inch pipe {f_t_3}")
K_3_bv = 3 * f_t_3
print(f"K for 3 inch ball valve {K_3_bv:.2f}")

# 2 - 3 inch 90s LR
K_3in_90s = 2 * (14 * f_t_3)
print(f"K of 2  3inch LR 90s {K_3in_90s:.2f}")

# Y strainer
K_y_strainer = 55 * f_t_3
print(f"K of Y strainer {K_y_strainer:.2f}")

# Reducer
K_3_2_red = K_formula_1(angle=30, d_small=2.067, d_large=3.068)
print(f"K of reducer {K_3_2_red:.2f}")

# sw 2" 90s
beta_3_2 = 2.067 / 3.068
K_sw_90s_2in = 2 * (30 * f_t_2) / beta_3_2 ** 4
print(f"K for 2 - 2inch SW 90s in terms of 3 inch pipe {K_sw_90s_2in:.2f}")

# length of 3" pipe
re_3 = Re(Q=flow, rho=62.4, d=3.068, mu=mu)
f_3 = f(eta=eta, d=3.068, Re=re_3)
print(f"friction factor 3 inch pipe {f_3:.3f}")
K_3in_pipe = K_L(f=f_3, L=5, D=3.068)
print(f"K of 3 inch piping {K_3in_pipe:.2f}")

# length of 2" pipe
re_2 = Re(Q=flow, rho=62.4, d=2.068, mu=mu)
f_2 = f(eta=eta, d=2.067, Re=re_3)
K_2in_pipe = K_L(f=f_2, L=12.5, D=2.067) / beta_3_2**4 # in terms of 3" pipe
print(f"friction factor 2 inch pipe {f_2:.3f}")
print(f"K of 2 inch suction pipe in terms of {K_2in_pipe:.2f}")

# Total K 
K_total_suction = K_3_man + K_3_bv + K_3in_90s + K_y_strainer + K_3_2_red + K_sw_90s_2in + K_3in_pipe + K_2in_pipe
print(f"K total on suction {K_total_suction:.2f}")

# head loss on suction
hL_suction = h_L(K_total_suction, Q=flow, d=3.068)
print(f"Head loss on suction side {hL_suction:.2f}")

# NPSHa
npsha = 144 / rho * (14.7 - 1.7) + (0 - (-3)) - hL_suction
npshr = 19
if npsha > npshr:
    msg = 'Good'
else:
    msg = "No Good"
print(f"NPSHa = {npsha:.2f} ft | NPSHr = {npshr} | {msg}")


