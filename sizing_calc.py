"""Flow-meter (orifice/nozzle) and control-valve sizing, all English units in/out.

Wraps Caleb Bell's ``fluids.flow_meter`` (differential-pressure meters -
orifice plates and nozzles, per ISO 5167 / ISO 15377 / Hollingshead) and
``fluids.control_valve`` (IEC 60534 control valve sizing), matching the
Crane TP-410 worked examples at
https://fluids.readthedocs.io/Examples/Crane%20TP%20410%20Solved%20Problems/ :
7.23, 7.24, 7.29 (orifice meters, including laminar/low-Re service),
7.30 (nozzle sizing), 7.27 (control valve sizing for liquid service).

No Streamlit here - see pages/2_Sizing.py for the UI.
"""

import math

import fluids.flow_meter as fm
import fluids.control_valve as cv
import fluids.fittings as _fit
from iapws.iapws97 import IAPWS97, Pc as _WATER_PC_MPA

import pipe_flow_calc as pf
import gas_flow_calc as gc

WATER_PC_PSIA = pf.pa_to_psi(_WATER_PC_MPA * 1e6)


def water_psat_psia(T_F: float) -> float:
    """Saturation pressure of water at T_F, psia."""
    T_K = pf.degF_to_K(T_F)
    w = IAPWS97(T=T_K, x=0.0)
    return pf.pa_to_psi(w.P * 1e6)

# ---------------------------------------------------------------------------
# Differential-pressure flow meters (orifice plates and nozzles)
# ---------------------------------------------------------------------------

METER_TYPES = {
    "ISO 5167 orifice (standard, most common)": "ISO 5167 orifice",
    "Hollingshead orifice (extended Re range, incl. laminar)": "Hollingshead orifice",
    "Conical orifice (low Re / viscous service)": "conical orifice",
    "Quarter-circle orifice (low Re / viscous service)": "quarter circle orifice",
    "Eccentric orifice (dirty/wet service)": "eccentric orifice",
    "Segmental orifice (dirty/wet, two-phase service)": "segmental orifice",
    "Long-radius nozzle": "long radius nozzle",
    "Venturi nozzle": "venturi nozzle",
    "ISA 1932 nozzle": "ISA 1932 nozzle",
}

ORIFICE_METER_TYPES = {"ISO 5167 orifice", "Hollingshead orifice", "conical orifice",
                        "quarter circle orifice", "eccentric orifice", "segmental orifice"}

TAPS_OPTIONS = {
    "Corner": "corner",
    "D and D/2 (1D upstream, 1/2D downstream)": "D and D/2",
    "Flange": "flange",
    "Pipe (2.5D upstream, 8D downstream)": "pipe",
    "Vena contracta": "vena contracta",
}


def solve_meter(D_in: float, rho_lbft3: float, mu_cP: float, k: float,
                 D2_in: float | None, P1_psia: float | None, P2_psia: float | None, m_lbhr: float | None,
                 meter_type: str, taps: str, solve_for: str):
    """Solve a differential-pressure flow meter for whichever of D2/P1/P2/m is unknown."""
    D_m = pf.inch_to_m(D_in)
    rho_kgm3 = pf.lbft3_to_kgm3(rho_lbft3)
    mu_pas = pf.cP_to_pas(mu_cP)
    D2_m = pf.inch_to_m(D2_in) if D2_in is not None else None
    P1_pa = pf.psi_to_pa(P1_psia) if P1_psia is not None else None
    P2_pa = pf.psi_to_pa(P2_psia) if P2_psia is not None else None
    m_kgs = pf.lbhr_to_kgs(m_lbhr) if m_lbhr is not None else None

    taps_arg = taps if meter_type in ORIFICE_METER_TYPES else None

    result = fm.differential_pressure_meter_solver(
        D=D_m, rho=rho_kgm3, mu=mu_pas, k=k, D2=D2_m, P1=P1_pa, P2=P2_pa, m=m_kgs,
        meter_type=meter_type, taps=taps_arg)

    if solve_for == "D2":
        D2_m = result
    elif solve_for == "P1":
        P1_pa = result
    elif solve_for == "P2":
        P2_pa = result
    elif solve_for == "m":
        m_kgs = result

    C, epsilon = fm.differential_pressure_meter_C_epsilon(
        D=D_m, D2=D2_m, m=m_kgs, P1=P1_pa, P2=P2_pa, rho=rho_kgm3, mu=mu_pas, k=k,
        meter_type=meter_type, taps=taps_arg)
    flow_coef = fm.flow_coefficient(D_m, D2_m, C)

    A_pipe = math.pi / 4.0 * D_m ** 2
    V_pipe_ms = m_kgs / (rho_kgm3 * A_pipe)
    Re_pipe = rho_kgm3 * V_pipe_ms * D_m / mu_pas

    nprd_pa = fm.differential_pressure_meter_dP(D=D_m, D2=D2_m, P1=P1_pa, P2=P2_pa, C=C, meter_type=meter_type)

    return {
        "D2_in": pf.m_to_inch(D2_m),
        "beta": D2_m / D_m,
        "P1_psia": pf.pa_to_psi(P1_pa),
        "P2_psia": pf.pa_to_psi(P2_pa),
        "dP_psi": pf.pa_to_psi(P1_pa) - pf.pa_to_psi(P2_pa),
        "m_lbhr": pf.kgs_to_lbhr(m_kgs),
        "Q_gpm": pf.m3s_to_gpm(m_kgs / rho_kgm3),
        "V_pipe_fts": pf.ms_to_fts(V_pipe_ms),
        "Re_pipe": Re_pipe,
        "C": C,
        "epsilon": epsilon,
        "flow_coefficient": flow_coef,
        "nprd_psi": pf.pa_to_psi(nprd_pa),
    }


# ---------------------------------------------------------------------------
# Control valve sizing (IEC 60534)
# ---------------------------------------------------------------------------

def solve_control_valve_liquid(rho_lbft3: float, Psat_psia: float, Pc_psia: float, mu_cP: float,
                                P1_psia: float, P2_psia: float, Q_gpm: float,
                                D1_in: float | None, D2_in: float | None, d_in: float | None,
                                FL: float, Fd: float):
    rho = pf.lbft3_to_kgm3(rho_lbft3)
    Psat = pf.psi_to_pa(Psat_psia)
    Pc = pf.psi_to_pa(Pc_psia)
    mu = pf.cP_to_pas(mu_cP)
    P1 = pf.psi_to_pa(P1_psia)
    P2 = pf.psi_to_pa(P2_psia)
    Q = pf.gpm_to_m3s(Q_gpm)
    D1 = pf.inch_to_m(D1_in) if D1_in else None
    D2 = pf.inch_to_m(D2_in) if D2_in else None
    d = pf.inch_to_m(d_in) if d_in else None

    out = cv.size_control_valve_l(rho=rho, Psat=Psat, Pc=Pc, mu=mu, P1=P1, P2=P2, Q=Q,
                                   D1=D1, D2=D2, d=d, FL=FL, Fd=Fd,
                                   allow_choked=True, allow_laminar=True, full_output=True)
    Kv = out["Kv"]
    P2_choke_pa = cv.control_valve_choke_P_l(Psat=Psat, Pc=Pc, FL=FL, P1=P1)
    return {
        "Kv": Kv,
        "Cv": cv.Kv_to_Cv(Kv),
        "choked": out.get("choked"),
        "laminar": out.get("laminar"),
        "Rev": out.get("Rev"),
        "FL": out.get("FL"),
        "FLP": out.get("FLP"),
        "FR": out.get("FR"),
        "FP": out.get("FP"),
        "P2_choke_psia": pf.pa_to_psi(P2_choke_pa),
    }


def solve_control_valve_gas(MW_gmol: float, T_F: float, mu_cP: float, gamma: float, Z: float,
                             P1_psia: float, P2_psia: float, Q_scfh: float, Ts_F: float, Ps_psia: float,
                             D1_in: float | None, D2_in: float | None, d_in: float | None,
                             FL: float, Fd: float, xT: float):
    """Q_scfh is referenced to Ts_F/Ps_psia; internally converted to the
    272.15 K / 1 atm reference fluids.control_valve.size_control_valve_g requires.
    """
    m_lbhr = gc.std_volumetric_to_lbhr(Q_scfh, steam=False, MW_gmol=MW_gmol, Z=Z, Ts_F=Ts_F, Ps_psia=Ps_psia)
    m_kgs = pf.lbhr_to_kgs(m_lbhr)

    T_K = pf.degF_to_K(T_F)
    mu = pf.cP_to_pas(mu_cP)
    P1 = pf.psi_to_pa(P1_psia)
    P2 = pf.psi_to_pa(P2_psia)
    D1 = pf.inch_to_m(D1_in) if D1_in else None
    D2 = pf.inch_to_m(D2_in) if D2_in else None
    d = pf.inch_to_m(d_in) if d_in else None

    rho_ref_kgm3 = pf.lbft3_to_kgm3(gc.ideal_gas_density_lbft3(P_psia=14.696, T_F=32.0, MW_gmol=MW_gmol, Z=1.0))
    Q_ref_m3s = m_kgs / rho_ref_kgm3

    out = cv.size_control_valve_g(T=T_K, MW=MW_gmol, mu=mu, gamma=gamma, Z=Z, P1=P1, P2=P2, Q=Q_ref_m3s,
                                   D1=D1, D2=D2, d=d, FL=FL, Fd=Fd, xT=xT,
                                   allow_choked=True, allow_laminar=True, full_output=True)
    Kv = out["Kv"]
    P2_choke_pa = cv.control_valve_choke_P_g(xT=xT, gamma=gamma, P1=P1)
    return {
        "Kv": Kv,
        "Cv": cv.Kv_to_Cv(Kv),
        "choked": out.get("choked"),
        "laminar": out.get("laminar"),
        "Rev": out.get("Rev"),
        "FL": out.get("FL"),
        "Y": out.get("Y"),
        "m_lbhr": m_lbhr,
        "P2_choke_psia": pf.pa_to_psi(P2_choke_pa),
    }


# ---------------------------------------------------------------------------
# NPSH available
# ---------------------------------------------------------------------------

def npsh_available(P_source_psia: float, Psat_psia: float, rho_lbft3: float,
                    elevation_diff_ft: float, friction_loss_ft: float) -> float:
    """NPSHa (ft): source pressure minus vapor pressure, converted to head, less
    the elevation the pump sits above the source liquid surface and suction
    friction losses. `elevation_diff_ft` is pump centerline minus source
    liquid-surface elevation (positive if the pump sits above the source).
    """
    head_from_pressure_ft = (P_source_psia - Psat_psia) * 144.0 / rho_lbft3
    return head_from_pressure_ft - elevation_diff_ft - friction_loss_ft


# ---------------------------------------------------------------------------
# Pump affinity rules
# ---------------------------------------------------------------------------

def pump_affinity(Q1_gpm: float, H1_ft: float, power1_hp: float, ratio: float):
    """ratio = N2/N1 (speed) or D2/D1 (impeller trim)."""
    return {
        "Q2_gpm": Q1_gpm * ratio,
        "H2_ft": H1_ft * ratio ** 2,
        "power2_hp": power1_hp * ratio ** 3,
    }


# ---------------------------------------------------------------------------
# Pump operating cost
# ---------------------------------------------------------------------------

def pump_operating_cost(Q_gpm: float, head_ft: float, rho_lbft3: float, pump_efficiency: float,
                         motor_efficiency: float, drive_efficiency: float,
                         electricity_rate_per_kwh: float, hours_per_year: float):
    bhp = pf.brake_horsepower(Q_gpm, head_ft, rho_lbft3, pump_efficiency)
    total_efficiency = pump_efficiency * motor_efficiency * drive_efficiency
    electrical_hp = pf.brake_horsepower(Q_gpm, head_ft, rho_lbft3, total_efficiency)
    electrical_kw = electrical_hp * 0.7456998715822701
    annual_cost = electrical_kw * hours_per_year * electricity_rate_per_kwh
    return {
        "bhp": bhp,
        "electrical_hp": electrical_hp,
        "electrical_kw": electrical_kw,
        "annual_cost": annual_cost,
    }


# ---------------------------------------------------------------------------
# Tee / wye branch flow (Crane converging/diverging branch formulas)
# ---------------------------------------------------------------------------


def solve_tee_branch(D_run_in: float, D_branch_in: float, Q_run_gpm: float, Q_branch_gpm: float,
                      angle: float, converging: bool, rho_lbft3: float):
    """K and head loss for each leg of a converging tee or diverging wye.

    For a converging tee, Q_run/Q_branch are the flows in each leg *before*
    they merge. For a diverging wye, they are the flows in each leg *after*
    the split. Either way the reference velocity for both legs' head loss is
    the combined flow through the run pipe's cross-section (Crane convention).
    """
    D_run = pf.inch_to_m(D_run_in)
    D_branch = pf.inch_to_m(D_branch_in)
    Q_run = pf.gpm_to_m3s(Q_run_gpm)
    Q_branch = pf.gpm_to_m3s(Q_branch_gpm)
    rho_kgm3 = pf.lbft3_to_kgm3(rho_lbft3)

    A_run = math.pi / 4.0 * D_run ** 2
    V_combined_ms = (Q_run + Q_branch) / A_run

    if converging:
        K_branch = _fit.K_branch_converging_Crane(D_run=D_run, D_branch=D_branch, Q_run=Q_run,
                                                    Q_branch=Q_branch, angle=angle)
        K_run = _fit.K_run_converging_Crane(D_run=D_run, D_branch=D_branch, Q_run=Q_run,
                                             Q_branch=Q_branch, angle=angle)
    else:
        K_branch = _fit.K_branch_diverging_Crane(D_run=D_run, D_branch=D_branch, Q_run=Q_run,
                                                   Q_branch=Q_branch, angle=angle)
        K_run = _fit.K_run_diverging_Crane(D_run=D_run, D_branch=D_branch, Q_run=Q_run,
                                            Q_branch=Q_branch, angle=angle)

    V_combined_fts = pf.ms_to_fts(V_combined_ms)
    h_branch_ft = K_branch * V_combined_fts ** 2 / (2 * pf.G)
    h_run_ft = K_run * V_combined_fts ** 2 / (2 * pf.G)

    return {
        "V_combined_fts": V_combined_fts,
        "K_branch": K_branch,
        "K_run": K_run,
        "h_branch_ft": h_branch_ft,
        "h_run_ft": h_run_ft,
        "dP_branch_psi": h_branch_ft * rho_lbft3 / 144.0,
        "dP_run_psi": h_run_ft * rho_lbft3 / 144.0,
    }
