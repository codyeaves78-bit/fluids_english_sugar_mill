"""Streamlit page: sugar-process stream properties and pipe head loss for
molasses and massecuite, built on SugarStreamFluids.py / sugar_stream_properties_fluids.py.

Molasses and massecuite are non-Newtonian (power-law / Ostwald-de Waele)
fluids, so this page uses Rein's Cane Sugar Engineering consistency (K) and
flow behavior index (n) formulas and pipe head-loss equation, rather than
the Newtonian/Colebrook approach used on the Pipe Flow page.
"""

import streamlit as st

from SugarStreamFluids import SugarStreamFluids
import sugar_stream_properties_fluids as ssp

TWO_K_OPTIONS = ssp.flatten_two_k()

st.set_page_config(page_title="Sugar Stream Properties", layout="wide")

st.title("Sugar Stream Properties")
st.caption("Molasses and massecuite properties and pipe head loss, using Rein's Cane Sugar Engineering "
           "power-law (Ostwald-de Waele) equations - built on your own SugarStreamFluids object.")

st.subheader("Stream")
c1, c2, c3, c4 = st.columns(4)
with c1:
    brix = st.number_input("Brix (%)", value=95.0, min_value=0.0, max_value=100.0, step=0.5)
with c2:
    purity = st.number_input("Purity (%)", value=60.0, min_value=0.01, max_value=100.0, step=0.5)
with c3:
    temp_deg_F = st.number_input("Temperature (deg F)", value=140.0, step=5.0)
with c4:
    grade_label = st.radio("Molasses grade", ["C (final)", "High grade (A/B)"], horizontal=True)
    grade = "C" if grade_label.startswith("C") else "high"

c5, c6, c7 = st.columns(3)
with c5:
    flow_lb_per_hr = st.number_input("Mass flow (lb/hr)", value=20000.0, min_value=0.0001, step=1000.0)
with c6:
    pressure_psia = st.number_input("Pressure (psia)", value=14.7, min_value=0.1, step=1.0,
                                     help="Used for boiling point elevation and latent heat (e.g. in a pan or evaporator).")
with c7:
    level_ft = st.number_input("Liquid level above heating surface (ft)", value=0.0, step=0.5,
                                help="Used for the hydrostatic-head part of boiling point elevation; 0 for non-boiling streams.")

st.subheader("Massecuite (optional)")
is_massecuite = st.checkbox("This is a massecuite stream (contains suspended sugar crystals)", value=False)
if is_massecuite:
    m1, m2, m3 = st.columns(3)
    with m1:
        ml_purity = st.number_input("Mother liquor purity (%)", value=40.0, min_value=0.01, max_value=100.0,
                                     step=0.5, help="Purity of the molasses surrounding the crystals - must be "
                                                     "lower than the overall massecuite purity above.")
    with m2:
        CV = st.number_input("Coefficient of variance, CV", value=50.0, min_value=1.0, step=1.0,
                              help="~50 for C massecuite, ~30-40 for A/B massecuite and grain.")
    with m3:
        L = st.number_input("Average crystal size, L (mm)", value=0.25, min_value=0.01, step=0.05,
                             help="~0.10 grain, ~0.25 C massecuite, ~0.4-0.5 B, ~0.6-1.0 A.")
else:
    ml_purity, CV, L = None, 50.0, 0.25

stream = SugarStreamFluids(brix=brix, purity=purity, flow_lb_per_hr=flow_lb_per_hr, temp_deg_F=temp_deg_F,
                            pressure_psia=pressure_psia, level_ft=level_ft, ml_purity=ml_purity, CV=CV, L=L,
                            grade=grade)

st.subheader("Stream Properties")
st.image(r'C:\Python Projects\Fluids\Screenshot 2026-09-03 093527.png')
st.markdown(f"Image Source 'https://researchspace.ukzn.ac.za/server/api/core/bitstreams/8fd096ce-e93b-49da-b0ff-41338c90fd22/content'")
p1, p2, p3, p4 = st.columns(4)
p1.metric("Specific gravity", f"{stream.specific_gravity:.4f}")
p2.metric("Brix", f"{stream.brix:.2f} ")
p3.metric("Stream Temperature", f"{stream.temp_deg_F:.0f} deg F")
p4.metric("Stream Temperature", f"{(stream.temp_deg_F - 32) * 5 / 9:.0f} deg C")

p5, p6, p7, p8 = st.columns(4)
p5.metric("Purity", f"{stream.purity:.2f}")
p6.metric("Flow behavior index, n", f"{stream.flow_behavior_index_n:.2f}")
p7.metric("Molasses consistency, K", f"{stream.molasses_consistency_Pa_sn:,.2f} Pa·s^n")
p8.metric("Volumetric flow", f"{stream.cu_ft_hr:,.2f} ft3/hr")

if is_massecuite:
    st.markdown("**Massecuite breakdown**")
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Crystal content (% on massecuite)", f"{stream.crystal_content_perc:.2f}%")
    q2.metric("Mother liquor brix", f"{stream.ml_brix:.2f}%")
    q3.metric("Mother liquor consistency", f"{stream.mother_liquor_consistency_Pa_sn:,.2f} Pa·s^n")
    q4.metric("Relative viscosity (crystals)", f"{stream.massecuite_relative_viscosity:.3f}x")
    st.metric("Massecuite consistency, K", f"{stream.massecuite_consistency_Pa_sn:,.2f} Pa·s^n")

st.subheader("Pipe Head Loss")

viscosity_source = st.radio(
    "Consistency / viscosity source for this calculation",
    ["Calculate from formula (brix/purity/temp)", "Enter viscosity manually", "View trusted reference chart"],
    help="The in-app formula is experimental for massecuite/magma and can give unrealistic numbers - "
         "prefer manual entry from a lab test or trusted chart when you have one.",
)

if viscosity_source == "View trusted reference chart":
    st.warning("The in-app power-law calculator for massecuite/magma consistency is experimental and can "
               "produce unrealistic results (especially at low velocity or very high brix). For design-grade "
               "viscosity values, use a trusted published reference instead, then come back and enter it "
               "manually above.")
    st.markdown("#### Cane Factory Product Viscosities")
    st.caption("Viscosity vs. temperature for C/B/A massecuite, B magma, A/B molasses, remelt, and syrup "
               "(log-scale Pa·s, 20-80 deg C).")
    st.link_button("Open the reference chart at sugartech.co.za", "https://www.sugartech.co.za/viscosity/index.php")
    st.caption("Source: Sugar Technology - sugartech.co.za, \"Viscosity\" (Cane Factory Product Viscosities "
               "chart). Not reproduced here - use the link above to view the original.")
else:
    h1, h2, h3, h4 = st.columns(4)
    with h1:
        pipe_ID_inches = st.number_input("Pipe ID (in)", value=4.0, min_value=0.1, step=0.5)
    with h2:
        pipe_length_ft = st.number_input("Pipe length (ft)", value=100.0, min_value=0.0, step=10.0)
    with h4:
        elevation_change_ft = st.number_input("Elevation change, outlet - inlet (ft)", value=0.0, step=1.0,
                                               help="Positive if the discharge point is higher than the source; "
                                                    "added directly to the friction + fittings head loss.")

    manual_viscosity_cP = None
    use_massecuite = False
    with h3:
        if viscosity_source == "Enter viscosity manually":
            manual_viscosity_cP = st.number_input("Viscosity (cP)", value=5000.0, min_value=0.001, step=100.0,
                                                    help="Treated as Newtonian (n=1) at whatever shear rate this "
                                                         "pipe/flow produces. From the Chart provided above, multipy Pa·s by 1000 to get cps")
            st.markdown(f"Pa·s equivalent: {manual_viscosity_cP / 1000}")
        elif is_massecuite:
            use_massecuite = st.checkbox("Use massecuite consistency (unchecked = mother liquor only)", value=True)
        else:
            st.caption("Using molasses consistency (no massecuite crystal content specified above).")

    if viscosity_source == "Calculate from formula (brix/purity/temp)" and (is_massecuite and use_massecuite):
        st.warning("Massecuite/magma consistency from this formula is experimental - cross-check against the "
                   "trusted reference chart (above) before using this number for design or pump sizing.")

    st.markdown("**Fittings & valves (Hooper 2-K method)**")
    if "sugar_fittings" not in st.session_state:
        st.session_state.sugar_fittings = []
    if "sugar_fitting_id" not in st.session_state:
        import itertools
        st.session_state.sugar_fitting_id = itertools.count(1)

    fa1, fa2, fa3 = st.columns([3, 1, 0.8])
    with fa1:
        fitting_label = st.selectbox("Type", list(TWO_K_OPTIONS.keys()))
    with fa2:
        fitting_qty = st.number_input("Qty", value=1, min_value=1, step=1, key="sugar_fit_qty")
    with fa3:
        st.write("")
        st.write("")
        if st.button("Add", key="sugar_fit_add"):
            twok = TWO_K_OPTIONS[fitting_label]
            st.session_state.sugar_fittings.append({
                "row_id": next(st.session_state.sugar_fitting_id),
                "label": fitting_label, "qty": fitting_qty, "K1": twok.K1, "Kinf": twok.Kinf,
            })
            st.rerun()

    if st.session_state.sugar_fittings:
        for j, frow in enumerate(st.session_state.sugar_fittings):
            fc1, fc2, fc3 = st.columns([3, 1, 1])
            fc1.write(f"{frow['label']}  _(K1={frow['K1']}, K∞={frow['Kinf']})_")
            fc2.write(f"qty: {frow['qty']}")
            if fc3.button("Remove", key=f"sugar_fit_rm_{frow['row_id']}"):
                st.session_state.sugar_fittings.pop(j)
                st.rerun()
    else:
        st.caption("No fittings/valves added yet.")

    fittings_list = [(f["K1"], f["Kinf"], f["qty"]) for f in st.session_state.sugar_fittings]

    if st.button("Calculate head loss", type="primary"):
        try:
            if viscosity_source == "Enter viscosity manually":
                result = stream.head_loss(pipe_ID_inches, pipe_length_ft,
                                           K_override=manual_viscosity_cP / 1000.0, n_override=1.0,
                                           fittings=fittings_list, elevation_change_ft=elevation_change_ft)
            else:
                result = stream.head_loss(pipe_ID_inches, pipe_length_ft, use_massecuite=use_massecuite,
                                           fittings=fittings_list, elevation_change_ft=elevation_change_ft)
            st.session_state["sugar_headloss_result"] = result
        except Exception as e:
            st.error(f"Could not solve: {e}")
            st.session_state["sugar_headloss_result"] = None

result = st.session_state.get("sugar_headloss_result")
if result:
    st.subheader("Results")
    r1, r2, r3 = st.columns(3)
    r1.metric("Velocity", f"{result['velocity_fps']:.4f} ft/s")
    r2.metric("Consistency used, K", f"{result['K_Pa_sn']:,.2f} Pa·s^n")
    r3.metric("Flow behavior index, n", f"{result['n']:.2f}")

    r3b, r3c = st.columns(2)
    r3b.metric("Reynolds number (generalized)", f"{result['Re']:,.1f}")
    r3c.metric("Fittings K total", f"{result['fittings_K']:,.3f}")

    r4, r5, r6, r7 = st.columns(4)
    r4.metric("Friction head loss", f"{result['friction_head_loss_ft']:,.3f} ft")
    r5.metric("Fittings head loss", f"{result['fittings_head_loss_ft']:,.3f} ft")
    r6.metric("Elevation change", f"{result['elevation_change_ft']:,.2f} ft")
    r7.metric("Apparent viscosity", f"{result['apparent_viscosity_cP']:,.0f} cP",
              help="The Newtonian-equivalent viscosity at this flow's own wall shear rate - only meaningful "
                   "for this specific velocity/pipe combination, since molasses and massecuite are shear-thinning.")

    r8, r9 = st.columns(2)
    r8.metric("Total head loss", f"{result['head_loss_ft']:,.2f} ft")
    r9.metric("Total pressure loss", f"{result['pressure_loss_psi']:,.2f} psi")

    if result["velocity_fps"] < 0.5:
        st.info("Velocity is quite low (< 0.5 ft/s) - shear-thinning fluids like molasses and massecuite get "
                "dramatically more viscous at low shear rates, so consider whether this pipe is oversized "
                "for the flow.")

with st.expander("About these calculations"):
    st.markdown("""
- Molasses and massecuite are modeled as power-law (Ostwald-de Waele) fluids: `tau = K * gamma_dot ** n`,
  per Rein's *Cane Sugar Engineering* (1st ed.) - **not** a single Newtonian viscosity.
- **K (consistency)** comes from Rein eq. 16.5, a function of brix, purity, temperature, and grade
  (C vs. high-grade A/B molasses use different correlation constants and flow behavior indices).
- **Massecuite consistency** = mother liquor consistency x a relative-viscosity multiplier that accounts for
  suspended sugar crystals (crystal size, crystal/mother-liquor volume ratio, and coefficient of variance).
- **Head loss** comes from Rein eq. 16.17, valid for laminar flow (which molasses and massecuite almost
  always are, given how viscous they are) - it is computed in meters (metric, matching Rein's own equations),
  then converted to feet and psi for display.
- **Apparent viscosity** is only reported alongside a head-loss result because, for a shear-thinning fluid,
  viscosity isn't a fixed property - it depends on the actual shear rate, which depends on the actual
  velocity in the actual pipe.
- **Fittings & valves** use Hooper's 2-K method (`K_f = K1/Re + K∞·(1 + 1/D)`, D in inches), evaluated at this
  flow's generalized (power-law) Reynolds number per Rein eq. 16.14 - a standard practical approximation for
  applying a Newtonian-derived fitting correlation to non-Newtonian service.
- **Elevation change** (outlet minus inlet) is added directly to the friction + fittings head loss to get the
  total head and pressure the pump (or gravity) has to overcome.
""")
