from fluids_english import *

# 7-19
k_3in_gate_valve = K_gate_valve(f_t=0.017)
print(f"K gate valve {k_3in_gate_valve}")

k_3in_mitre = K_mitre(f_t=0.017, angle=90)
print(f"K 3in mitre {k_3in_mitre}")

k_3in_straight_pipe = K_L(f=0.017, L=10, D=3.068/12)
print(f"K 3in straight pipe {k_3in_straight_pipe}")

k_sudden_contraction = K_contraction(angle=180, d_small=2.067, d_large=3.068)
print(f"K sudden contraction {k_sudden_contraction}")

k_2in_straight_pipe = K_different_pipe_ID(K_L(f=0.019, L=20, D=2.067/12), da=3.068, db=2.067)
print(f"K 2in straight pipe {k_2in_straight_pipe}")

k_exit_2 = K_different_pipe_ID(K_exit(), da=3.068, db=2.067)
print(f"K 2in exit {k_exit_2}")

k_entrance_3 = K_entrance_flush(r_d_ratio=0)
print(f"3 inch flush entrance {k_entrance_3}")

K_total = k_3in_gate_valve + k_3in_mitre + k_3in_straight_pipe + k_2in_straight_pipe + k_entrance_3 + k_exit_2 + k_sudden_contraction
print(f"K total {K_total}")

discharge_flow = discharge_Q(d=3.068, head=11.5, K=K_total)
# set up loop
for i in range(10):
    print(f"Discharge Flow on iteration {i}  |  {discharge_flow:.2f}  |  current K {K_total}")
    re_3in = Re(Q=discharge_flow, rho=62.4, d=3.068, mu=1.1)
    f_3in = f(eta=0.00015, d=3.068, Re=re_3in)
    re_2in = Re(Q=discharge_flow, rho=62.4, d=2.067, mu=1.1)
    f_2in = f(eta=0.00015, d=2.067, Re=re_2in)
    k_3in_straight_pipe = K_L(f=f_3in, L=10, D=3.068/12)
    k_2in_straight_pipe = K_different_pipe_ID(K_L(f=f_2in, L=20, D=2.067/12), da=3.068, db=2.067)
    K_total = k_3in_gate_valve + k_3in_mitre + k_3in_straight_pipe + k_2in_straight_pipe + k_entrance_3 + k_exit_2 + k_sudden_contraction
    discharge_flow = discharge_Q(d=3.068, head=11.5, K=K_total)
print(f"f for 2 inch {f_2in:.3f} | f for 3 inch {f_3in:.3f}")
print(f"Re for 2 inch {re_2in:,.0f} | Re for 3 inch {re_3in:,.0f}")

