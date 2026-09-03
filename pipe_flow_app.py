"""Streamlit app: pipe flow / head-loss calculator, English units.

Built on top of pipe_flow_calc.py, which wraps Caleb Bell's ``fluids``
library (Crane TP-410 fittings/valves/reducers, automatic pipe ID from
NPS+schedule, automatic friction factor from pipe material) plus ``iapws``
for water properties. See https://github.com/CalebBell/fluids and
https://fluids.readthedocs.io/ for the underlying library.

Run with:  streamlit run pipe_flow_app.py
"""

import itertools

import streamlit as st

import pipe_flow_calc as pf
import fitting_widgets as fw

st.set_page_config(page_title="Pipe Flow Calculator", layout="wide")

# ---------------------------------------------------------------------------
# Session state setup
# ---------------------------------------------------------------------------

if "id_counter" not in st.session_state:
    st.session_state.id_counter = itertools.count(1)

if "segments" not in st.session_state:
    st.session_state.segments = [{
        "id": next(st.session_state.id_counter),
        "nps": 3.0,
        "schedule": "40",
        "material": "Carbon steel, bare",
        "custom_roughness_in": 0.0018,
        "length_ft": 50.0,
        "fittings": [],
        "transition_kind": "None",
        "transition_angle": 30.0,
    }]


def new_segment():
    return {
        "id": next(st.session_state.id_counter),
        "nps": 3.0,
        "schedule": "40",
        "material": "Carbon steel, bare",
        "custom_roughness_in": 0.0018,
        "length_ft": 20.0,
        "fittings": [],
        "transition_kind": "None",
        "transition_angle": 30.0,
    }


format_nps = pf.format_nps


# ---------------------------------------------------------------------------
# Sidebar - fluid & flow rate
# ---------------------------------------------------------------------------

st.sidebar.header("Fluid")

fluid_mode = st.sidebar.radio("Fluid properties", ["Water (auto, IAPWS-97)", "Custom fluid"])

if fluid_mode.startswith("Water"):
    temp_F = st.sidebar.number_input("Temperature (deg F)", value=60.0, min_value=32.5, max_value=700.0, step=5.0)
    pressure_psia = st.sidebar.number_input("System pressure (psia)", value=14.7, min_value=1.0, max_value=3000.0,
                                             step=1.0,
                                             help="Needed to keep water liquid at higher temperatures; "
                                                  "raise this if the phase warning below appears.")
    rho_lbft3, mu_cP, phase = pf.water_properties(temp_F, pressure_psia)
    st.sidebar.caption(f"rho = {rho_lbft3:.2f} lb/ft3, mu = {mu_cP:.4f} cP, phase = {phase}")
    if phase != "Liquid":
        st.sidebar.warning(f"Water is not liquid at this T/P ({phase}). Raise pressure or lower temperature.")
else:
    rho_lbft3 = st.sidebar.number_input("Density (lb/ft3)", value=62.4, min_value=0.01, step=0.1)
    mu_cP = st.sidebar.number_input("Viscosity (cP)", value=1.0, min_value=0.0001, step=0.1, format="%.4f")

st.sidebar.header("Flow Rate")
flow_unit = st.sidebar.selectbox("Units", ["GPM", "lb/hr", "ft3/hr", "ft3/min (CFM)", "bbl/hr (oil barrel)"])
flow_value = st.sidebar.number_input(f"Flow rate ({flow_unit})", value=200.0, min_value=0.0001, step=10.0)

if flow_unit == "GPM":
    Q_m3s = pf.gpm_to_m3s(flow_value)
elif flow_unit == "lb/hr":
    Q_m3s = pf.lbhr_to_m3s(flow_value, rho_lbft3)
elif flow_unit == "ft3/hr":
    Q_m3s = pf.cfh_to_m3s(flow_value)
elif flow_unit == "bbl/hr (oil barrel)":
    Q_m3s = pf.bblhr_to_m3s(flow_value)
else:
    Q_m3s = pf.cfm_to_m3s(flow_value)

Q_gpm = pf.m3s_to_gpm(Q_m3s)
st.sidebar.caption(f"= {Q_gpm:,.1f} GPM")

st.sidebar.header("Static / Extra Head")
elevation_ft = st.sidebar.number_input("Elevation change, outlet - inlet (ft)", value=0.0, step=1.0,
                                        help="Positive if the discharge point is higher than the source.")
extra_psi = st.sidebar.number_input("Additional required pressure at outlet (psi)", value=0.0, step=1.0,
                                     help="E.g. required inlet pressure of downstream equipment.")

st.sidebar.header("Pump (optional)")
do_pump = st.sidebar.checkbox("Compute pump brake horsepower", value=True)
if do_pump:
    efficiency_pct = st.sidebar.slider("Pump efficiency (%)", min_value=10, max_value=100, value=75)

st.sidebar.header("Erosional Velocity Check (optional)")
do_erosional = st.sidebar.checkbox("Check API RP 14E erosional velocity", value=True)
if do_erosional:
    C_label = st.sidebar.selectbox("Service", list(pf.EROSIONAL_C_OPTIONS.keys()))
    C_value = pf.EROSIONAL_C_OPTIONS[C_label]

# ---------------------------------------------------------------------------
# Main area - title
# ---------------------------------------------------------------------------

st.title("Liquid Flow / Head-Loss Calculator")
st.caption("Built on Caleb Bell's `fluids` library (Crane TP-410 methods) - "
           "https://github.com/CalebBell/fluids")
st.caption("For compressible fluids (steam, air, natural gas), see the **Gas Flow** page in the sidebar.")

with st.expander("How this works"):
    st.markdown("""
- Build your line as one or more **pipe segments**, each with its own nominal
  size, schedule, and material. Inside diameter, roughness, friction factor,
  and velocity are all computed automatically for you (no lookup tables).
- Add **fittings and valves** to each segment with a count - K values come
  from `fluids`' implementation of the Crane TP-410 (and Rennels) methods.
- If two consecutive segments are different sizes, a **reducer/enlargement**
  is automatically inserted between them - just pick gradual (conical) or
  sudden, and an angle if gradual.
- All inputs and outputs are in English units (GPM, in, ft, lb/ft3, cP, psi,
  deg F, hp). Conversion to/from the SI units `fluids` uses internally is
  done with `fluids.units` (pint).
""")

# ---------------------------------------------------------------------------
# Pipe segments UI
# ---------------------------------------------------------------------------

st.header("Pipe Segments")

segments = st.session_state.segments

for i, seg in enumerate(segments):
    sid = seg["id"]
    with st.expander(f"Segment {i + 1}  (id {sid})", expanded=True):
        c1, c2, c3, c4 = st.columns([1, 1, 1.4, 1])
        with c1:
            seg["nps"] = st.selectbox("Nominal pipe size", pf.NPS_OPTIONS,
                                       index=pf.NPS_OPTIONS.index(seg["nps"]),
                                       format_func=format_nps, key=f"nps_{sid}")
        with c2:
            seg["schedule"] = st.selectbox("Schedule", pf.SCHEDULE_OPTIONS,
                                            index=pf.SCHEDULE_OPTIONS.index(seg["schedule"]),
                                            key=f"sch_{sid}")
        with c3:
            seg["material"] = st.selectbox("Material", pf.MATERIAL_OPTIONS,
                                            index=pf.MATERIAL_OPTIONS.index(seg["material"]),
                                            key=f"mat_{sid}")
            if seg["material"] == "Custom":
                seg["custom_roughness_in"] = st.number_input("Custom roughness (in)",
                                                               value=seg["custom_roughness_in"],
                                                               min_value=0.0, step=0.0001, format="%.5f",
                                                               key=f"rough_{sid}")
        with c4:
            len_unit = st.selectbox("Length units", ["ft", "miles"], key=f"lenunit_{sid}")
            if len_unit == "miles":
                miles_val = st.number_input("Length (miles)", value=seg["length_ft"] / 5280.0, min_value=0.0,
                                             step=0.1, key=f"len_mi_{sid}")
                seg["length_ft"] = miles_val * 5280.0
            else:
                seg["length_ft"] = st.number_input("Length (ft)", value=seg["length_ft"], min_value=0.0, step=1.0,
                                                    key=f"len_{sid}")

        NPS, Di_in, Do_in, t_in = pf.pipe_geometry_in(seg["nps"], seg["schedule"])
        roughness_ft = pf.material_roughness_ft(seg["material"], seg["custom_roughness_in"])
        st.caption(f"ID = {Di_in:.4f} in | OD = {Do_in:.4f} in | wall = {t_in:.4f} in | "
                   f"roughness = {roughness_ft * 12:.6f} in")

        st.markdown("**Fittings & valves in this segment**")

        fw.render_add_fitting_form(f"seg{sid}", Di_in, seg["fittings"], st.session_state.id_counter)
        fw.render_fitting_list(f"seg{sid}", seg["fittings"])

        if i < len(segments) - 1:
            st.markdown("**Transition to next segment**")
            tc1, tc2 = st.columns(2)
            with tc1:
                seg["transition_kind"] = st.selectbox("Type", ["None", "Gradual (conical)", "Sudden"],
                                                        index=["None", "Gradual (conical)", "Sudden"]
                                                        .index(seg["transition_kind"]),
                                                        key=f"trkind_{sid}")
            if seg["transition_kind"] == "Gradual (conical)":
                with tc2:
                    seg["transition_angle"] = st.number_input("Included cone angle (deg)",
                                                                value=seg["transition_angle"],
                                                                min_value=1.0, max_value=180.0, step=1.0,
                                                                key=f"trangle_{sid}")

        if len(segments) > 1:
            if st.button("Remove this segment", key=f"rmseg_{sid}"):
                segments.pop(i)
                st.rerun()

col_add, _ = st.columns([1, 4])
with col_add:
    if st.button("+ Add Pipe Segment"):
        segments.append(new_segment())
        st.rerun()

# ---------------------------------------------------------------------------
# Solve
# ---------------------------------------------------------------------------

solved = []
for seg in segments:
    Di_in = pf.pipe_geometry_in(seg["nps"], seg["schedule"])[1]
    roughness_ft = pf.material_roughness_ft(seg["material"], seg["custom_roughness_in"])
    fittings = [(f["name"], f["qty"], f["values"]) for f in seg["fittings"]]
    result = pf.solve_segment(Di_in, seg["length_ft"], roughness_ft, Q_m3s, rho_lbft3, mu_cP, fittings)
    solved.append(result)

transitions = []
for i in range(len(segments) - 1):
    kind_label = segments[i]["transition_kind"]
    if kind_label == "None":
        continue
    kind = "sudden" if kind_label == "Sudden" else "gradual"
    tr = pf.solve_transition(solved[i], solved[i + 1], kind, segments[i]["transition_angle"])
    transitions.append((i, tr))

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

st.header("Results")

rows = []
for i, (seg, res) in enumerate(zip(segments, solved)):
    rows.append({
        "Segment": i + 1,
        "NPS": format_nps(seg["nps"]),
        "Sch": seg["schedule"],
        "ID (in)": round(res["Di_in"], 3),
        "Length (ft)": seg["length_ft"],
        "Velocity (ft/s)": round(res["V_fts"], 2),
        "Reynolds #": f"{res['Re']:,.0f}",
        "Darcy f": round(res["fd"], 4),
        "K, pipe": round(res["K_pipe"], 3),
        "K, fittings": round(res["K_fittings"], 3),
        "Head loss (ft)": round(res["h_loss_ft"], 3),
    })
st.dataframe(rows, use_container_width=True, hide_index=True)

any_fittings = any(res["fitting_rows"] for res in solved)
if any_fittings:
    with st.expander("Fitting details (equivalent length, minimum lift velocity)"):
        for i, res in enumerate(solved):
            if not res["fitting_rows"]:
                continue
            st.markdown(f"**Segment {i + 1}**")
            frows = []
            for fr in res["fitting_rows"]:
                L_D = pf.equivalent_length_L_over_D(fr["K_each"], res["fd"])
                L_ft = L_D * res["Di_in"] / 12.0
                frows.append({
                    "Fitting": fr["name"], "Qty": fr["qty"], "K (each)": round(fr["K_each"], 4),
                    "L/D (each)": round(L_D, 1), "Equiv. length, ft (each)": round(L_ft, 2),
                })
            st.dataframe(frows, use_container_width=True, hide_index=True)

            for fr in res["fitting_rows"]:
                v_min = pf.min_lift_velocity_fts(fr["name"], fr["values"], res["ctx"], rho_lbft3)
                if v_min is not None:
                    if res["V_fts"] < v_min:
                        st.warning(f"Segment {i + 1}: {fr['name']} may not fully lift at "
                                   f"{res['V_fts']:.2f} ft/s (needs >= {v_min:.2f} ft/s) - risk of "
                                   f"chattering/wear.")
                    else:
                        st.caption(f"Segment {i + 1}: {fr['name']} fully lifts above {v_min:.2f} ft/s "
                                   f"(actual {res['V_fts']:.2f} ft/s - OK).")

if transitions:
    st.subheader("Reducers / Enlargements")
    trows = []
    for i, tr in transitions:
        trows.append({
            "Between segments": f"{i + 1} -> {i + 2}",
            "K": round(tr["K"], 4),
            "Reference velocity (ft/s)": round(tr["V_ref_fts"], 2),
            "Head loss (ft)": round(tr["h_loss_ft"], 4),
        })
    st.dataframe(trows, use_container_width=True, hide_index=True)

friction_head_ft = sum(r["h_loss_ft"] for r in solved) + sum(tr["h_loss_ft"] for _, tr in transitions)
friction_dp_psi = friction_head_ft * rho_lbft3 / 144.0
extra_head_ft = extra_psi * 144.0 / rho_lbft3
total_head_ft = friction_head_ft + elevation_ft + extra_head_ft

st.subheader("Totals")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Friction head loss", f"{friction_head_ft:,.2f} ft")
m2.metric("Friction pressure drop", f"{friction_dp_psi:,.2f} psi")
m3.metric("Elevation change", f"{elevation_ft:,.2f} ft")
m4.metric("Total required head", f"{total_head_ft:,.2f} ft")

if do_pump:
    bhp = pf.brake_horsepower(Q_gpm, total_head_ft, rho_lbft3, efficiency_pct / 100.0)
    p1, p2 = st.columns(2)
    p1.metric("Pump brake horsepower", f"{bhp:,.2f} hp")
    p2.metric("Pump power", f"{pf.hp_to_kw(bhp):,.2f} kW")

if do_erosional:
    v_ero = pf.erosional_velocity_fts(rho_lbft3, C_value)
    v_max = max(r["V_fts"] for r in solved)
    st.subheader("Erosional Velocity Check (API RP 14E)")
    e1, e2 = st.columns(2)
    e1.metric("Erosional velocity limit", f"{v_ero:,.2f} ft/s")
    e2.metric("Max segment velocity", f"{v_max:,.2f} ft/s")
    if v_max > v_ero:
        st.warning(f"Max velocity ({v_max:.2f} ft/s) exceeds the erosional velocity limit ({v_ero:.2f} ft/s).")
    else:
        st.success(f"Max velocity ({v_max:.2f} ft/s) is within the erosional velocity limit ({v_ero:.2f} ft/s).")
