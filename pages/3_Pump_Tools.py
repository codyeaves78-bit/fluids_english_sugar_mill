"""Streamlit page: standalone pump calculations not tied to a modeled pipe run.

Built on sizing_calc.py. Matches Crane TP-410 worked examples 7.32 (NPSH
available), 7.33 (pump affinity rules), and 7.34 (pump power and operating
cost).
"""

import streamlit as st

import pipe_flow_calc as pf
import sizing_calc as sc

st.set_page_config(page_title="Pump Tools", layout="wide")

st.title("Pump Tools")
st.caption("NPSH available, pump affinity rules, and operating cost - "
           "https://github.com/CalebBell/fluids")

tab_npsh, tab_affinity, tab_cost = st.tabs(["NPSH Available", "Pump Affinity Rules", "Operating Cost"])

# ===========================================================================
# NPSH Available
# ===========================================================================
with tab_npsh:
    st.subheader("Fluid")
    fluid_kind = st.radio("Type", ["Water (auto, IAPWS-97)", "Custom liquid"], key="npsh_fluid")
    T_F = st.number_input("Temperature (deg F)", value=60.0, step=5.0, key="npsh_T")
    if fluid_kind.startswith("Water"):
        rho, mu_cP, phase = pf.water_properties(T_F, 20.0)
        Psat = sc.water_psat_psia(T_F)
        st.caption(f"rho = {rho:.3f} lb/ft3, Psat = {Psat:.4f} psia")
    else:
        c1, c2 = st.columns(2)
        with c1:
            rho = st.number_input("Density (lb/ft3)", value=62.4, min_value=0.01, step=0.1, key="npsh_rho")
        with c2:
            Psat = st.number_input("Vapor pressure at T (psia)", value=0.5, min_value=0.0, step=0.1,
                                    key="npsh_psat")

    st.subheader("Suction conditions")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        basis = st.radio("Source pressure basis", ["psig", "psia"], horizontal=True, key="npsh_basis")
    with c2:
        atm = st.number_input("Atmospheric (psia)", value=14.696, step=0.01, key="npsh_atm") \
            if basis == "psig" else 14.696
    with c3:
        P_source_val = st.number_input(f"Source surface pressure ({basis})", value=0.0, step=1.0,
                                        key="npsh_psource")
    P_source_psia = P_source_val + atm if basis == "psig" else P_source_val
    with c4:
        st.metric("Source pressure", f"{P_source_psia:.3f} psia")

    c5, c6, c7 = st.columns(3)
    with c5:
        elevation_diff_ft = st.number_input("Pump elevation above source surface (ft)", value=25.0, step=1.0,
                                             key="npsh_elev",
                                             help="Negative if the source liquid surface is above the pump "
                                                  "(flooded suction).")
    with c6:
        friction_loss_ft = st.number_input("Suction piping friction loss (ft)", value=6.0, min_value=0.0,
                                            step=0.5, key="npsh_floss",
                                            help="Compute this on the Pipe Flow page by modeling just the "
                                                 "suction piping, then enter the resulting head loss here.")
    with c7:
        NPSHr_ft = st.number_input("Required NPSH, NPSHr (ft)", value=20.0, min_value=0.0, step=1.0,
                                    key="npsh_npshr")

    npsha = sc.npsh_available(P_source_psia, Psat, rho, elevation_diff_ft, friction_loss_ft)
    margin = npsha - NPSHr_ft

    st.subheader("Results")
    r1, r2, r3 = st.columns(3)
    r1.metric("NPSH available", f"{npsha:,.2f} ft")
    r2.metric("NPSH required", f"{NPSHr_ft:,.2f} ft")
    r3.metric("Margin", f"{margin:,.2f} ft")
    if margin < 0:
        st.error("NPSHa is below NPSHr - this pump will cavitate. Raise source pressure/elevation, "
                 "reduce suction losses, or select a pump with lower NPSHr.")
    elif margin < NPSHr_ft * 0.3:
        st.warning("Margin is thin (< 30% of NPSHr). Many pump vendors recommend at least a 30% "
                   "(or 3-5 ft) margin to avoid cavitation under off-design conditions.")
    else:
        st.success("NPSHa exceeds NPSHr with reasonable margin.")


# ===========================================================================
# Pump Affinity Rules
# ===========================================================================
with tab_affinity:
    st.markdown("Scale a pump's performance to a new speed or impeller trim using the affinity laws: "
                "Q ∝ ratio, H ∝ ratio², Power ∝ ratio³.")
    st.subheader("Known operating point")
    c1, c2, c3 = st.columns(3)
    with c1:
        Q1 = st.number_input("Flow rate Q1 (GPM)", value=400.0, min_value=0.0, step=10.0, key="aff_q1")
    with c2:
        H1 = st.number_input("Head H1 (ft)", value=126.0, min_value=0.0, step=1.0, key="aff_h1")
    with c3:
        P1 = st.number_input("Power P1 (hp)", value=17.5, min_value=0.0, step=0.5, key="aff_p1")

    st.subheader("Scaling")
    basis = st.radio("Scale by", ["Speed (RPM)", "Impeller diameter", "Direct ratio"], horizontal=True,
                      key="aff_basis")
    if basis == "Speed (RPM)":
        c1, c2 = st.columns(2)
        with c1:
            N1 = st.number_input("Speed N1 (rpm)", value=3500.0, min_value=0.01, step=10.0, key="aff_n1")
        with c2:
            N2 = st.number_input("Speed N2 (rpm)", value=1700.0, min_value=0.01, step=10.0, key="aff_n2")
        ratio = N2 / N1
    elif basis == "Impeller diameter":
        c1, c2 = st.columns(2)
        with c1:
            D1 = st.number_input("Impeller D1 (in)", value=10.0, min_value=0.01, step=0.1, key="aff_d1")
        with c2:
            D2 = st.number_input("Impeller D2 (in)", value=9.0, min_value=0.01, step=0.1, key="aff_d2")
        ratio = D2 / D1
    else:
        ratio = st.number_input("Ratio (new/old)", value=0.5, min_value=0.01, step=0.01, key="aff_ratio")
    st.caption(f"ratio = {ratio:.4f}")

    result = sc.pump_affinity(Q1, H1, P1, ratio)
    st.subheader("Results at the new condition")
    r1, r2, r3 = st.columns(3)
    r1.metric("Flow rate Q2", f"{result['Q2_gpm']:,.2f} gpm")
    r2.metric("Head H2", f"{result['H2_ft']:,.2f} ft")
    r3.metric("Power P2", f"{result['power2_hp']:,.2f} hp")
    st.caption("Affinity laws assume similar efficiency and are most accurate for modest speed/trim changes "
               "(roughly within 20%) - verify against the pump curve for larger changes.")


# ===========================================================================
# Pump Operating Cost
# ===========================================================================
with tab_cost:
    st.subheader("Duty point")
    c1, c2, c3 = st.columns(3)
    with c1:
        Q_cost = st.number_input("Flow rate (GPM)", value=700.0, min_value=0.0, step=10.0, key="cost_q")
    with c2:
        head_cost = st.number_input("Head (ft)", value=428.0, min_value=0.0, step=1.0, key="cost_head")
    with c3:
        rho_cost = st.number_input("Density (lb/ft3)", value=62.364, min_value=0.01, step=0.1, key="cost_rho")

    st.subheader("Efficiencies")
    c4, c5, c6 = st.columns(3)
    with c4:
        pump_eff = st.slider("Pump efficiency (%)", min_value=1, max_value=100, value=71, key="cost_pumpeff") / 100.0
    with c5:
        motor_eff = st.slider("Motor efficiency (%)", min_value=1, max_value=100, value=95, key="cost_motoreff") / 100.0
    with c6:
        drive_eff = st.slider("Drive/VSD efficiency (%)", min_value=1, max_value=100, value=96,
                               key="cost_driveeff") / 100.0

    st.subheader("Operation")
    c7, c8 = st.columns(2)
    with c7:
        rate = st.number_input("Electricity rate ($/kWh)", value=0.12, min_value=0.0, step=0.01, key="cost_rate")
    with c8:
        hours = st.number_input("Operating hours per year", value=8000.0, min_value=0.0, max_value=8760.0,
                                 step=100.0, key="cost_hours")

    result = sc.pump_operating_cost(Q_cost, head_cost, rho_cost, pump_eff, motor_eff, drive_eff, rate, hours)
    st.subheader("Results")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Brake horsepower", f"{result['bhp']:,.2f} hp")
    r2.metric("Electrical power", f"{result['electrical_hp']:,.2f} hp")
    r3.metric("Electrical power", f"{result['electrical_kw']:,.2f} kW")
    r4.metric("Annual operating cost", f"${result['annual_cost']:,.2f}")
