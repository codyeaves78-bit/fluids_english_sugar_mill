"""Compressible (gas/steam) flow calculation engine, all English units in/out.

Two models, both from Caleb Bell's ``fluids`` library and matching the
Crane TP-410 worked examples at
https://fluids.readthedocs.io/Examples/Crane%20TP%20410%20Solved%20Problems/ :

- ``solve_plant_piping``: isothermal compressible flow through plant piping
  (one pipe size + fittings/valves), via ``fluids.compressible.isothermal_gas``.
  Matches examples 7.10, 7.16, 7.20, 7.21, 7.22 (steam and air lines, sonic
  velocity / choked flow checks).
- ``solve_pipeline``: long gas transmission pipeline capacity, via the
  Weymouth / Panhandle / Spitzglass / Fritzsche / Oliphant / Muller / IGT
  correlations in ``fluids.compressible``. Matches example 7.18 (natural
  gas pipeline).

Gas density is computed with the ideal gas law (rho = P*MW/(Z*R*T), with an
optional compressibility factor Z as a simple real-gas correction) rather
than a full equation of state - this reproduces the worked examples' final
answers to within ~0.2% without requiring the (heavy) ``thermo``/``chemicals``
packages. Steam uses ``iapws`` (real properties) via pipe_flow_calc's
water_properties, which works for either the liquid or vapor phase.

No Streamlit here - see pages/1_Gas_Flow.py for the UI.
"""

import math

import fluids.compressible as comp
import fluids.friction as friction
import fluids.fittings as fit
from fluids import K_from_f, f_from_K

import pipe_flow_calc as pf

R = comp.R  # J/(mol*K)
AIR_MW = 28.9647  # g/mol

GAS_PRESETS = {
    "Air": 28.9647,
    "Natural gas (typical pipeline gas, MW~19.5)": 19.5,
    "Methane": 16.04,
    "Custom": None,
}


def ideal_gas_density_lbft3(P_psia: float, T_F: float, MW_gmol: float, Z: float = 1.0) -> float:
    P_pa = pf.psi_to_pa(P_psia)
    T_K = pf.degF_to_K(T_F)
    rho_kgm3 = P_pa * (MW_gmol / 1000.0) / (Z * R * T_K)
    return pf.kgm3_to_lbft3(rho_kgm3)


def std_volumetric_to_lbhr(Q_scfh: float, steam: bool, MW_gmol: float, Z: float,
                            Ts_F: float = 60.0, Ps_psia: float = 14.696) -> float:
    """Standard ft3/hr -> mass flow (lb/hr), using density at standard conditions.

    Mass flow is conserved regardless of what pressure/temperature the
    volumetric rate is referenced to, so this only needs the *standard*
    density - not the actual flowing conditions.
    """
    if steam:
        rho_std_lbft3, _, _ = pf.water_properties(Ts_F, Ps_psia)
    else:
        rho_std_lbft3 = ideal_gas_density_lbft3(Ps_psia, Ts_F, MW_gmol, Z)
    return Q_scfh * rho_std_lbft3


# ---------------------------------------------------------------------------
# Plant piping (isothermal_gas), with fittings/valves - single pipe size
# ---------------------------------------------------------------------------

def solve_plant_piping(Di_in: float, length_ft: float, roughness_ft: float, fittings: list,
                        steam: bool, MW_gmol: float, Z: float, mu_cP_input: float, T_F: float,
                        P1_psia: float | None, P2_psia: float | None, m_lbhr: float | None,
                        solve_for: str, iterations: int = 12):
    """Solve isothermal compressible flow through one pipe + fittings.

    Exactly one of P1_psia, P2_psia, m_lbhr should be None; `solve_for` names
    which one ('P1', 'P2', or 'm').
    """
    Di_m = pf.inch_to_m(Di_in)
    roughness_m = pf.ft_to_m(roughness_ft)
    L_m = pf.ft_to_m(length_ft)
    A_m2 = math.pi / 4.0 * Di_m ** 2

    def density_and_visc(P_psia):
        if steam:
            rho_lbft3, mu_cP, phase = pf.water_properties(T_F, P_psia)
            return rho_lbft3, mu_cP, phase
        rho_lbft3 = ideal_gas_density_lbft3(P_psia, T_F, MW_gmol, Z)
        return rho_lbft3, mu_cP_input, "Gas (ideal)"

    P1_pa = pf.psi_to_pa(P1_psia) if P1_psia is not None else None
    P2_pa = pf.psi_to_pa(P2_psia) if P2_psia is not None else None
    m_kgs = pf.lbhr_to_kgs(m_lbhr) if m_lbhr is not None else None

    fd_guess = 0.02
    phase = "Gas (ideal)"
    rho_kgm3 = None
    fd_eff = fd_guess
    K_total = 0.0
    solved = None

    for _ in range(iterations):
        # P1_pa/P2_pa/m_kgs keep exactly one None (the target) for every
        # call - isothermal_gas requires that. The solved value only gets
        # written back in after the loop converges.
        P_ref_psia = P1_psia if P1_psia is not None else P2_psia
        rho_lbft3, mu_cP, phase = density_and_visc(P_ref_psia)
        rho_kgm3 = pf.lbft3_to_kgm3(rho_lbft3)
        mu_pas = pf.cP_to_pas(mu_cP)

        K_pipe = K_from_f(fd=fd_guess, L=L_m, D=Di_m)
        ctx = {"Di_m": Di_m, "Re": None, "roughness_m": roughness_m,
               "fd": fd_guess, "fd_t": fit.ft_Crane(Di_m)}
        K_fittings = sum(pf.fitting_K(name, ctx, values) * qty for name, qty, values in fittings)
        K_total = K_pipe + K_fittings
        fd_eff = f_from_K(K=K_total, L=L_m, D=Di_m)

        try:
            solved = comp.isothermal_gas(rho=rho_kgm3, fd=fd_eff, P1=P1_pa, P2=P2_pa, L=L_m, D=Di_m, m=m_kgs)
        except ValueError:
            Pcf = comp.P_isothermal_critical_flow(P=P1_pa, fd=fd_eff, D=Di_m, L=L_m)
            m_max = comp.isothermal_gas(rho=rho_kgm3, fd=fd_eff, P1=P1_pa, P2=Pcf, L=L_m, D=Di_m, m=None)
            return _choked_result(P1_pa, Pcf, m_max, Di_m, A_m2, T_F, steam, MW_gmol, Z, mu_cP,
                                   solve_for, K_total, fd_eff)

        m_for_re = solved if solve_for == "m" else m_kgs
        v_ref = m_for_re / (rho_kgm3 * A_m2)
        Re = rho_kgm3 * v_ref * Di_m / mu_pas
        fd_guess = friction.friction_factor(Re=Re, eD=roughness_m / Di_m)

    if solve_for == "m":
        m_kgs = solved
    elif solve_for == "P2":
        P2_pa = solved
    elif solve_for == "P1":
        P1_pa = solved

    Pcf = comp.P_isothermal_critical_flow(P=P1_pa, fd=fd_eff, D=Di_m, L=L_m)
    choked = P2_pa <= Pcf

    rho1_lbft3, mu1_cP, _ = density_and_visc(pf.pa_to_psi(P1_pa))
    rho2_lbft3, mu2_cP, _ = density_and_visc(pf.pa_to_psi(P2_pa))
    rho1_kgm3, rho2_kgm3 = pf.lbft3_to_kgm3(rho1_lbft3), pf.lbft3_to_kgm3(rho2_lbft3)
    v1_ms = m_kgs / (rho1_kgm3 * A_m2)
    v2_ms = m_kgs / (rho2_kgm3 * A_m2)
    Re_final = rho1_kgm3 * v1_ms * Di_m / pf.cP_to_pas(mu1_cP)

    return {
        "P1_psia": pf.pa_to_psi(P1_pa),
        "P2_psia": pf.pa_to_psi(P2_pa),
        "dP_psi": pf.pa_to_psi(P1_pa) - pf.pa_to_psi(P2_pa),
        "m_lbhr": pf.kgs_to_lbhr(m_kgs),
        "v1_fts": pf.ms_to_fts(v1_ms),
        "v2_fts": pf.ms_to_fts(v2_ms),
        "rho1_lbft3": rho1_lbft3,
        "rho2_lbft3": rho2_lbft3,
        "Re": Re_final,
        "fd": fd_guess,
        "fd_eff": fd_eff,
        "K_total": K_total,
        "Pcf_psia": pf.pa_to_psi(Pcf),
        "choked": choked,
        "phase": phase,
    }


def _choked_result(P1_pa, Pcf_pa, m_max_kgs, Di_m, A_m2, T_F, steam, MW_gmol, Z, mu_cP, solve_for, K_total, fd_eff):
    """Flow is choked (sonic) at the requested conditions - report the maximum achievable flow."""
    if steam:
        rho1_lbft3, mu1_cP, phase = pf.water_properties(T_F, pf.pa_to_psi(P1_pa))
        rho2_lbft3, mu2_cP, _ = pf.water_properties(T_F, pf.pa_to_psi(Pcf_pa))
    else:
        rho1_lbft3 = ideal_gas_density_lbft3(pf.pa_to_psi(P1_pa), T_F, MW_gmol, Z)
        rho2_lbft3 = ideal_gas_density_lbft3(pf.pa_to_psi(Pcf_pa), T_F, MW_gmol, Z)
        phase = "Gas (ideal)"
    rho1_kgm3, rho2_kgm3 = pf.lbft3_to_kgm3(rho1_lbft3), pf.lbft3_to_kgm3(rho2_lbft3)
    v1_ms = m_max_kgs / (rho1_kgm3 * A_m2)
    v2_ms = m_max_kgs / (rho2_kgm3 * A_m2)
    return {
        "P1_psia": pf.pa_to_psi(P1_pa),
        "P2_psia": pf.pa_to_psi(Pcf_pa),
        "dP_psi": pf.pa_to_psi(P1_pa) - pf.pa_to_psi(Pcf_pa),
        "m_lbhr": pf.kgs_to_lbhr(m_max_kgs),
        "v1_fts": pf.ms_to_fts(v1_ms),
        "v2_fts": pf.ms_to_fts(v2_ms),
        "rho1_lbft3": rho1_lbft3,
        "rho2_lbft3": rho2_lbft3,
        "Re": None,
        "fd": fd_eff,
        "fd_eff": fd_eff,
        "K_total": K_total,
        "Pcf_psia": pf.pa_to_psi(Pcf_pa),
        "choked": True,
        "phase": phase,
    }


# ---------------------------------------------------------------------------
# Gas transmission pipeline (Weymouth / Panhandle / etc.), no fittings
# ---------------------------------------------------------------------------

PIPELINE_METHODS = {
    "Weymouth": {"func": comp.Weymouth, "needs_mu": False, "default_E": 0.92},
    "Panhandle A": {"func": comp.Panhandle_A, "needs_mu": False, "default_E": 0.92},
    "Panhandle B": {"func": comp.Panhandle_B, "needs_mu": False, "default_E": 0.92},
    "Spitzglass (high pressure)": {"func": comp.Spitzglass_high, "needs_mu": False, "default_E": 1.0},
    "Spitzglass (low pressure, <1 psig)": {"func": comp.Spitzglass_low, "needs_mu": False, "default_E": 1.0},
    "Fritzsche": {"func": comp.Fritzsche, "needs_mu": False, "default_E": 1.0},
    "Oliphant": {"func": comp.Oliphant, "needs_mu": False, "default_E": 0.92},
    "Muller": {"func": comp.Muller, "needs_mu": True, "default_E": 1.0},
    "IGT": {"func": comp.IGT, "needs_mu": True, "default_E": 1.0},
}


def solve_pipeline(method: str, SG: float, Tavg_F: float, L_value: float, L_unit: str, Di_in: float,
                    P1_psia: float | None, P2_psia: float | None, Q_scfh: float | None,
                    solve_for: str, Zavg: float, E: float, mu_cP: float | None,
                    Ts_F: float = 60.0, Ps_psia: float = 14.696):
    """Solve one of Q/P1/P2 for a long gas transmission pipeline."""
    entry = PIPELINE_METHODS[method]
    Tavg_K = pf.degF_to_K(Tavg_F)
    Ts_K = pf.degF_to_K(Ts_F)
    Ps_pa = pf.psi_to_pa(Ps_psia)
    Di_m = pf.inch_to_m(Di_in)
    L_m = pf.mile_to_m(L_value) if L_unit == "miles" else pf.ft_to_m(L_value)

    P1_pa = pf.psi_to_pa(P1_psia) if P1_psia is not None else None
    P2_pa = pf.psi_to_pa(P2_psia) if P2_psia is not None else None
    Q_m3s = (Q_scfh * pf.u.foot ** 3 / pf.u.hour).to(pf.u.m ** 3 / pf.u.s).magnitude if Q_scfh is not None else None

    kwargs = dict(SG=SG, Tavg=Tavg_K, L=L_m, D=Di_m, P1=P1_pa, P2=P2_pa, Q=Q_m3s,
                  Ts=Ts_K, Ps=Ps_pa, Zavg=Zavg, E=E)
    if entry["needs_mu"]:
        kwargs["mu"] = pf.cP_to_pas(mu_cP)

    result = entry["func"](**kwargs)

    if solve_for == "Q":
        Q_m3s = result
    elif solve_for == "P1":
        P1_pa = result
    elif solve_for == "P2":
        P2_pa = result

    return {
        "P1_psia": pf.pa_to_psi(P1_pa),
        "P2_psia": pf.pa_to_psi(P2_pa),
        "Q_scfh": pf.m3s_to_scfh(Q_m3s),
        "Q_mmscfd": pf.m3s_to_scfh(Q_m3s) * 24.0 / 1e6,
    }
