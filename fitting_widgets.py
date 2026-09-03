"""Shared Streamlit widgets for adding/listing fittings, used by both the
liquid (pipe_flow_app.py) and gas (pages/1_Gas_Flow.py) pages so the
reduced-port-valve UI only needs to be built once.
"""

import streamlit as st

import pipe_flow_calc as pf


def render_add_fitting_form(key_prefix: str, Di_in: float, fittings_list: list, id_counter) -> None:
    """Render the 'add a fitting' mini-form and append to fittings_list on click."""
    add_cols = st.columns([2, 1.5, 1.5, 0.8])
    with add_cols[0]:
        fit_name = st.selectbox("Type", list(pf.FITTING_LIBRARY.keys()), key=f"{key_prefix}_addtype")
    entry = pf.FITTING_LIBRARY[fit_name]
    spec = entry["params"]
    new_values = {}
    param_cols = st.columns(len(spec)) if spec else []
    for (pkey, plabel, wtype, default, extra), col in zip(spec, param_cols):
        with col:
            if wtype == "number":
                new_values[pkey] = st.number_input(plabel, value=default,
                                                     key=f"{key_prefix}_addparam_{fit_name}_{pkey}", **extra)
            else:
                options = extra["options"]
                labels = list(options.keys())
                default_label = next((l for l, v in options.items() if v == default), labels[0])
                chosen_label = st.selectbox(plabel, labels, index=labels.index(default_label),
                                             key=f"{key_prefix}_addparam_{fit_name}_{pkey}")
                new_values[pkey] = options[chosen_label]
    with add_cols[1]:
        qty = st.number_input("Qty", value=1, min_value=1, step=1, key=f"{key_prefix}_addqty")

    if "reducer" in entry:
        rc = st.columns([1.5, 1.5, 1.5])
        with rc[0]:
            reduced = st.checkbox("Reduced port (bore smaller than line size)",
                                   key=f"{key_prefix}_addreduced_{fit_name}")
        d_small_in = None
        if reduced:
            with rc[1]:
                d_small_in = st.number_input("Valve bore / seat (in)", value=round(Di_in * 0.75, 3),
                                              min_value=0.01, max_value=Di_in, step=0.05,
                                              key=f"{key_prefix}_addbore_{fit_name}")
            if entry["reducer"]["has_angle"]:
                with rc[2]:
                    new_values["angle"] = st.number_input("Reducer cone angle (deg)", value=30.0,
                                                            min_value=1.0, max_value=180.0, step=1.0,
                                                            key=f"{key_prefix}_addrangle_{fit_name}")
            else:
                new_values["angle"] = 0.0
        else:
            new_values["angle"] = 0.0
        new_values["d_small_in"] = d_small_in

    with add_cols[3]:
        st.write("")
        st.write("")
        if st.button("Add", key=f"{key_prefix}_addbtn"):
            fittings_list.append({
                "row_id": next(id_counter),
                "name": fit_name, "qty": qty, "values": new_values,
            })
            st.rerun()


def render_fitting_list(key_prefix: str, fittings_list: list) -> None:
    """Render the list of already-added fittings with per-row remove buttons."""
    if not fittings_list:
        st.caption("No fittings added yet.")
        return
    for j, frow in enumerate(fittings_list):
        rc = st.columns([3, 1, 1])
        display = dict(frow["values"])
        if display.get("d_small_in") is None:
            display.pop("d_small_in", None)
            display.pop("angle", None) if "reducer" in pf.FITTING_LIBRARY[frow["name"]] else None
        param_str = ", ".join(f"{k}={v}" for k, v in display.items())
        label = frow["name"]
        if frow["values"].get("d_small_in"):
            label += f"  (reduced port, {frow['values']['d_small_in']:.3f} in bore)"
        rc[0].write(label + (f"  _(({param_str}))_" if param_str else ""))
        rc[1].write(f"qty: {frow['qty']}")
        if rc[2].button("Remove", key=f"{key_prefix}_rmfit_{frow['row_id']}"):
            fittings_list.pop(j)
            st.rerun()
