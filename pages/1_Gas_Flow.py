"""Streamlit page: compressible (gas/steam) flow calculator, English units.

Two independent tools, both built on gas_flow_calc.py / Caleb Bell's
``fluids.compressible`` module, matching the Crane TP-410 worked examples at
https://fluids.readthedocs.io/Examples/Crane%20TP%20410%20Solved%20Problems/ :

- Plant Piping: one pipe size + fittings/valves, isothermal compressible
  flow (steam or gas), with a choked/sonic-velocity check.
- Gas Transmission Pipeline: long gas mains via Weymouth / Panhandle /
  Spitzglass / Fritzsche / Oliphant / Muller / IGT.
"""

import streamlit as st

import pipe_flow_calc as pf
import gas_flow_calc as gc
import fitting_widgets as fw

st.set_page_config(page_title="Gas Flow Calculator", layout="wide")

st.title("Gas / Compressible Flow Calculator")
st.caption("Built on Caleb Bell's `fluids.compressible` module (isothermal gas flow, "
           "Weymouth/Panhandle pipeline equations) - https://github.com/CalebBell/fluids . "
           "For liquids, see the Pipe Flow page.")

tab_plant, tab_pipeline = st.tabs(["Plant Piping (fittings & valves)", "Gas Transmission Pipeline"])


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
# Tab 1: Plant Piping
# ===========================================================================
with tab_plant:
    st.subheader("Fluid")
    fc1, fc2 = st.columns(2)
    with fc1:
        fluid_kind = st.radio("Type", ["Gas (ideal, by molecular weight)", "Steam (IAPWS-97)"], key="pp_fluid_kind")
    steam = fluid_kind.startswith("Steam")

    with fc2:
        T_F = st.number_input("Temperature (deg F)", value=115.0, step=5.0, key="pp_T")

    if not steam:
        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            gas_preset = st.selectbox("Gas", list(gc.GAS_PRESETS.keys()), key="pp_gas_preset")
        with gc2:
            if gc.GAS_PRESETS[gas_preset] is None:
                MW_gmol = st.number_input("Molecular weight (g/mol)", value=20.0, min_value=1.0, step=0.1,
                                           key="pp_mw")
            else:
                MW_gmol = gc.GAS_PRESETS[gas_preset]
                st.metric("Molecular weight", f"{MW_gmol:.2f} g/mol")
        with gc3:
            Z = st.number_input("Compressibility factor, Z", value=1.0, min_value=0.1, max_value=2.0, step=0.01,
                                 key="pp_Z", help="1.0 = ideal gas. Lower for real gas at high pressure.")
        mu_cP_input = st.number_input("Viscosity (cP)", value=0.018 if gas_preset == "Air" else 0.011,
                                       min_value=0.0001, step=0.001, format="%.4f", key="pp_mu")
    else:
        MW_gmol, Z, mu_cP_input = None, None, None
        rho_preview, mu_preview, phase_preview = pf.water_properties(T_F, 100.0)
        st.caption(f"Steam properties come from IAPWS-97 at the actual line pressure each iteration "
                   f"(e.g. at 100 psia, {T_F:.0f}F: rho={rho_preview:.4f} lb/ft3, phase={phase_preview}).")

    st.subheader("Pipe")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        nps = st.selectbox("Nominal pipe size", pf.NPS_OPTIONS, index=pf.NPS_OPTIONS.index(2.0),
                            format_func=pf.format_nps, key="pp_nps")
    with p2:
        schedule = st.selectbox("Schedule", pf.SCHEDULE_OPTIONS, index=pf.SCHEDULE_OPTIONS.index("40"),
                                 key="pp_sch")
    with p3:
        material = st.selectbox("Material", pf.MATERIAL_OPTIONS,
                                 index=pf.MATERIAL_OPTIONS.index("Carbon steel, bare"), key="pp_mat")
    with p4:
        length_ft = st.number_input("Length (ft)", value=75.0, min_value=0.0, step=5.0, key="pp_len")

    custom_roughness_in = 0.0018
    if material == "Custom":
        custom_roughness_in = st.number_input("Custom roughness (in)", value=0.0018, min_value=0.0,
                                                step=0.0001, format="%.5f", key="pp_rough")

    NPS_, Di_in, Do_in, t_in = pf.pipe_geometry_in(nps, schedule)
    roughness_ft = pf.material_roughness_ft(material, custom_roughness_in)
    st.caption(f"ID = {Di_in:.4f} in | OD = {Do_in:.4f} in | roughness = {roughness_ft * 12:.6f} in")

    st.subheader("Fittings & valves")
    if "gas_fittings" not in st.session_state:
        st.session_state.gas_fittings = []
    if "gas_id_counter" not in st.session_state:
        import itertools
        st.session_state.gas_id_counter = itertools.count(1)

    fw.render_add_fitting_form("pp", Di_in, st.session_state.gas_fittings, st.session_state.gas_id_counter)
    fw.render_fitting_list("pp", st.session_state.gas_fittings)

    fittings = [(f["name"], f["qty"], f["values"]) for f in st.session_state.gas_fittings]

    st.subheader("Flow / Pressure")
    solve_for_label = st.selectbox("Solve for", ["Downstream pressure (P2)", "Upstream pressure (P1)",
                                                   "Mass flow rate"], key="pp_solvefor")
    solve_for = {"Downstream pressure (P2)": "P2", "Upstream pressure (P1)": "P1",
                 "Mass flow rate": "m"}[solve_for_label]

    fcols = st.columns(3)
    with fcols[0]:
        if solve_for != "P1":
            P1_psia = pressure_block("Upstream (P1)", 65.0, "pp_P1")
        else:
            P1_psia = None
            st.caption("P1 will be solved for.")
    with fcols[1]:
        if solve_for != "P2":
            P2_psia = pressure_block("Downstream (P2)", 0.0, "pp_P2")
        else:
            P2_psia = None
            st.caption("P2 will be solved for.")
    with fcols[2]:
        m_lbhr = None
        if solve_for != "m":
            flow_unit = st.radio("Flow given as", ["Mass flow (lb/hr)", "Standard volumetric (scfh)"],
                                  key="pp_flow_unit")
            if flow_unit == "Mass flow (lb/hr)":
                m_lbhr = st.number_input("Mass flow (lb/hr)", value=500.0, min_value=0.0001, step=10.0,
                                          key="pp_m_lbhr")
            else:
                Q_scfh = st.number_input("Standard volumetric flow (scfh)", value=6000.0, min_value=0.0001,
                                          step=100.0, key="pp_q_scfh")
                with st.expander("Standard reference conditions"):
                    Ts_F = st.number_input("Standard temperature (deg F)", value=60.0, key="pp_ts")
                    Ps_psia = st.number_input("Standard pressure (psia)", value=14.696, key="pp_ps")
                m_lbhr = gc.std_volumetric_to_lbhr(Q_scfh, steam, MW_gmol, Z, Ts_F, Ps_psia)
                st.caption(f"= {m_lbhr:,.2f} lb/hr")
        else:
            st.caption("Mass flow will be solved for.")

    if st.button("Calculate", key="pp_calc", type="primary"):
        try:
            result = gc.solve_plant_piping(
                Di_in=Di_in, length_ft=length_ft, roughness_ft=roughness_ft, fittings=fittings,
                steam=steam, MW_gmol=MW_gmol, Z=Z, mu_cP_input=mu_cP_input, T_F=T_F,
                P1_psia=P1_psia, P2_psia=P2_psia, m_lbhr=m_lbhr, solve_for=solve_for,
            )
            st.session_state["pp_result"] = result
        except Exception as e:
            st.error(f"Could not solve: {e}")
            st.session_state["pp_result"] = None

    result = st.session_state.get("pp_result")
    if result:
        st.subheader("Results")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Upstream pressure P1", f"{result['P1_psia']:,.2f} psia")
        r2.metric("Downstream pressure P2", f"{result['P2_psia']:,.2f} psia")
        r3.metric("Pressure drop", f"{result['dP_psi']:,.3f} psi")
        r4.metric("Mass flow", f"{result['m_lbhr']:,.1f} lb/hr")

        r5, r6, r7, r8 = st.columns(4)
        r5.metric("Upstream velocity", f"{result['v1_fts']:,.1f} ft/s")
        r6.metric("Downstream velocity", f"{result['v2_fts']:,.1f} ft/s")
        r7.metric("Reynolds #", f"{result['Re']:,.0f}" if result["Re"] else "N/A")
        r8.metric("Darcy f (pipe)", f"{result['fd']:.4f}")

        st.caption(f"Phase: {result['phase']} | Total system K (pipe + fittings): {result['K_total']:.3f} | "
                   f"Equivalent friction factor used in isothermal_gas: {result['fd_eff']:.4f}")

        if result["choked"]:
            st.warning(f"Flow is choked (sonic) at the pipe exit. The critical (minimum possible) downstream "
                       f"pressure is {result['Pcf_psia']:.2f} psia - the requested downstream pressure cannot "
                       f"be reached. Results above show the maximum achievable flow at that critical pressure.")
        else:
            st.success(f"Flow is subsonic. Critical (choke) downstream pressure would be "
                       f"{result['Pcf_psia']:.2f} psia - well below the actual P2.")


# ===========================================================================
# Tab 2: Gas Transmission Pipeline
# ===========================================================================
with tab_pipeline:
    st.subheader("Pipeline")
    method = st.selectbox("Flow equation", list(gc.PIPELINE_METHODS.keys()), key="pl_method")
    entry = gc.PIPELINE_METHODS[method]

    l1, l2, l3, l4 = st.columns(4)
    with l1:
        nps_pl = st.selectbox("Nominal pipe size", pf.NPS_OPTIONS, index=pf.NPS_OPTIONS.index(14.0),
                               format_func=pf.format_nps, key="pl_nps")
    with l2:
        sch_pl = st.selectbox("Schedule", pf.SCHEDULE_OPTIONS, index=pf.SCHEDULE_OPTIONS.index("20"),
                               key="pl_sch")
    with l3:
        L_value = st.number_input("Length", value=100.0, min_value=0.0001, step=1.0, key="pl_len")
    with l4:
        L_unit = st.selectbox("Length units", ["miles", "ft"], key="pl_len_unit")

    Di_in_pl = pf.pipe_geometry_in(nps_pl, sch_pl)[1]
    st.caption(f"ID = {Di_in_pl:.4f} in")

    g1, g2, g3, g4 = st.columns(4)
    with g1:
        SG = st.number_input("Specific gravity (vs. air)", value=0.65, min_value=0.01, step=0.01, key="pl_sg",
                              help="Natural gas is typically 0.55-0.75. Air = 1.0.")
    with g2:
        Tavg_F = st.number_input("Average temperature (deg F)", value=60.0, step=5.0, key="pl_tavg")
    with g3:
        Zavg = st.number_input("Average compressibility, Z", value=1.0, min_value=0.1, max_value=2.0, step=0.01,
                                key="pl_zavg")
    with g4:
        E = st.number_input("Pipeline efficiency, E", value=entry["default_E"], min_value=0.1, max_value=1.0,
                             step=0.01, key="pl_E")

    mu_cP_pl = None
    if entry["needs_mu"]:
        mu_cP_pl = st.number_input("Viscosity (cP)", value=0.011, min_value=0.0001, step=0.001, format="%.4f",
                                    key="pl_mu")

    st.subheader("Flow / Pressure")
    solve_for_pl_label = st.selectbox("Solve for", ["Flow rate (Q)", "Downstream pressure (P2)",
                                                       "Upstream pressure (P1)"], key="pl_solvefor")
    solve_for_pl = {"Flow rate (Q)": "Q", "Downstream pressure (P2)": "P2",
                     "Upstream pressure (P1)": "P1"}[solve_for_pl_label]

    pcols = st.columns(3)
    with pcols[0]:
        if solve_for_pl != "P1":
            P1_psia_pl = pressure_block("Upstream (P1)", 1300.0, "pl_P1")
        else:
            P1_psia_pl = None
            st.caption("P1 will be solved for.")
    with pcols[1]:
        if solve_for_pl != "P2":
            P2_psia_pl = pressure_block("Downstream (P2)", 300.0, "pl_P2")
        else:
            P2_psia_pl = None
            st.caption("P2 will be solved for.")
    with pcols[2]:
        Q_scfh_pl = None
        if solve_for_pl != "Q":
            Q_mmscfd = st.number_input("Flow rate (MMscfd)", value=100.0, min_value=0.0001, step=1.0,
                                        key="pl_q_mmscfd")
            Q_scfh_pl = Q_mmscfd * 1e6 / 24.0
        else:
            st.caption("Flow rate will be solved for.")

    if st.button("Calculate", key="pl_calc", type="primary"):
        try:
            result_pl = gc.solve_pipeline(
                method=method, SG=SG, Tavg_F=Tavg_F, L_value=L_value, L_unit=L_unit, Di_in=Di_in_pl,
                P1_psia=P1_psia_pl, P2_psia=P2_psia_pl, Q_scfh=Q_scfh_pl, solve_for=solve_for_pl,
                Zavg=Zavg, E=E, mu_cP=mu_cP_pl,
            )
            st.session_state["pl_result"] = result_pl
        except Exception as e:
            st.error(f"Could not solve: {e}")
            st.session_state["pl_result"] = None

    result_pl = st.session_state.get("pl_result")
    if result_pl:
        st.subheader("Results")
        rr1, rr2, rr3, rr4 = st.columns(4)
        rr1.metric("Upstream pressure P1", f"{result_pl['P1_psia']:,.1f} psia")
        rr2.metric("Downstream pressure P2", f"{result_pl['P2_psia']:,.1f} psia")
        rr3.metric("Flow rate", f"{result_pl['Q_mmscfd']:,.2f} MMscfd")
        rr4.metric("Flow rate", f"{result_pl['Q_scfh']:,.0f} scfh")
