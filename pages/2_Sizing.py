"""Streamlit page: orifice/nozzle flow-meter sizing and control valve sizing.

Built on sizing_calc.py, wrapping Caleb Bell's ``fluids.flow_meter``
(differential-pressure meters) and ``fluids.control_valve`` (IEC 60534),
matching the Crane TP-410 worked examples at
https://fluids.readthedocs.io/Examples/Crane%20TP%20410%20Solved%20Problems/ .
"""

import streamlit as st

import pipe_flow_calc as pf
import gas_flow_calc as gc
import sizing_calc as sc

st.set_page_config(page_title="Sizing Calculator", layout="wide")

st.title("Flow Meter & Control Valve Sizing")
st.caption("Built on Caleb Bell's `fluids.flow_meter` and `fluids.control_valve` modules - "
           "https://github.com/CalebBell/fluids")

tab_meter, tab_cv_l, tab_cv_g, tab_tee = st.tabs(["Orifice / Nozzle Meter Sizing", "Control Valve - Liquid",
                                                    "Control Valve - Gas", "Tee / Wye Branch Flow"])


def pressure_block(prefix: str, default_psig: float, key_prefix: str):
    c1, c2 = st.columns([2, 1])
    with c1:
        basis = st.radio(f"{prefix} pressure basis", ["psig", "psia"], horizontal=True, key=f"{key_prefix}_basis")
    with c2:
        atm_psia = st.number_input("Atmospheric (psia)", value=14.696, step=0.01, key=f"{key_prefix}_atm") \
            if basis == "psig" else 14.696
    val = st.number_input(f"{prefix} pressure ({basis})", value=default_psig, step=1.0, key=f"{key_prefix}_val")
    return val + atm_psia if basis == "psig" else val


# ===========================================================================
# Tab 1: Orifice / Nozzle Meter Sizing
# ===========================================================================
with tab_meter:
    st.subheader("Fluid")
    phase = st.radio("Fluid phase", ["Liquid", "Gas / Vapor"], horizontal=True, key="mt_phase")

    if phase == "Liquid":
        liq_kind = st.radio("Type", ["Water (auto, IAPWS-97)", "Custom liquid"], key="mt_liq_kind")
        T_F = st.number_input("Temperature (deg F)", value=60.0, step=5.0, key="mt_T")
        if liq_kind.startswith("Water"):
            rho, mu_cP, ph = pf.water_properties(T_F, 30.0)
            st.caption(f"rho = {rho:.3f} lb/ft3, mu = {mu_cP:.4f} cP")
        else:
            rho = st.number_input("Density (lb/ft3)", value=62.4, min_value=0.01, step=0.1, key="mt_rho")
            mu_cP = st.number_input("Viscosity (cP)", value=1.0, min_value=0.0001, step=0.1,
                                     format="%.4f", key="mt_mu")
        k = 1.0e7  # incompressible - expansibility correction is negligible for liquids
    else:
        gas_kind = st.radio("Type", ["Gas (ideal, by molecular weight)", "Steam (IAPWS-97)"], key="mt_gas_kind")
        T_F = st.number_input("Temperature (deg F)", value=200.0, step=5.0, key="mt_T_gas")
        steam = gas_kind.startswith("Steam")
        if not steam:
            gpc1, gpc2 = st.columns(2)
            with gpc1:
                gas_preset = st.selectbox("Gas", list(gc.GAS_PRESETS.keys()), key="mt_gas_preset")
                MW_gmol = gc.GAS_PRESETS[gas_preset] if gc.GAS_PRESETS[gas_preset] is not None else \
                    st.number_input("Molecular weight (g/mol)", value=20.0, min_value=1.0, step=0.1, key="mt_mw")
            with gpc2:
                mu_cP = st.number_input("Viscosity (cP)", value=0.018, min_value=0.0001, step=0.001,
                                         format="%.4f", key="mt_mu_gas")
        else:
            MW_gmol, mu_cP = None, None
        k = st.number_input("Isentropic exponent, k (Cp/Cv)", value=1.4, min_value=1.0, max_value=1.7,
                             step=0.01, key="mt_k",
                             help="Air/diatomic gas ~1.4, steam ~1.3, natural gas ~1.27")

    st.subheader("Pipe")
    p1, p2 = st.columns(2)
    with p1:
        nps = st.selectbox("Nominal pipe size", pf.NPS_OPTIONS, index=pf.NPS_OPTIONS.index(4.0),
                            format_func=pf.format_nps, key="mt_nps")
    with p2:
        schedule = st.selectbox("Schedule", pf.SCHEDULE_OPTIONS, index=pf.SCHEDULE_OPTIONS.index("40"),
                                 key="mt_sch")
    Di_in = pf.pipe_geometry_in(nps, schedule)[1]
    st.caption(f"ID = {Di_in:.4f} in")

    st.subheader("Meter")
    m1, m2 = st.columns(2)
    with m1:
        meter_label = st.selectbox("Meter type", list(sc.METER_TYPES.keys()), key="mt_type")
        meter_type = sc.METER_TYPES[meter_label]
    with m2:
        if meter_type in sc.ORIFICE_METER_TYPES:
            taps_label = st.selectbox("Tap location", list(sc.TAPS_OPTIONS.keys()), key="mt_taps")
            taps = sc.TAPS_OPTIONS[taps_label]
        else:
            taps = "D and D/2"
            st.caption("(Taps not applicable to nozzles)")

    st.subheader("Flow / Pressure")
    solve_for_label = st.selectbox("Solve for", ["Bore / throat diameter (D2)", "Flow rate",
                                                    "Upstream pressure (P1)", "Downstream pressure (P2)"],
                                    key="mt_solvefor")
    solve_for = {"Bore / throat diameter (D2)": "D2", "Flow rate": "m",
                 "Upstream pressure (P1)": "P1", "Downstream pressure (P2)": "P2"}[solve_for_label]

    fcols = st.columns(3)
    with fcols[0]:
        if solve_for != "D2":
            D2_in = st.number_input("Bore / throat diameter (in)", value=round(Di_in * 0.5, 3),
                                     min_value=0.01, max_value=Di_in, step=0.01, key="mt_d2")
        else:
            D2_in = None
            st.caption("D2 will be solved for.")
    with fcols[1]:
        if solve_for != "P1":
            P1_psia = pressure_block("Upstream (P1)", 100.0, "mt_P1")
        else:
            P1_psia = None
            st.caption("P1 will be solved for.")
    with fcols[2]:
        if solve_for != "P2":
            P2_psia = pressure_block("Downstream (P2)", 90.0, "mt_P2")
        else:
            P2_psia = None
            st.caption("P2 will be solved for.")

    m_lbhr = None
    if solve_for != "m":
        flow_col1, flow_col2 = st.columns(2)
        with flow_col1:
            if phase == "Liquid":
                Q_gpm = st.number_input("Flow rate (GPM)", value=200.0, min_value=0.0001, step=10.0,
                                         key="mt_q_gpm")
                m_lbhr = pf.kgs_to_lbhr(pf.gpm_to_m3s(Q_gpm) * pf.lbft3_to_kgm3(rho))
            else:
                Q_scfh = st.number_input("Standard volumetric flow (scfh)", value=6000.0, min_value=0.0001,
                                          step=100.0, key="mt_q_scfh")
                with st.expander("Standard reference conditions"):
                    Ts_F = st.number_input("Standard temperature (deg F)", value=60.0, key="mt_ts")
                    Ps_psia = st.number_input("Standard pressure (psia)", value=14.696, key="mt_ps")
                m_lbhr = gc.std_volumetric_to_lbhr(Q_scfh, steam, MW_gmol, 1.0, Ts_F, Ps_psia)
                st.caption(f"= {m_lbhr:,.2f} lb/hr")
    else:
        st.caption("Flow rate will be solved for.")

    if phase != "Liquid":
        P_ref_psia = P1_psia if P1_psia is not None else (P2_psia if P2_psia is not None else 100.0)
        if steam:
            rho, mu_cP, gas_phase = pf.water_properties(T_F, P_ref_psia)
        else:
            rho = gc.ideal_gas_density_lbft3(P_ref_psia, T_F, MW_gmol, 1.0)
            gas_phase = "Gas (ideal)"
        st.caption(f"Properties at ~{P_ref_psia:.1f} psia, {T_F:.0f}F: "
                   f"rho={rho:.4f} lb/ft3, mu={mu_cP:.5f} cP, phase={gas_phase}")

    if st.button("Calculate", key="mt_calc", type="primary"):
        try:
            result = sc.solve_meter(D_in=Di_in, rho_lbft3=rho, mu_cP=mu_cP, k=k, D2_in=D2_in,
                                     P1_psia=P1_psia, P2_psia=P2_psia, m_lbhr=m_lbhr,
                                     meter_type=meter_type, taps=taps, solve_for=solve_for)
            st.session_state["mt_result"] = result
        except Exception as e:
            st.error(f"Could not solve: {e}")
            st.session_state["mt_result"] = None

    result = st.session_state.get("mt_result")
    if result:
        st.subheader("Results")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Bore / throat diameter", f"{result['D2_in']:.4f} in")
        r2.metric("Beta ratio (D2/D)", f"{result['beta']:.4f}")
        r3.metric("Upstream pressure P1", f"{result['P1_psia']:,.2f} psia")
        r4.metric("Downstream pressure P2", f"{result['P2_psia']:,.2f} psia")

        r5, r6, r7, r8 = st.columns(4)
        r5.metric("Differential pressure", f"{result['dP_psi']:,.4f} psi")
        r6.metric("Mass flow", f"{result['m_lbhr']:,.1f} lb/hr")
        r7.metric("Volumetric flow", f"{result['Q_gpm']:,.2f} gpm")
        r8.metric("Pipe velocity", f"{result['V_pipe_fts']:,.2f} ft/s")

        r9, r10, r11, r12 = st.columns(4)
        r9.metric("Pipe Reynolds #", f"{result['Re_pipe']:,.0f}")
        r10.metric("Discharge coeff. C", f"{result['C']:.4f}")
        r11.metric("Expansibility", f"{result['epsilon']:.4f}")
        r12.metric("Flow coefficient", f"{result['flow_coefficient']:.4f}")

        st.metric("Permanent (non-recoverable) pressure loss", f"{result['nprd_psi']:,.4f} psi",
                  help="The portion of the measured differential pressure that does not recover downstream. "
                       "Nozzles and venturis recover most of the measured dP; orifice plates recover very little.")

        if result["Re_pipe"] < 4000:
            st.info("Pipe flow is laminar or transitional (Re < 4000). Prefer the 'Hollingshead orifice', "
                    "'conical orifice', or 'quarter-circle orifice' meter types for low-Re service - the "
                    "standard ISO 5167 orifice correlation is validated for turbulent flow.")


# ===========================================================================
# Tab 2: Control Valve - Liquid
# ===========================================================================
with tab_cv_l:
    st.subheader("Fluid")
    cvl_kind = st.radio("Type", ["Water (auto, IAPWS-97)", "Custom liquid"], key="cvl_kind")
    T_F_l = st.number_input("Temperature (deg F)", value=160.0, step=5.0, key="cvl_T")
    if cvl_kind.startswith("Water"):
        rho_l, mu_cP_l, ph_l = pf.water_properties(T_F_l, 50.0)
        Psat_l = sc.water_psat_psia(T_F_l)
        Pc_l = sc.WATER_PC_PSIA
        st.caption(f"rho={rho_l:.3f} lb/ft3, mu={mu_cP_l:.4f} cP, Psat={Psat_l:.3f} psia, Pc={Pc_l:.1f} psia")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            rho_l = st.number_input("Density (lb/ft3)", value=62.4, min_value=0.01, step=0.1, key="cvl_rho")
        with c2:
            mu_cP_l = st.number_input("Viscosity (cP)", value=1.0, min_value=0.0001, step=0.1, key="cvl_mu")
        with c3:
            Psat_l = st.number_input("Saturation pressure (psia)", value=1.0, min_value=0.0, step=1.0,
                                      key="cvl_psat")
        with c4:
            Pc_l = st.number_input("Critical pressure (psia)", value=1000.0, min_value=1.0, step=10.0,
                                    key="cvl_pc")

    st.subheader("Process conditions")
    pc1, pc2, pc3 = st.columns(3)
    with pc1:
        P1_l = pressure_block("Upstream (P1)", 80.0, "cvl_P1")
    with pc2:
        P2_l = pressure_block("Downstream (P2)", 70.0, "cvl_P2")
    with pc3:
        Q_l = st.number_input("Flow rate (GPM)", value=250.0, min_value=0.0001, step=10.0, key="cvl_q")

    st.subheader("Valve & piping")
    v1, v2, v3, v4, v5 = st.columns(5)
    with v1:
        nps_l = st.selectbox("Line size", pf.NPS_OPTIONS, index=pf.NPS_OPTIONS.index(4.0),
                              format_func=pf.format_nps, key="cvl_nps")
    with v2:
        sch_l = st.selectbox("Line schedule", pf.SCHEDULE_OPTIONS, index=pf.SCHEDULE_OPTIONS.index("40"),
                              key="cvl_sch")
    D_line_l = pf.pipe_geometry_in(nps_l, sch_l)[1]
    with v3:
        d_valve_l = st.number_input("Valve port size (in)", value=round(D_line_l * 0.75, 2), min_value=0.1,
                                     step=0.1, key="cvl_dvalve")
    with v4:
        FL_l = st.number_input("FL (liquid pressure recovery factor)", value=0.9, min_value=0.1, max_value=1.0,
                                step=0.01, key="cvl_fl",
                                help="Typically 0.8-0.9 full open; get from the manufacturer, don't rely on default.")
    with v5:
        Fd_l = st.number_input("Fd (valve style modifier)", value=1.0, min_value=0.1, max_value=1.0, step=0.05,
                                key="cvl_fd", help="0.1-1.0; get from the manufacturer, don't rely on default.")
    st.caption(f"Line ID = {D_line_l:.4f} in")

    if st.button("Calculate", key="cvl_calc", type="primary"):
        try:
            result_l = sc.solve_control_valve_liquid(
                rho_lbft3=rho_l, Psat_psia=Psat_l, Pc_psia=Pc_l, mu_cP=mu_cP_l,
                P1_psia=P1_l, P2_psia=P2_l, Q_gpm=Q_l,
                D1_in=D_line_l, D2_in=D_line_l, d_in=d_valve_l, FL=FL_l, Fd=Fd_l)
            st.session_state["cvl_result"] = result_l
        except Exception as e:
            st.error(f"Could not solve: {e}")
            st.session_state["cvl_result"] = None

    result_l = st.session_state.get("cvl_result")
    if result_l:
        st.subheader("Results")
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Required Cv", f"{result_l['Cv']:,.2f} gpm")
        rc2.metric("Required Kv", f"{result_l['Kv']:,.2f} m3/hr")
        rc3.metric("Choked flow?", "Yes" if result_l["choked"] else "No")
        rc4.metric("Laminar flow?", "Yes" if result_l["laminar"] else "No")
        st.metric("Choke pressure threshold (P2)", f"{result_l['P2_choke_psia']:,.2f} psia",
                  help="Downstream pressure below which choked flow begins, at this P1/FL. "
                       "Compare against the actual P2 above.")
        st.caption(f"Valve Reynolds number: {result_l['Rev']:,.0f}" if result_l["Rev"] else "")
        if result_l["choked"]:
            st.warning("Flow is choked at the valve - increasing the pressure drop further will not "
                       "increase flow. Consider a larger valve or anti-cavitation trim.")


# ===========================================================================
# Tab 3: Control Valve - Gas
# ===========================================================================
with tab_cv_g:
    st.subheader("Fluid")
    gpreset_col, mu_col, k_col, z_col = st.columns(4)
    with gpreset_col:
        gas_preset_g = st.selectbox("Gas", list(gc.GAS_PRESETS.keys()), key="cvg_preset")
        MW_g = gc.GAS_PRESETS[gas_preset_g] if gc.GAS_PRESETS[gas_preset_g] is not None else \
            st.number_input("Molecular weight (g/mol)", value=20.0, min_value=1.0, step=0.1, key="cvg_mw")
    with mu_col:
        mu_cP_g = st.number_input("Viscosity (cP)", value=0.018, min_value=0.0001, step=0.001,
                                   format="%.4f", key="cvg_mu")
    with k_col:
        gamma_g = st.number_input("Specific heat ratio, gamma", value=1.4, min_value=1.0, max_value=1.7,
                                   step=0.01, key="cvg_gamma")
    with z_col:
        Z_g = st.number_input("Compressibility factor, Z", value=1.0, min_value=0.1, max_value=2.0,
                               step=0.01, key="cvg_z")

    T_F_g = st.number_input("Inlet temperature (deg F)", value=70.0, step=5.0, key="cvg_T")

    st.subheader("Process conditions")
    pcg1, pcg2, pcg3 = st.columns(3)
    with pcg1:
        P1_g = pressure_block("Upstream (P1)", 100.0, "cvg_P1")
    with pcg2:
        P2_g = pressure_block("Downstream (P2)", 60.0, "cvg_P2")
    with pcg3:
        Q_scfh_g = st.number_input("Standard volumetric flow (scfh)", value=50000.0, min_value=0.0001,
                                    step=1000.0, key="cvg_q")
    with st.expander("Standard reference conditions"):
        Ts_F_g = st.number_input("Standard temperature (deg F)", value=60.0, key="cvg_ts")
        Ps_psia_g = st.number_input("Standard pressure (psia)", value=14.696, key="cvg_ps")

    st.subheader("Valve & piping")
    vg1, vg2, vg3, vg4, vg5, vg6 = st.columns(6)
    with vg1:
        nps_g = st.selectbox("Line size", pf.NPS_OPTIONS, index=pf.NPS_OPTIONS.index(4.0),
                              format_func=pf.format_nps, key="cvg_nps")
    with vg2:
        sch_g = st.selectbox("Line schedule", pf.SCHEDULE_OPTIONS, index=pf.SCHEDULE_OPTIONS.index("40"),
                              key="cvg_sch")
    D_line_g = pf.pipe_geometry_in(nps_g, sch_g)[1]
    with vg3:
        d_valve_g = st.number_input("Valve port size (in)", value=round(D_line_g * 0.75, 2), min_value=0.1,
                                     step=0.1, key="cvg_dvalve")
    with vg4:
        FL_g = st.number_input("FL", value=0.9, min_value=0.1, max_value=1.0, step=0.01, key="cvg_fl")
    with vg5:
        Fd_g = st.number_input("Fd", value=1.0, min_value=0.1, max_value=1.0, step=0.05, key="cvg_fd")
    with vg6:
        xT_g = st.number_input("xT", value=0.7, min_value=0.1, max_value=1.0, step=0.05, key="cvg_xt",
                                help="Pressure diff. ratio factor at choked flow; get from manufacturer.")
    st.caption(f"Line ID = {D_line_g:.4f} in")

    if st.button("Calculate", key="cvg_calc", type="primary"):
        try:
            result_g = sc.solve_control_valve_gas(
                MW_gmol=MW_g, T_F=T_F_g, mu_cP=mu_cP_g, gamma=gamma_g, Z=Z_g,
                P1_psia=P1_g, P2_psia=P2_g, Q_scfh=Q_scfh_g, Ts_F=Ts_F_g, Ps_psia=Ps_psia_g,
                D1_in=D_line_g, D2_in=D_line_g, d_in=d_valve_g, FL=FL_g, Fd=Fd_g, xT=xT_g)
            st.session_state["cvg_result"] = result_g
        except Exception as e:
            st.error(f"Could not solve: {e}")
            st.session_state["cvg_result"] = None

    result_g = st.session_state.get("cvg_result")
    if result_g:
        st.subheader("Results")
        rg1, rg2, rg3, rg4 = st.columns(4)
        rg1.metric("Required Cv", f"{result_g['Cv']:,.2f}")
        rg2.metric("Required Kv", f"{result_g['Kv']:,.2f} m3/hr")
        rg3.metric("Choked flow?", "Yes" if result_g["choked"] else "No")
        rg4.metric("Laminar flow?", "Yes" if result_g["laminar"] else "No")
        st.metric("Choke pressure threshold (P2)", f"{result_g['P2_choke_psia']:,.2f} psia",
                  help="Downstream pressure below which choked flow begins, at this P1/xT/gamma.")
        st.caption(f"Mass flow: {result_g['m_lbhr']:,.1f} lb/hr" +
                   (f" | Valve Reynolds number: {result_g['Rev']:,.0f}" if result_g["Rev"] else ""))
        if result_g["choked"]:
            st.warning("Flow is choked at the valve - increasing the pressure drop further will not "
                       "increase flow.")


# ===========================================================================
# Tab 4: Tee / Wye Branch Flow
# ===========================================================================
with tab_tee:
    st.markdown("Loss coefficients and head loss for each leg of a tee or wye junction, per Crane TP-410's "
                "branch/run formulas (`K_branch_converging_Crane`, `K_run_converging_Crane`, and their "
                "diverging counterparts).")

    junction_kind = st.radio("Junction type", ["Converging (branch merges into run)",
                                                 "Diverging (run splits into branch)"], key="tee_kind")
    converging = junction_kind.startswith("Converging")

    st.subheader("Fluid")
    fc1, fc2 = st.columns(2)
    with fc1:
        tee_fluid_kind = st.radio("Type", ["Water (auto, IAPWS-97)", "Custom liquid"], key="tee_fluid_kind")
    with fc2:
        T_F_tee = st.number_input("Temperature (deg F)", value=60.0, step=5.0, key="tee_T")
    if tee_fluid_kind.startswith("Water"):
        rho_tee, mu_tee, ph_tee = pf.water_properties(T_F_tee, 30.0)
        st.caption(f"rho = {rho_tee:.3f} lb/ft3")
    else:
        rho_tee = st.number_input("Density (lb/ft3)", value=62.4, min_value=0.01, step=0.1, key="tee_rho")

    st.subheader("Geometry")
    g1, g2, g3 = st.columns(3)
    with g1:
        nps_run = st.selectbox("Run pipe size", pf.NPS_OPTIONS, index=pf.NPS_OPTIONS.index(4.0),
                                format_func=pf.format_nps, key="tee_nps_run")
    with g2:
        sch_run = st.selectbox("Run schedule", pf.SCHEDULE_OPTIONS, index=pf.SCHEDULE_OPTIONS.index("40"),
                                key="tee_sch_run")
    same_size = st.checkbox("Branch is the same size as the run", value=True, key="tee_samesize")
    with g3:
        if not same_size:
            nps_branch = st.selectbox("Branch pipe size", pf.NPS_OPTIONS, index=pf.NPS_OPTIONS.index(4.0),
                                       format_func=pf.format_nps, key="tee_nps_branch")
            sch_branch = st.selectbox("Branch schedule", pf.SCHEDULE_OPTIONS,
                                       index=pf.SCHEDULE_OPTIONS.index("40"), key="tee_sch_branch")
        else:
            nps_branch, sch_branch = nps_run, sch_run

    D_run_in = pf.pipe_geometry_in(nps_run, sch_run)[1]
    D_branch_in = pf.pipe_geometry_in(nps_branch, sch_branch)[1]
    angle = st.number_input("Branch takeoff angle (deg)", value=90.0 if converging else 45.0,
                             min_value=1.0, max_value=180.0, step=1.0, key="tee_angle")
    st.caption(f"Run ID = {D_run_in:.4f} in | Branch ID = {D_branch_in:.4f} in")

    st.subheader("Flow")
    q1, q2 = st.columns(2)
    if converging:
        with q1:
            Q_run_gpm = st.number_input("Run leg flow, before merge (GPM)", value=300.0, min_value=0.0,
                                         step=10.0, key="tee_q_run")
        with q2:
            Q_branch_gpm = st.number_input("Branch leg flow, before merge (GPM)", value=100.0, min_value=0.0,
                                            step=10.0, key="tee_q_branch")
        st.caption(f"Combined flow downstream = {Q_run_gpm + Q_branch_gpm:,.1f} GPM")
    else:
        with q1:
            Q_run_gpm = st.number_input("Run leg flow, after split (GPM)", value=400.0, min_value=0.0,
                                         step=10.0, key="tee_q_run_d")
        with q2:
            Q_branch_gpm = st.number_input("Branch leg flow, after split (GPM)", value=250.0, min_value=0.0,
                                            step=10.0, key="tee_q_branch_d")
        st.caption(f"Combined flow upstream = {Q_run_gpm + Q_branch_gpm:,.1f} GPM")

    if st.button("Calculate", key="tee_calc", type="primary"):
        try:
            result_tee = sc.solve_tee_branch(D_run_in, D_branch_in, Q_run_gpm, Q_branch_gpm, angle,
                                              converging, rho_tee)
            st.session_state["tee_result"] = result_tee
        except Exception as e:
            st.error(f"Could not solve: {e}")
            st.session_state["tee_result"] = None

    result_tee = st.session_state.get("tee_result")
    if result_tee:
        st.subheader("Results")
        t1, t2, t3 = st.columns(3)
        t1.metric("Combined velocity", f"{result_tee['V_combined_fts']:,.2f} ft/s")
        t2.metric("Branch loss coefficient", f"{result_tee['K_branch']:.4f}")
        t3.metric("Run loss coefficient", f"{result_tee['K_run']:.4f}")

        t4, t5, t6, t7 = st.columns(4)
        t4.metric("Branch head loss", f"{result_tee['h_branch_ft']:,.4f} ft")
        t5.metric("Run head loss", f"{result_tee['h_run_ft']:,.4f} ft")
        t6.metric("Branch pressure change", f"{result_tee['dP_branch_psi']:,.4f} psi")
        t7.metric("Run pressure change", f"{result_tee['dP_run_psi']:,.4f} psi")
        st.caption("A negative loss coefficient or head loss means pressure recovery in that leg, "
                   "not a loss - this is physically normal for diverging (splitting) run legs and for "
                   "some converging branch geometries.")
