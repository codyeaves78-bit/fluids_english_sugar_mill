"""Pipe math for pump guy. No fancy units, just gpm/inch/psi like Crane book.

Ug: flow in gpm. Pipe size in inch. Fluid weight in lb/ft3. Thick-water
number (viscosity) in cP. Head and pressure in ft and psi. That is all.

Assumes user has Crane TP-410 book
"""

import math


def h_L(K: float, Q: float, d: float) -> float:
    """Water go through fitting, water lose height. This how much.

    Args:
        K: Resistance number of fitting/pipe. No unit, just a number.
        Q: Flow, gpm.
        d: Pipe inside size, inch.

    Returns:
        Head lost, ft of water.
    """
    return 0.002593 * K * Q**2 / d**4


def Re(Q: float, rho: float, d: float, mu: float) -> float:
    """Reynolds number. Big number good, mean water flow smooth (turbulent math still work).

    Args:
        Q: Flow, gpm.
        rho: Fluid weight, lb/ft3.
        d: Pipe inside size, inch.
        mu: Thick-water number, cP.

    Returns:
        Reynolds number. No unit.
    """
    return 50.66 * Q * rho / (d * mu)


def v_ft_s(Q: float, d: float) -> float:
    """How fast water move in pipe.

    Args:
        Q: Flow, gpm.
        d: Pipe inside size, inch.

    Returns:
        Speed, ft/sec.
    """
    cfpm = Q * 0.133681  # gallon to ft3, per minute
    cfps = cfpm / 60  # now per second
    A_ft2 = (3.14159 * d**2 / 4) / 144  # pipe hole area, ft2
    return cfps / A_ft2


def vel_head(v_ft_sec: float) -> float:
    """Speed turn into head, using normal earth gravity (32.2 ft/s2).

    Args:
        v_ft_sec: Speed, ft/sec.

    Returns:
        Velocity head, ft of water.
    """
    return v_ft_sec**2 / (2 * 32.2)


def P_from_H(rho: float, H: float) -> float:
    """Head go in, pressure come out.

    Args:
        rho: Fluid weight, lb/ft3.
        H: Head, ft of water.

    Returns:
        Pressure, psi.
    """
    return rho / 144 * H


def bhp(Q: float, H: float, rho: float, eff: float) -> float:
    """How much muscle pump need (brake horsepower).

    Args:
        Q: Flow, gpm.
        H: Total head, ft.
        rho: Fluid weight, lb/ft3.
        eff: Pump efficiency, 0 to 1 (0.75 mean 75%).

    Returns:
        Brake horsepower, hp.
    """
    return Q * H * rho / (247000 * eff)


def f(eta: float = 0.00015, d: float = 1, Re: float = 10000) -> float:
    """Darcy friction number. Colebrook math, solve with secant method (guess, check, guess better).

    Args:
        eta: Pipe roughness bump size, ft.
        d: Pipe inside size, inch.
        Re: Reynolds number from Re() function above.

    Returns:
        Darcy friction factor. No unit.
    """
    if Re > 2000:  # not slow-smooth flow no more, use turbulent math
        D = d / 12  # inch to ft

        def left(f):
            return 1 / f**0.5

        def right(f):
            return -2.0 * math.log(eta / (3.7 * D) + 2.51 / (Re * f**0.5), 10)

        f1 = 0.02  # first guess
        f2 = 0.01  # second guess
        y1 = left(f1) - right(f1)
        y2 = left(f2) - right(f2)
        fn = f2 - ((y2 * (f2 - f1)) / (y2 - y1))
        fn_1 = f2  # keep old guess for next loop
        max_iterations = 20
        tolerance = 0.000001
        iteration = 1
        while abs(fn - fn_1) > tolerance and iteration <= max_iterations:
            y1 = left(fn_1) - right(fn_1)
            y2 = left(fn) - right(fn)
            a = fn  # remember this guess
            fn = fn - ((y2 * (fn - fn_1)) / (y2 - y1))
            fn_1 = a
            iteration += 1
        print(f"friction factor converged in {iteration} iterations")
        if Re < 4000:
            print(f"WARNING!!! Re is > 2000 and < 4000, this is the transition zone, calculation assumes turbulent flow")

        return fn
    elif Re <= 2000:  # slow-smooth flow (laminar), easy math
        return 64 / Re



def K_L(f: float, L: float, D: float) -> float:
    """Resistance number K for straight pipe run (friction, not fitting).

    Args:
        f: Darcy friction factor from f() above.
        L: Pipe length. Any unit, long as same as D.
        D: Pipe inside size. Same unit as L.

    Returns:
        Resistance coefficient K. No unit.
    """
    return f * L / D

def discharge_Q(d: float, head: float, K: float) -> float:
    """Flow through orifice/fitting when you already know the head, not the flow.

    Same math as h_L() up top, just solved backward for Q instead of head.
    (19.64 = 1/sqrt(0.002593), the constant h_L uses.)

    Args:
        d: Pipe/orifice inside size, inch.
        head: Head available/lost, ft of water.
        K: Resistance number of fitting/pipe. No unit, just a number.

    Returns:
        Flow, gpm.
    """
    return 19.64 * d**2 * math.sqrt(head / K)

#################################################################
# K numbers for valve and fitting rock-math (Crane TP-410 book)
#################################################################

def K_formula_1(angle: float, d_small: float, d_large: float) -> float:
    """K for gentle pipe squeeze/spread, cone angle small (Crane formula 1).

    Args:
        angle: Full cone angle, degree.
        d_small: Small pipe size. Any unit, long as same as d_large.
        d_large: Big pipe size. Same unit as d_small.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    radian = angle * math.pi / 180
    beta = d_small / d_large
    numerator = 0.8 * math.sin(radian / 2) * (1 - beta**2)
    denominator = beta**4
    return numerator / denominator

def K_formula_2(angle: float, d_small: float, d_large: float) -> float:
    """K for gentle pipe squeeze, cone angle wide (Crane formula 2).

    Use this one instead of K_formula_1 when cone angle bigger than
    45 degree (up to 180). Formula 1 math get bad at wide angle.

    Args:
        angle: Full cone angle, degree.
        d_small: Small pipe size. Any unit, long as same as d_large.
        d_large: Big pipe size. Same unit as d_small.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    radian = angle * math.pi / 180
    beta = d_small / d_large
    numerator = 0.5 * math.sqrt(math.sin(radian / 2)) * (1 - beta**2)
    denominator = beta**4
    return numerator / denominator


def K_formula_3(angle: float, d_small: float, d_large: float) -> float:
    """K for gentle pipe spread (grow bigger), cone angle small (Crane formula 3).

    Spread-cousin of K_formula_1 (cone angle 45 degree or less).

    Args:
        angle: Full cone angle, degree.
        d_small: Small pipe size. Any unit, long as same as d_large.
        d_large: Big pipe size. Same unit as d_small.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    radian = angle * math.pi / 180
    beta = d_small / d_large
    numerator = 2.6 * math.sin(radian / 2) * ((1 - beta**2)**2)
    denominator = beta**4
    return numerator / denominator


def K_formula_4(d_small: float, d_large: float) -> float:
    """K for sudden pipe spread, no cone at all (Crane formula 4).

    Spread-cousin of K_formula_2 (cone angle 45 to 180 degree). Angle
    number not needed no more, math same for whole range.

    Args:
        d_small: Small pipe size. Any unit, long as same as d_large.
        d_large: Big pipe size. Same unit as d_small.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    beta = d_small / d_large
    numerator = (1 - beta**2)**2
    denominator = beta**4
    return numerator / denominator


def K_formula_5(angle: float, d_small: float, d_large: float, K1: float) -> float:
    """K for valve with cone reducer on each side, angle 45 degree or less (Crane formula 5).

    Take valve own K (K1, at small-bore speed) plus squeeze-loss and
    spread-loss from the two cone reducers. Formula: K1/beta**4 +
    K_formula_1 + K_formula_3.

    Args:
        angle: Full cone angle of reducer, degree.
        d_small: Valve bore size. Any unit, long as same as d_large.
        d_large: Pipe size reducer connect to. Same unit as d_small.
        K1: Valve own K, counted at d_small speed.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    beta = d_small / d_large
    return K1 / beta**4 + K_formula_1(angle, d_small, d_large) + K_formula_3(angle, d_small, d_large)


def K_formula_6(angle: float, d_small: float, d_large: float, K1: float) -> float:
    """K for valve with cone reducer, angle 45 to 180 degree (Crane formula 6).

    Wide-angle cousin of K_formula_5: K1/beta**4 + K_formula_2 + K_formula_4.

    Args:
        angle: Full cone angle of reducer, degree.
        d_small: Valve bore size. Any unit, long as same as d_large.
        d_large: Pipe size reducer connect to. Same unit as d_small.
        K1: Valve own K, counted at d_small speed.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    beta = d_small / d_large
    return K1 / beta**4 + K_formula_2(angle, d_small, d_large) + K_formula_4(d_small, d_large)


def K_formula_7(angle: float, d_small: float, d_large: float, K1: float) -> float:
    """K for valve/reducer combo, different mix math (Crane formula 7).

    Ug, warning: no valve function below call this by angle-range check
    like formula 5/6 get called. Some valve function (globe, angle,
    lift-check, stop-check) always use this one no matter angle. Before
    you trust number, check Crane book which beta/angle range formula 7
    really for.

    Args:
        angle: Full cone angle of reducer, degree.
        d_small: Valve bore size. Any unit, long as same as d_large.
        d_large: Pipe size reducer connect to. Same unit as d_small.
        K1: Valve own K, counted at d_small speed.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    beta = d_small / d_large
    return K1 / beta**4 + beta * (K_formula_2(angle, d_small, d_large) + K_formula_4(d_small, d_large))


def _beta(d_small: float, d_large: float) -> float:
    """Bore ratio helper. No reducer given, ratio is 1 (same size, no squeeze).

    Ug story: old code write `1 if d_small or d_large == None else ...`,
    but `==` grab tighter than `or`, so it really mean
    `d_small or (d_large == None)`. Any real (non-zero) d_small make
    whole thing true, so beta got stuck at 1 EVERY TIME someone pass a
    real reducer size. Whole family of valve function below had this same
    copy-paste bug. Fixed here, once, for all of them.

    Args:
        d_small: Valve/reduced bore size, or None if no reducer.
        d_large: Full pipe size, or None if no reducer.

    Returns:
        beta = d_small / d_large, or 1 if either side not given.
    """
    return 1 if d_small is None or d_large is None else d_small / d_large


def _K_valve_reducer_by_angle(f_t: float, base: float, d_small: float, d_large: float, angle: float, K: float) -> float:
    """Shared brain for gate/ball valve: pick formula 5 or 6 by cone angle.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table number).
        base: Valve-own K multiplier (K1 = base * f_t) when no K given.
        d_small: Valve bore size, or None for no reducer.
        d_large: Pipe size, or None for no reducer.
        angle: Full cone angle of reducer, degree. 0 when no reducer.
        K: Valve-own K if you already know it, else None to use base * f_t.

    Returns:
        K number for the valve (+reducer if any).

    Note:
        beta < 1 with angle > 180 not covered (matches K_formula_7 gap
        above) - falls through and returns None. Nobody has fed this yet,
        but watch out.
    """
    beta = _beta(d_small, d_large)
    if beta == 1 and angle == 0:
        return base * f_t
    elif beta < 1 and angle <= 45:
        if K is None:
            K = base * f_t
        return K_formula_5(angle, d_small, d_large, K1=K)
    elif beta < 1 and 45 < angle <= 180:
        if K is None:
            K = base * f_t
        return K_formula_6(angle, d_small, d_large, K1=K)


def _K_valve_reducer_formula7(f_t: float, base: float, d_small: float, d_large: float, angle: float, K: float) -> float:
    """Shared brain for globe/angle/lift-check/stop-check valve: always formula 7.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table number).
        base: Valve-own K multiplier (K1 = base * f_t) when no K given.
        d_small: Valve bore size, or None for no reducer.
        d_large: Pipe size, or None for no reducer.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K if you already know it, else None to use base * f_t.

    Returns:
        K number for the valve (+reducer if any).
    """
    beta = _beta(d_small, d_large)
    if beta == 1:
        return base * f_t
    elif beta < 1:
        if K is None:
            K = base * f_t
        return K_formula_7(angle, d_small, d_large, K)


def _K_valve_reducer_formula6(f_t: float, base: float, d_small: float, d_large: float, angle: float, K: float) -> float:
    """Shared brain for plug valve: always formula 6.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table number).
        base: Valve-own K multiplier (K1 = base * f_t) when no K given.
        d_small: Valve bore size, or None for no reducer.
        d_large: Pipe size, or None for no reducer.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K if you already know it, else None to use base * f_t.

    Returns:
        K number for the valve (+reducer if any).
    """
    beta = _beta(d_small, d_large)
    if beta == 1:
        return base * f_t
    elif beta < 1:
        if K is None:
            K = base * f_t
        return K_formula_6(angle, d_small, d_large, K1=K)


def K_gate_valve(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for gate valve, wide open.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 8 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree. 0 when no reducer.
        K: Valve-own K, counted at d_small. Default 8 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_by_angle(f_t, 8, d_small, d_large, angle, K)


def K_globe_valve(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for regular (Z-body) globe valve.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 340 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 340 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 340, d_small, d_large, angle, K)


def K_globe_valve_45(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for angle-pattern globe valve (45 deg Y body).

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 55 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 55 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 55, d_small, d_large, angle, K)


def K_globe_valve_90(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for angle-pattern globe valve (90 deg body).

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 150 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 150 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 150, d_small, d_large, angle, K)


def K_angle_valve(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for angle valve.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 55 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 55 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 55, d_small, d_large, angle, K)


def K_swing_check_flanged(f_t: float) -> float:
    """K for swing check valve, flanged body, wide open.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 50 * f_t.
    """
    return 50 * f_t


def K_swing_check_thread(f_t: float) -> float:
    """K for swing check valve, threaded body, wide open.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 100 * f_t.
    """
    return 100 * f_t


def K_lift_check_90(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for lift-check valve, 90 deg (globe-lift) body.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 600 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 600 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 600, d_small, d_large, angle, K)


def K_lift_check_45(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for lift-check valve, 45 deg (angle-lift) body.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 55 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 55 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 55, d_small, d_large, angle, K)


def K_telt_disc_check(f_t: float, angle: float, nom_pipe_diameter: float) -> float:
    """K for tilting-disc check valve. Table split by pipe size and disc angle.

    Ug note: function name say "telt" - probably mean "tilt", just
    a spelling thing from way back. Not fixed here (renaming break
    anyone already calling it), just flagging.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).
        angle: Disc tilt angle, degree. Table only know 5 and 15;
            anything else fall back to 15 with a warning print.
        nom_pipe_diameter: Nominal pipe size, inch (2 to 48).

    Returns:
        K number. Falls back to 12-inch/15-degree row (K = 90 * f_t)
        with a warning print if nom_pipe_diameter outside 2-48.
    """
    if 2 <= nom_pipe_diameter <= 8:
        if angle == 5:
            return 40 * f_t
        elif angle == 15:
            return 120 * f_t
        else:
            print('Using angle of 15 deg for calculations')
            return 120 * f_t
    elif 10 <= nom_pipe_diameter <= 14:
        if angle == 5:
            return 30 * f_t
        elif angle == 15:
            return 90 * f_t
        else:
            print('Using angle of 15 deg for calculations')
            return 90 * f_t
    elif 16 <= nom_pipe_diameter <= 48:
        if angle == 5:
            return 20 * f_t
        elif angle == 15:
            return 60 * f_t
        else:
            print('Using angle of 15 deg for calculations')
            return 60 * f_t
    else:
        print(f'WARNING!!! Nominal Pipe Diameter {nom_pipe_diameter} out of range 2 - 48, using 12 inch pipe with angle = 15 for value')
        return 90 * f_t

def K_stop_check_1(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for stop-check valve type 1 (globe-lift body).

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 400 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 400 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 400, d_small, d_large, angle, K)


def K_stop_check_2(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for stop-check valve type 2.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 200 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 200 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 200, d_small, d_large, angle, K)


def K_stop_check_3(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for stop-check valve type 3.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 300 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 300 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 300, d_small, d_large, angle, K)


def K_stop_check_4(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for stop-check valve type 4.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 350 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 350 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 350, d_small, d_large, angle, K)


def K_stop_check_5_and_6(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for stop-check valve type 5 and 6 (same K in Crane table).

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 55 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 55 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula7(f_t, 55, d_small, d_large, angle, K)


def K_foot_valve_strainer_poppet(f_t: float) -> float:
    """K for foot valve with strainer, poppet disc type.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 420 * f_t.
    """
    return 420 * f_t


def K_foot_valve_strainer_disc(f_t: float) -> float:
    """K for foot valve with strainer, flat disc type.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 75 * f_t.
    """
    return 75 * f_t


def K_ball_valve(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for ball valve, wide open.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 3 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree. 0 when no reducer.
        K: Valve-own K, counted at d_small. Default 3 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_by_angle(f_t, 3, d_small, d_large, angle, K)


def butterfly_valve(f_t: float, nom_pipe_diameter: float, offset: int = 1) -> float:
    """K for butterfly valve. Table split by pipe size and disc offset.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).
        nom_pipe_diameter: Nominal pipe size, inch (2 to 24).
        offset: 1 = single offset disc, 2 = double, 3 = triple. Anything
            else fall back to offset 2 with a warning print.

    Returns:
        K number. Falls back to 12-inch/double-offset row (K = 52 * f_t)
        with a warning print if nom_pipe_diameter or offset out of range.
    """
    if 2 <= nom_pipe_diameter <= 8:
        if offset == 1:
            return 45 * f_t
        elif offset == 2:
            return 74 * f_t
        elif offset == 3:
            return 218 * f_t
        else:
            print("Using offset = 2 for calcs")
            return 74 * f_t
    elif 10 <= nom_pipe_diameter <= 14:
        if offset == 1:
            return 35 * f_t
        elif offset == 2:
            return 52 * f_t
        elif offset == 3:
            return 96 * f_t
        else:
            print("Using offset = 2 for calcs")
            return 52 * f_t
    elif 16 <= nom_pipe_diameter <= 24:
        if offset == 1:
            return 25 * f_t
        elif offset == 2:
            return 43 * f_t
        elif offset == 3:
            return 55 * f_t
        else:
            print("Using offset = 2 for calcs")
            return 43 * f_t
    else:
        print(f"Nominal Pipe diameter {nom_pipe_diameter} or Offset {offset} out of range, using 12 inch double offset for value")
        return 52 * f_t

def diaphragm_valve_weir(f_t: float) -> float:
    """K for diaphragm valve, weir (dam) type.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 149 * f_t.
    """
    return 149 * f_t

def diaphragm_valve_straight(f_t: float) -> float:
    """K for diaphragm valve, straight-through type.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 39 * f_t.
    """
    return 39 * f_t

def K_plug_valve_1(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for plug valve, straightway type.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 18 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 18 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula6(f_t, 18, d_small, d_large, angle, K)

def K_plug_valve_2(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for plug valve, 3-way through-flow type.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 30 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 30 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula6(f_t, 30, d_small, d_large, angle, K)

def K_plug_valve_3(f_t: float, d_small: float = None, d_large: float = None, angle: float = 0, K: float = None) -> float:
    """K for plug valve, branch-flow type.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value),
            used for valve-own loss K = 90 * f_t when K not given.
        d_small: Valve bore size for reduced port.
        d_large: Full pipe size the reduced port sit in.
        angle: Full cone angle of reducer, degree.
        K: Valve-own K, counted at d_small. Default 90 * f_t.

    Returns:
        K number. No unit. Counted at small-pipe speed.
    """
    return _K_valve_reducer_formula6(f_t, 90, d_small, d_large, angle, K)

def K_mitre(f_t: float, angle: float) -> float:
    """K for mitre bend (no curve, just a cut angle joint). Curve-fit to Crane table.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).
        angle: Bend angle, degree.

    Returns:
        K number. No unit.
    """
    a = 6.2887
    b = 0.0260
    c = -5.0267
    x = angle
    factor = a * math.exp(b * x) + c
    return f_t * factor

def _interp_table(x: float, xs: list, ys: list) -> float:
    """Look up y for x in a table, straight line between points, clamp at ends.

    Args:
        x: Value you want to look up.
        xs: Table x points, small to big.
        ys: Table y points, same order/length as xs.

    Returns:
        y at x: exact table hit, straight-line guess between two nearest
        points, or nearest end value if x fall outside table.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for lo, hi, y_lo, y_hi in zip(xs, xs[1:], ys, ys[1:]):
        if lo <= x <= hi:
            weight = (x - lo) / (hi - lo)
            return y_lo + weight * (y_hi - y_lo)


def K_90_bw(f_t: float, r_d_ratio: float = 1.5) -> float:
    """K for smooth (butt-weld) 90 degree bend.

    Look up velocity-head number n from Crane table for 90 deg bends,
    keyed by bend radius over pipe size (r/d), straight-line guess
    between table points, then K = n * f_t.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).
        r_d_ratio: Bend radius over pipe size, no unit. Outside table's
            [1, 20] range, clamp to nearest end.

    Returns:
        K number. No unit.
    """
    r_d_ratios = [1, 1.5, 2, 3, 4, 6, 8, 10, 12, 14, 16, 20]
    factors = [20, 14, 12, 12, 14, 17, 24, 30, 34, 38, 42, 50]
    return _interp_table(r_d_ratio, r_d_ratios, factors) * f_t

def K_elbow_angle(f_t: float, r_d_ratio: float, angle: float) -> float:
    """K for smooth bend at some angle other than plain 90 degree.

    Crane formula: K = (n-1)(0.25*pi*f_t*(r/d) + 0.5*K_90) + K_90, where
    n is how many 90-degree bends fit in the total angle (n = angle/90).

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).
        r_d_ratio: Bend radius over pipe size, no unit.
        angle: Total bend angle, degree (e.g. 180 for a U-bend).

    Returns:
        K number. No unit.
    """
    n = angle / 90
    K = K_90_bw(f_t, r_d_ratio)
    return (n - 1) * (0.25 * math.pi * f_t * r_d_ratio + 0.5 * K) + K

def K_threaded_180_return(f_t: float) -> float:
    """K for threaded 180 degree return bend.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 50 * f_t.
    """
    return 50 * f_t

def K_threaded_90(f_t: float) -> float:
    """K for threaded 90 degree elbow.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 30 * f_t.
    """
    return 30 * f_t

def K_threaded_45(f_t: float) -> float:
    """K for threaded 45 degree elbow.

    Args:
        f_t: Pipe friction factor at full-rough flow (Crane table value).

    Returns:
        K number, 16 * f_t.
    """
    return 16 * f_t

def K_entrance_projecting_inward() -> float:
    """K for pipe entrance that sticks into the tank (re-entrant), sharp edge.

    Returns:
        K number, flat 0.78 (no inputs needed, Crane table value is fixed).
    """
    return 0.78

def K_entrance_flush(r_d_ratio: float) -> float:
    """K for flush pipe entrance with a rounded lip.

    Look up K straight from Crane table for flush entrances, keyed by
    corner radius over pipe size (r/d), straight-line guess between
    table points.

    Args:
        r_d_ratio: Entrance corner radius over pipe size, no unit.
            Outside table's [0, 0.15] range, clamp to nearest end.

    Returns:
        K number. No unit.
    """
    r_d_values = [0, 0.02, 0.04, 0.06, 0.1, 0.15]
    K_values = [0.5, 0.28, 0.24, 0.15, 0.09, 0.04]
    return _interp_table(r_d_ratio, r_d_values, K_values)

def K_exit() -> float:
    """K for pipe exit into a big tank/space (all velocity head lost).

    Returns:
        K number, flat 1.0.
    """
    return 1.0

def K_Tee_wye_converging(Q_branch: float, Q_comb: float, beta: float, C: float, D: float, E: float, F: float) -> float:
    """K for tee/wye branch outlet, converging flow (branch + run mixing together into run).

    C, D, E, F come from Crane TP-410 table 2-1, page 2-15 - pick the row
    for your fitting type/angle, don't make these numbers up.

    Args:
        Q_branch: Flow in the branch leg, gpm.
        Q_comb: Flow in the combined (downstream run) leg, gpm.
        beta: Branch size over run size, no unit.
        C: Table constant, base multiplier.
        D: Table constant, branch-ratio-squared term weight.
        E: Table constant, flow-split term weight.
        F: Table constant, branch-ratio term weight.

    Returns:
        K number for the branch, counted at branch-pipe speed.
    """
    part_1 = D * ((Q_branch / Q_comb / beta**2)**2)
    part_2 = E * (1 - Q_branch / Q_comb)**2
    part_3 = F / beta**2 * (Q_branch / Q_comb)**2
    return C * (1 + part_1 - part_2 - part_3)

def K_Tee_run(Q_branch: float, Q_comb: float) -> float:
    """K for tee run-through leg when branch also pulling/pushing flow. Quick guess, not exact.

    Args:
        Q_branch: Flow in the branch leg, gpm.
        Q_comb: Flow in the combined (run) leg, gpm.

    Returns:
        K number for the run leg, counted at run-pipe speed.
    """
    return 1.55 * (Q_branch / Q_comb) - (Q_branch / Q_comb)**2

def K_Tee_wye_diverging_branch(Q_branch: float, Q_comb: float, beta: float, G: float, H: float, J: float, angle: float) -> float:
    """K for tee/wye branch outlet, diverging flow (combined flow splitting off into branch).

    G, H, J come from Crane TP-410 tables 2-3/2-4/2-5, page 2-15 - pick
    the row for your fitting type/angle, don't make these numbers up.

    Args:
        Q_branch: Flow in the branch leg, gpm.
        Q_comb: Flow in the combined (upstream run) leg, gpm.
        beta: Branch size over run size, no unit.
        G: Table constant, base multiplier.
        H: Table constant, branch-ratio-squared term weight.
        J: Table constant, branch-ratio/angle term weight.
        angle: Branch takeoff angle, degree.

    Returns:
        K number for the branch, counted at branch-pipe speed.
    """
    radian = angle * math.pi / 180
    p1 = H * (Q_branch / Q_comb / beta**2)**2
    p2 = J * (Q_branch / Q_comb / beta**2) * math.cos(radian)
    return G * (1 + p1 - p2)

def K_Tee_wye_diverging_run(Q_branch: float, Q_comb: float, M: float) -> float:
    """K for tee/wye run leg, diverging flow (combined flow splitting off into branch).

    M comes from Crane TP-410 tables 2-3/2-4/2-5, page 2-15.

    Args:
        Q_branch: Flow in the branch leg, gpm.
        Q_comb: Flow in the combined (upstream run) leg, gpm.
        M: Table constant.

    Returns:
        K number for the run leg, counted at run-pipe speed.
    """
    return M * (Q_branch / Q_comb)**2

def K_different_pipe_ID(Kb: float, da: float, db: float) -> float:
    """Move a K number from one pipe size's speed-reference to another's.

    Same trick used by hand in heat_treat_unit_head_loss.py (dividing by
    beta**4) - this just makes it a reusable function. Since h_L ~ K/d**4
    at fixed flow, K must scale by (d_ref_old/d_ref_new)**4 to keep the
    same physical head loss when you change which diameter's velocity
    you're counting K against.

    Args:
        Kb: K number counted at db's speed.
        da: Diameter you want the K counted at now.
        db: Diameter Kb was originally counted at.

    Returns:
        K number, counted at da's speed instead of db's.
    """
    return Kb * (da / db)**4

