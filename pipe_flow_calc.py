"""Pipe flow / head-loss calculation engine, all English units in and out.

Wraps Caleb Bell's ``fluids`` library (Crane TP-410 methods for fittings,
valves, reducers, and pipe schedule/material lookups) plus ``iapws`` for
water properties. Unit conversion between English units and the SI units
``fluids`` expects is done with ``fluids.units.u`` (a pint UnitRegistry),
per https://fluids.readthedocs.io/fluids.units.html.

No Streamlit here - this module is plain Python so it can be tested or
reused on its own. See pipe_flow_app.py for the Streamlit UI built on top
of it.
"""

import math

from fluids.units import u
import fluids.friction as friction
import fluids.piping as piping
import fluids.fittings as fit
from fluids import L_equiv_from_K
from iapws import IAPWS97

G = 32.174  # ft/s^2, standard gravity

# ---------------------------------------------------------------------------
# Unit conversions (English <-> SI) via fluids' own pint registry
# ---------------------------------------------------------------------------

def gpm_to_m3s(v):
    return (v * u.gallon / u.minute).to(u.m ** 3 / u.s).magnitude

def cfh_to_m3s(v):
    return (v * u.foot ** 3 / u.hour).to(u.m ** 3 / u.s).magnitude

def cfm_to_m3s(v):
    return (v * u.foot ** 3 / u.minute).to(u.m ** 3 / u.s).magnitude

def lbhr_to_m3s(v, rho_lbft3):
    mass_flow = (v * u.lb / u.hour).to(u.kg / u.s).magnitude
    rho_kgm3 = lbft3_to_kgm3(rho_lbft3)
    return mass_flow / rho_kgm3

def bblhr_to_m3s(v):
    return (v * u.oil_barrel / u.hour).to(u.m ** 3 / u.s).magnitude

def m3s_to_gpm(v):
    return (v * u.m ** 3 / u.s).to(u.gallon / u.minute).magnitude

def lbhr_to_kgs(v):
    return (v * u.lb / u.hour).to(u.kg / u.s).magnitude

def kgs_to_lbhr(v):
    return (v * u.kg / u.s).to(u.lb / u.hour).magnitude

def mile_to_m(v):
    return (v * u.mile).to(u.m).magnitude

def m3s_to_scfh(v):
    """Pure volumetric conversion; "standard" just describes what the m3/s represents."""
    return (v * u.m ** 3 / u.s).to(u.foot ** 3 / u.hour).magnitude

def inch_to_m(v):
    return (v * u.inch).to(u.m).magnitude

def m_to_inch(v):
    return (v * u.m).to(u.inch).magnitude

def ft_to_m(v):
    return (v * u.foot).to(u.m).magnitude

def m_to_ft(v):
    return (v * u.m).to(u.foot).magnitude

def lbft3_to_kgm3(v):
    return (v * u.lb / u.foot ** 3).to(u.kg / u.m ** 3).magnitude

def kgm3_to_lbft3(v):
    return (v * u.kg / u.m ** 3).to(u.lb / u.foot ** 3).magnitude

def cP_to_pas(v):
    return (v * u.centipoise).to(u.pascal * u.second).magnitude

def pas_to_cP(v):
    return (v * u.pascal * u.second).to(u.centipoise).magnitude

def ms_to_fts(v):
    return (v * u.m / u.s).to(u.foot / u.s).magnitude

def psi_to_pa(v):
    return (v * u.psi).to(u.pascal).magnitude

def pa_to_psi(v):
    return (v * u.pascal).to(u.psi).magnitude

def degF_to_K(v):
    return u.Quantity(v, u.degF).to(u.kelvin).magnitude

def hp_to_btuhr(v):
    return (v * u.horsepower).to(u.BTU / u.hour).magnitude

def hp_to_kw(v):
    return (v * u.horsepower).to(u.kilowatt).magnitude


# ---------------------------------------------------------------------------
# Pipe / material data
# ---------------------------------------------------------------------------

NPS_OPTIONS = piping.NPS40  # standard nominal pipe sizes, inch

SCHEDULE_OPTIONS = [
    "5", "10", "20", "30", "40", "60", "80", "100", "120", "140", "160",
    "STD", "XS", "XXS", "5S", "10S", "40S", "80S",
]

# Curated pipe-relevant materials from fluids.friction (clean, new pipe).
MATERIAL_OPTIONS = sorted(friction.roughness_clean_names) + [
    "PVC / Plastic (smooth)",
    "Custom",
]

_PVC_ROUGHNESS_FT = 0.0000015  # ft, standard published value for smooth plastic pipe


def material_roughness_ft(material: str, custom_roughness_in: float = 0.0) -> float:
    """Roughness for a material name, in feet."""
    if material == "Custom":
        return custom_roughness_in / 12.0
    if material == "PVC / Plastic (smooth)":
        return _PVC_ROUGHNESS_FT
    roughness_m = friction.material_roughness(material)
    return m_to_ft(roughness_m)


def pipe_geometry_in(nps: float, schedule: str):
    """Return (NPS, Di_in, Do_in, wall_thickness_in) for a nominal pipe size/schedule."""
    NPS, Di_m, Do_m, t_m = piping.nearest_pipe(NPS=nps, schedule=schedule)
    return NPS, m_to_inch(Di_m), m_to_inch(Do_m), m_to_inch(t_m)


_NPS_FRACTION_LABELS = {0.125: '1/8"', 0.25: '1/4"', 0.375: '3/8"', 0.5: '1/2"', 0.75: '3/4"',
                         1.25: '1-1/4"', 1.5: '1-1/2"', 2.5: '2-1/2"', 3.5: '3-1/2"'}


def format_nps(v: float) -> str:
    if v in _NPS_FRACTION_LABELS:
        return _NPS_FRACTION_LABELS[v]
    if float(v).is_integer():
        return f'{int(v)}"'
    return f'{v}"'


# ---------------------------------------------------------------------------
# Water properties (IAPWS-97), English units in and out
# ---------------------------------------------------------------------------

def water_properties(temp_F: float, pressure_psia: float):
    """Return (rho_lbft3, mu_cP, phase) for water at temp_F / pressure_psia."""
    T_K = degF_to_K(temp_F)
    P_MPa = psi_to_pa(pressure_psia) / 1e6
    w = IAPWS97(T=T_K, P=P_MPa)
    rho_lbft3 = kgm3_to_lbft3(w.rho)
    mu_cP = pas_to_cP(w.mu)
    return rho_lbft3, mu_cP, w.phase


# ---------------------------------------------------------------------------
# Fitting K-value registry
#
# Each entry maps a UI-facing fitting name to the function used to compute
# its resistance coefficient K, plus a spec of any extra parameters the UI
# needs to collect. All functions take the *segment* context (Di_m, fd_t,
# Re, roughness_m) plus whatever extra params are listed, and return K
# referenced to that segment's own pipe diameter (i.e. no reducer inside
# the fitting itself - use a Transition between segments for that).
# ---------------------------------------------------------------------------

def _k_elbow_bend(ctx, angle, rd):
    # Pass our own (laminar-safe) fd directly rather than letting bend_rounded
    # recompute it from Re via Clamond, which throws a math domain error at
    # the very low Re reached with high-viscosity fluids.
    return fit.bend_rounded(Di=ctx["Di_m"], angle=angle, bend_diameters=rd, fd=ctx["fd"])

def _k_miter_bend(ctx, angle):
    return fit.bend_miter(angle=angle, Di=ctx["Di_m"], Re=ctx["Re"],
                           roughness=ctx["roughness_m"])

def _k_tee_run(ctx):
    return 20.0 * ctx["fd_t"]

def _k_tee_branch(ctx):
    return 60.0 * ctx["fd_t"]

def _k_gate_valve(ctx, d_small_in, angle):
    if d_small_in:
        return fit.K_gate_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], angle=angle, fd=ctx["fd"])
    return fit.K_gate_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"], angle=0.0)

def _k_globe_valve(ctx, d_small_in):
    if d_small_in:
        return fit.K_globe_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], fd=ctx["fd"])
    return fit.K_globe_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"])

def _k_ball_valve(ctx, d_small_in, angle):
    if d_small_in:
        return fit.K_ball_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], angle=angle, fd=ctx["fd"])
    return fit.K_ball_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"], angle=0.0)

def _k_butterfly_valve(ctx, style):
    return fit.K_butterfly_valve_Crane(D=ctx["Di_m"], style=style)

def _k_swing_check(ctx, angled):
    return fit.K_swing_check_valve_Crane(D=ctx["Di_m"], angled=angled)

def _k_lift_check(ctx, angled, d_small_in):
    if d_small_in:
        return fit.K_lift_check_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], angled=angled, fd=ctx["fd"])
    return fit.K_lift_check_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"], angled=angled)

def _k_angle_valve(ctx, style, d_small_in):
    if d_small_in:
        return fit.K_angle_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], style=style, fd=ctx["fd"])
    return fit.K_angle_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"], style=style)

def _k_plug_valve(ctx, style, d_small_in, angle):
    if d_small_in:
        return fit.K_plug_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], angle=angle, style=style,
                                       fd=ctx["fd"])
    return fit.K_plug_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"], angle=0.0, style=style)

def _k_diaphragm_valve(ctx, style):
    return fit.K_diaphragm_valve_Crane(D=ctx["Di_m"], style=style)

def _k_foot_valve(ctx, style):
    return fit.K_foot_valve_Crane(D=ctx["Di_m"], style=style)

def _k_tilting_disk_check(ctx, angle):
    return fit.K_tilting_disk_check_valve_Crane(D=ctx["Di_m"], angle=angle)

def _k_angle_stop_check(ctx, style, d_small_in):
    if d_small_in:
        return fit.K_angle_stop_check_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], style=style,
                                                    fd=ctx["fd"])
    return fit.K_angle_stop_check_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"], style=style)

def _k_globe_stop_check(ctx, style, d_small_in):
    if d_small_in:
        return fit.K_globe_stop_check_valve_Crane(D1=inch_to_m(d_small_in), D2=ctx["Di_m"], style=style,
                                                    fd=ctx["fd"])
    return fit.K_globe_stop_check_valve_Crane(D1=ctx["Di_m"], D2=ctx["Di_m"], style=style)

def _k_entrance_sharp(ctx):
    return fit.entrance_sharp()

def _k_entrance_rounded(ctx, rc_in):
    return fit.entrance_rounded(Di=ctx["Di_m"], rc=inch_to_m(rc_in))

def _k_entrance_beveled(ctx, l_in, angle):
    return fit.entrance_beveled(Di=ctx["Di_m"], l=inch_to_m(l_in), angle=angle)

def _k_entrance_angled(ctx, angle):
    return fit.entrance_angled(angle=angle)

def _k_entrance_reentrant(ctx):
    return 0.78  # standard published constant; fluids has no dedicated function

def _k_exit(ctx):
    return fit.exit_normal()

def _k_custom_valve(ctx, coeff_type, coeff_value):
    if coeff_type == "Kv":
        return fit.Kv_to_K(Kv=coeff_value, D=ctx["Di_m"])
    return fit.Cv_to_K(Cv=coeff_value, D=ctx["Di_m"])


FITTING_LIBRARY = {
    "Elbow / Bend (rounded)": {
        "func": _k_elbow_bend,
        "params": [
            ("angle", "Bend angle (deg)", "number", 90.0, dict(min_value=1.0, max_value=180.0, step=1.0)),
            ("rd", "Bend radius / pipe ID, r/D  (1.0=standard/short-rad, 1.5=long-rad)", "number", 1.5,
             dict(min_value=0.5, max_value=20.0, step=0.1)),
        ],
    },
    "Miter Bend": {
        "func": _k_miter_bend,
        "params": [
            ("angle", "Bend angle (deg)", "number", 90.0, dict(min_value=1.0, max_value=180.0, step=1.0)),
        ],
    },
    "Tee - Flow Through Run": {"func": _k_tee_run, "params": []},
    "Tee - Flow Through Branch": {"func": _k_tee_branch, "params": []},
    "Gate Valve": {"func": _k_gate_valve, "params": [], "reducer": {"has_angle": True}},
    "Globe Valve": {"func": _k_globe_valve, "params": [], "reducer": {"has_angle": False}},
    "Ball Valve": {"func": _k_ball_valve, "params": [], "reducer": {"has_angle": True}},
    "Butterfly Valve": {
        "func": _k_butterfly_valve,
        "params": [
            ("style", "Disc type", "select", 0,
             dict(options={"Centric / concentric": 0, "Double offset": 1, "Triple offset": 2})),
        ],
    },
    "Swing Check Valve": {
        "func": _k_swing_check,
        "params": [
            ("angled", "Body type", "select", False,
             dict(options={"Straight (inline)": False, "Angled body": True})),
        ],
    },
    "Lift Check Valve": {
        "func": _k_lift_check,
        "params": [
            ("angled", "Body type", "select", False,
             dict(options={"Straight, 90 deg (globe-lift)": False, "Angled, 45 deg (angle-lift)": True})),
        ],
        "reducer": {"has_angle": False},
    },
    "Angle Valve": {
        "func": _k_angle_valve,
        "params": [
            ("style", "Style", "select", 0,
             dict(options={"Style 0 (N=55·fd)": 0, "Style 1 (N=150·fd)": 1, "Style 2 (N=55·fd)": 2})),
        ],
        "reducer": {"has_angle": False},
    },
    "Plug Valve": {
        "func": _k_plug_valve,
        "params": [
            ("style", "Type", "select", 0, dict(options={
                "Straight-through (N=18·fd)": 0,
                "3-way, straight-through flow (N=30·fd)": 1,
                "3-way, 90° flow (N=90·fd)": 2,
            })),
        ],
        "reducer": {"has_angle": True},
    },
    "Diaphragm Valve": {
        "func": _k_diaphragm_valve,
        "params": [
            ("style", "Type", "select", 0,
             dict(options={"Weir type (N=149·fd)": 0, "Straight-through (N=39·fd)": 1})),
        ],
    },
    "Foot Valve (w/ strainer)": {
        "func": _k_foot_valve,
        "params": [
            ("style", "Disc type", "select", 0,
             dict(options={"Poppet disc (N=420·fd)": 0, "Hinged disc (N=75·fd)": 1})),
        ],
    },
    "Tilting-Disk Check Valve": {
        "func": _k_tilting_disk_check,
        "params": [
            ("angle", "Disk tilt angle (deg)", "select", 15, dict(options={"5": 5, "15": 15})),
        ],
    },
    "Angle Stop-Check Valve": {
        "func": _k_angle_stop_check,
        "params": [
            ("style", "Style", "select", 0, dict(options={
                "Standard (N=200·fd)": 0,
                "Restricted, flow forced up (N=350·fd)": 1,
                "Clearest flow area, no guides (N=55·fd)": 2,
            })),
        ],
        "reducer": {"has_angle": False},
    },
    "Globe Stop-Check Valve": {
        "func": _k_globe_stop_check,
        "params": [
            ("style", "Style", "select", 0, dict(options={
                "Standard (N=400·fd)": 0,
                "Angled, restricted (N=300·fd)": 1,
                "Angled, smaller restriction (N=55·fd)": 2,
            })),
        ],
        "reducer": {"has_angle": False},
    },
    "Pipe Entrance - Sharp": {"func": _k_entrance_sharp, "params": []},
    "Pipe Entrance - Rounded": {
        "func": _k_entrance_rounded,
        "params": [("rc_in", "Corner radius (in)", "number", 0.25, dict(min_value=0.0, max_value=12.0, step=0.05))],
    },
    "Pipe Entrance - Beveled": {
        "func": _k_entrance_beveled,
        "params": [
            ("l_in", "Bevel length (in)", "number", 0.5, dict(min_value=0.0, max_value=24.0, step=0.05)),
            ("angle", "Bevel angle (deg)", "number", 45.0, dict(min_value=0.0, max_value=90.0, step=1.0)),
        ],
    },
    "Pipe Entrance - Angled": {
        "func": _k_entrance_angled,
        "params": [("angle", "Entrance angle from pipe axis (deg)", "number", 45.0,
                     dict(min_value=0.0, max_value=90.0, step=1.0))],
    },
    "Pipe Entrance - Re-entrant / Projecting": {"func": _k_entrance_reentrant, "params": []},
    "Pipe Exit": {"func": _k_exit, "params": []},
    "Custom Valve (by Kv or Cv rating)": {
        "func": _k_custom_valve,
        "params": [
            ("coeff_type", "Rating type", "select", "Cv", dict(options={"Cv (US gpm basis)": "Cv", "Kv (m3/hr basis)": "Kv"})),
            ("coeff_value", "Rated Cv or Kv", "number", 100.0, dict(min_value=0.01, step=1.0)),
        ],
    },
}


def equivalent_length_L_over_D(K: float, fd: float) -> float:
    """Equivalent length in pipe diameters (L/D) that gives the same K at friction factor fd."""
    return L_equiv_from_K(K=K, fd=fd)


# Check-valve-family fittings with an unambiguous mapping to Crane's minimum
# full-lift velocity styles (fluids.fittings.v_lift_valve_Crane). Types with
# an ambiguous style mapping (tilting-disk, stop-check) are intentionally
# left out rather than guessed at.
_LIFT_VELOCITY_STYLES = {
    "Swing Check Valve": lambda values: "swing check angled" if values.get("angled") else "swing check straight",
    "Lift Check Valve": lambda values: "lift check angled" if values.get("angled") else "lift check straight",
    "Foot Valve (w/ strainer)": lambda values: "foot valve poppet disc" if values.get("style") == 0
                                                 else "foot valve hinged disc",
}


def min_lift_velocity_fts(fitting_name: str, values: dict, ctx: dict, rho_lbft3: float) -> float | None:
    """Minimum velocity (ft/s) to keep a check/foot valve disc fully, stably lifted.

    Returns None if this fitting type has no unambiguous style mapping.
    """
    style_fn = _LIFT_VELOCITY_STYLES.get(fitting_name)
    if style_fn is None:
        return None
    style = style_fn(values)
    rho_kgm3 = lbft3_to_kgm3(rho_lbft3)
    d_small_in = values.get("d_small_in")
    D1_m = inch_to_m(d_small_in) if d_small_in else ctx["Di_m"]
    v_min_ms = fit.v_lift_valve_Crane(rho=rho_kgm3, D1=D1_m, D2=ctx["Di_m"], style=style)
    return ms_to_fts(v_min_ms)


def fitting_K(name: str, ctx: dict, values: dict) -> float:
    entry = FITTING_LIBRARY[name]
    kwargs = {p[0]: values[p[0]] for p in entry["params"]}
    if "reducer" in entry:
        kwargs["d_small_in"] = values.get("d_small_in") or None
        if entry["reducer"]["has_angle"]:
            kwargs["angle"] = values.get("angle", 0.0)
    return entry["func"](ctx, **kwargs)


# ---------------------------------------------------------------------------
# Reducer / enlargement (transition between two pipe segments)
# ---------------------------------------------------------------------------

def transition_K(D1_m, D2_m, kind: str, angle: float, roughness_m: float, fd: float | None, Re: float | None):
    """K for a reducer (D1>D2) or enlargement (D1<D2) between two segments.

    Referenced to the smaller of the two diameters (matches fluids' own
    convention for both contraction_conical and diffuser_conical - K is
    always given in terms of the smaller-bore pipe's velocity).
    """
    if D1_m == D2_m:
        return 0.0
    contracting = D2_m < D1_m
    if kind == "sudden":
        if contracting:
            return fit.contraction_sharp(Di1=D1_m, Di2=D2_m, fd=fd, Re=Re, roughness=roughness_m)
        else:
            return fit.diffuser_sharp(Di1=D1_m, Di2=D2_m, fd=fd, Re=Re, roughness=roughness_m)
    else:  # gradual (conical)
        if contracting:
            return fit.contraction_conical(Di1=D1_m, Di2=D2_m, angle=angle, fd=fd, Re=Re, roughness=roughness_m)
        else:
            return fit.diffuser_conical(Di1=D1_m, Di2=D2_m, angle=angle, fd=fd, Re=Re, roughness=roughness_m)


# ---------------------------------------------------------------------------
# Segment (a run of one pipe size, with its own fittings) and system solve
# ---------------------------------------------------------------------------

def solve_segment(Di_in: float, length_ft: float, roughness_ft: float, Q_m3s: float,
                   rho_lbft3: float, mu_cP: float, fittings: list):
    """Compute velocity, Re, friction factor, and head loss for one pipe segment.

    fittings: list of (name, quantity, values-dict) tuples.
    Returns a dict of results, all in English units, plus the raw ctx dict
    (SI) so transitions to neighboring segments can reuse Re/roughness/fd.
    """
    Di_m = inch_to_m(Di_in)
    roughness_m = ft_to_m(roughness_ft)
    A_m2 = math.pi / 4.0 * Di_m ** 2
    V_ms = Q_m3s / A_m2
    rho_kgm3 = lbft3_to_kgm3(rho_lbft3)
    mu_pas = cP_to_pas(mu_cP)
    Re = rho_kgm3 * V_ms * Di_m / mu_pas
    eD = roughness_m / Di_m
    fd = friction.friction_factor(Re=Re, eD=eD)
    fd_t = fit.ft_Crane(Di_m)

    K_pipe = fd * ft_to_m(length_ft) / Di_m

    ctx = {"Di_m": Di_m, "Re": Re, "roughness_m": roughness_m, "fd": fd, "fd_t": fd_t}

    fitting_rows = []
    K_fittings = 0.0
    for name, qty, values in fittings:
        k_each = fitting_K(name, ctx, values)
        k_total = k_each * qty
        K_fittings += k_total
        fitting_rows.append({"name": name, "qty": qty, "values": values, "K_each": k_each, "K_total": k_total})

    K_total = K_pipe + K_fittings
    V_fts = ms_to_fts(V_ms)
    h_loss_ft = K_total * V_fts ** 2 / (2 * G)

    return {
        "Di_in": Di_in,
        "V_fts": V_fts,
        "Re": Re,
        "fd": fd,
        "fd_t": fd_t,
        "eD": eD,
        "K_pipe": K_pipe,
        "K_fittings": K_fittings,
        "K_total": K_total,
        "h_loss_ft": h_loss_ft,
        "fitting_rows": fitting_rows,
        "ctx": ctx,
    }


def solve_transition(seg_a: dict, seg_b: dict, kind: str, angle: float):
    """Head loss for a reducer/enlargement between two already-solved segments."""
    D1_m, D2_m = seg_a["ctx"]["Di_m"], seg_b["ctx"]["Di_m"]
    if D1_m == D2_m:
        return {"K": 0.0, "h_loss_ft": 0.0, "V_ref_fts": 0.0}
    small_seg = seg_a if D1_m < D2_m else seg_b
    roughness_m = small_seg["ctx"]["roughness_m"]
    K = transition_K(D1_m, D2_m, kind, angle, roughness_m, fd=small_seg["fd"], Re=small_seg["ctx"]["Re"])
    V_ref = small_seg["V_fts"]
    h_loss_ft = K * V_ref ** 2 / (2 * G)
    return {"K": K, "h_loss_ft": h_loss_ft, "V_ref_fts": V_ref}


# ---------------------------------------------------------------------------
# Pump power and erosional velocity checks
# ---------------------------------------------------------------------------

def brake_horsepower(Q_gpm: float, head_ft: float, rho_lbft3: float, efficiency: float) -> float:
    Q_m3s = gpm_to_m3s(Q_gpm)
    Q_ft3s = (Q_m3s * u.m ** 3 / u.s).to(u.foot ** 3 / u.s).magnitude
    power_ftlbf_s = rho_lbft3 * Q_ft3s * head_ft
    return power_ftlbf_s / (550.0 * efficiency)


EROSIONAL_C_OPTIONS = {
    "Non-corrosive, continuous service (C=150)": 150,
    "Non-corrosive, intermittent service (C=250)": 250,
    "Corrosive, continuous service (C=100)": 100,
    "Corrosive, intermittent service (C=125)": 125,
}


def erosional_velocity_fts(rho_lbft3: float, C: float) -> float:
    rho_kgm3 = lbft3_to_kgm3(rho_lbft3)
    V_ms = piping.erosional_velocity(rho=rho_kgm3, C=C)
    return ms_to_fts(V_ms)
