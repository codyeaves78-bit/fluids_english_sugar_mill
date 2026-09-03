# basic functions to call for the SugarStream object

import numpy as np

# building my functions to call
def bpe_brix(brix):
  """ bpe from brix alone"""
  bpe = 4.266667 * brix / (100 - brix)
  return bpe

def bpe_head(lvl, brix, t_vap):
  """ bpe from head, level in ft"""
  brix_poly = (
      0.99991
      + 0.0038008 * brix
      + 0.000012662 * (brix**2)
      + 0.00000009596 * (brix**3)
  )

  temp_poly = (
      5.314
      - 0.07135 * t_vap
      + 0.00033908 * (t_vap**2)
      - 0.00000055728 * (t_vap**3)
  )

  bpe_calc = lvl * 6 * brix_poly * temp_poly
  if bpe_calc <1:
    bpe_calc = 1
  return bpe_calc

def sat_steam_temp(p_psia):
    """saturation steam temperature, I use this over IAPWS97 for speed"""
    """Only for pressure 1-60 psia"""
    A = 6.239238
    B = 2988.801361
    C = 377.305590
    temp = B / (A - np.log10(p_psia)) - C
    return temp

def bpe_total(lvl, brix, p_vap_psia):
   """bpe total, combine previous functions, lvl in ft"""
   t_vap = sat_steam_temp(p_vap_psia)
   bpe1 = bpe_brix(brix)
   bpe2 = bpe_head(lvl, brix, t_vap) # lvl in ft
   bpe_total = bpe1 + bpe2
   return bpe_total

def get_latent_heat(p_psia):
    """gets the latent heat of the steam or liquid"""
    # only for psia 1 to 60
    # this is much much faster but very slightly less accurate than using IAPWS97
    # Calculate the polynomial
    temp = sat_steam_temp(p_psia)
    h_fg = -0.00000152231563 * temp**3 + .000504774867 * temp**2 - 0.634291695987 * temp + 1096.29
    return h_fg

def get_cp(brix):
  """gets the specific heat capacity"""
  cp = 0.9964 - 0.005656 * brix
  return cp

def specific_gravity(brix): 
    """gets the specific gravity of the sugar solution, only for 68 deg F, but good enough for our purposes"""
    sg = (
       62.2511
       + 0.24081 * brix
       + 0.0007902404 * brix**2
       + 0.00000423954  * brix**3
       - 0.00000001657193 * brix**4
        ) / 62.4
    return sg

# Power-law (Ostwald-de Waele) model constants for molasses, by grade, per Rein's
# Cane Sugar Engineering (1st ed.): tau = K * gamma_dot ** n.
#   - K_const: the correlation constant in the consistency formula (eq. 16.5).
#   - n: the flow behavior index used with K in the head-loss formula (eq. 16.17).
# "C" is C (final) molasses; "HIGH" is high-grade (A and B) molasses.
MOLASSES_GRADE_PROPERTIES = {
    "C": {"K_const": 0.111, "n": 0.85},
    "HIGH": {"K_const": 0.088, "n": 0.91},
}


def _molasses_grade(grade: str) -> dict:
    key = grade.strip().upper()
    if key not in MOLASSES_GRADE_PROPERTIES:
        raise ValueError(f"grade must be 'C' or 'high', got {grade!r}")
    return MOLASSES_GRADE_PROPERTIES[key]


def molasses_flow_behavior_index(grade: str = "C") -> float:
    """Power-law flow behavior index n for molasses, by grade (see MOLASSES_GRADE_PROPERTIES)."""
    return _molasses_grade(grade)["n"]


def molasses_consistency(brix: float = 80.0, purity: float = 55.0, temp_deg_F: float = 140.0,
                          grade: str = "C") -> float:
    """
    Power-law consistency index K for molasses, per Rein's Cane Sugar Engineering
    (1st ed.), equation 16.5: tau = K * gamma_dot ** n (see molasses_flow_behavior_index
    for the matching n).

    Args:
        brix: Brix of the molasses, percent (0-100).
        purity: Purity of the molasses, percent (0-100).
        temp_deg_F: Molasses temperature, deg F.
        grade: "C" for C (final) molasses (default), or "high" for high-grade
            (A/B) molasses - selects the correlation constant (0.111 vs 0.088).

    Returns:
        Consistency index K, Pa*s^n (metric - this is not a simple viscosity;
        combine with n and a shear rate via head_loss_meters, or compute an
        apparent viscosity as K * gamma_dot ** (n - 1)).
    """
    K_const = _molasses_grade(grade)["K_const"]
    t_C = (temp_deg_F - 32.0) * 5.0 / 9.0
    top = 3.7 * brix - 0.7 * (t_C - 50.0)
    bot = 113.5 - brix + 0.19 * (t_C - 50.0)
    return K_const * (purity ** (-1.3)) * np.exp(top / bot)

def reynolds_number_molasses_massecuite(D, u, rho, K, n, g: float = 9.81):
    """
    Calculates the reynolds number for the sugar streams based on Rein's formula 16.14 from his book
    Re = A / (B * C)
    A = D ** n * u ** (2 - n) * rho
    B = g ** (n - 1) * K
    C = ((3 * n + 1) / (4 * n)) ** n
    metric units
    """
    A = D ** n * u ** (2 - n) * rho
    B = g ** (n - 1) * K
    C = ((3 * n + 1) / (4 * n)) ** n 
    return A / (B * C)   

def head_loss_meters_fittings(k_f, u, g: float = 9.81):
   """
   Calculates the head loss in meters from valves and fittings, metric units
   """
   return k_f * u ** 2 / (2 * g)

def calc_k_f(k1, Re, k_max, D):
   """
   Hooper's 2-K method for a single fitting/valve loss coefficient:
   K_f = k1 / Re + k_max * (1 + 1 / D)

   NOTE: D must be the pipe inside diameter in INCHES, not meters - the 1/D
   correction term in the published 2-K correlation (and the K1/k_max
   constants in TWO_K below) is calibrated on diameter in inches. Convert
   before calling: D_inches = D_m / 0.0254.
   """
   return k1 / Re + k_max * (1 + 1 / D)


def total_fittings_K(fittings, Re, D_inches):
    """
    Total 2-K fitting/valve loss coefficient for a list of fittings, at a
    given (generalized) Reynolds number and pipe ID in inches.

    Args:
        fittings: list of (k1, k_max, qty) tuples - qty of each fitting/valve
            (see TWO_K for k1/k_max values, or use flatten_two_k() to look
            one up by name).
        Re: Reynolds number (see reynolds_number_molasses_massecuite).
        D_inches: Pipe inside diameter, inches.

    Returns:
        Total K_f, dimensionless.
    """
    return sum(qty * calc_k_f(k1, Re, k_max, D_inches) for k1, k_max, qty in fittings)


def flatten_two_k(tree=None, prefix=""):
    """
    Flattens the nested TWO_K dict into {"Category > Sub > Type": TwoK(K1, Kinf)}
    labels, for populating a UI dropdown without hand-writing every path.
    """
    if tree is None:
        tree = TWO_K
    out = {}
    for key, value in tree.items():
        label = f"{prefix} > {key}" if prefix else key
        if isinstance(value, TwoK):
            out[label] = value
        else:
            out.update(flatten_two_k(value, label))
    return out

def head_loss_meters(K: float, L: float, D: float, n: float, u: float, rho: float, g: float = 9.81) -> float:
    """
    Friction head loss for laminar power-law (Ostwald-de Waele) pipe flow, per
    Rein's Cane Sugar Engineering (1st ed.), equation 16.17:

        H = A * (B * C) ** n
        A = 4 * K * L / (g * D * rho)
        B = (3 * n + 1) / (4 * n)
        C = 8 * u / D

    All inputs are metric; the result is metric too (head of the flowing fluid,
    at its own density). Convert with m_to_ft / head_ft_to_psi for display.

    Args:
        K: Power-law consistency index, Pa*s^n (see molasses_consistency).
        L: Pipe length, m.
        D: Pipe inside diameter, m.
        n: Power-law flow behavior index (see molasses_flow_behavior_index).
        u: Mean velocity in the pipe, m/s.
        rho: Fluid density, kg/m^3.
        g: Gravitational acceleration, m/s^2.

    Returns:
        Friction head loss, m of the flowing fluid.
    """
    A = 4 * K * L / (g * D * rho)
    B = (3 * n + 1) / (4 * n)
    C = (8 * u) / D
    return A * (B * C) ** n


def m_to_ft(head_m: float) -> float:
    """Convert a head (or any length) from meters to feet."""
    return head_m * 3.280839895


def head_ft_to_psi(head_ft: float, rho_lbft3: float) -> float:
    """Convert a head of fluid (ft) to a pressure (psi), given the fluid's density (lb/ft3)."""
    return head_ft * rho_lbft3 / 144.0


def molasses_viscosity(brix=80.0, purity=35.0, temp_deg_F=140.0, RS_Ash_ratio=0.7, purity_exponent=3):
   """
   This is using equation 14 from the 'THE VISCOSITY OF MOLASSES AND MASSECUITE' paper by EEA ROUILLARD and MFS KOENIG from the Sugar MIlling Research Institue
   Link here 'https://www.scribd.com/document/358730871/The-Viscosity-Molasses-and-Massecuite'
   this equation does not need the shear rate
   it is expressed as follows
   mu = A / (B * C)
   where
   A = 1.03e-17 * (brix / (100 - brix)) ** 5.82
   B = ((T - 273.15) / T ** 2) ** 4.45
   C = np.exp(0.187 * (purity / 100) ** VALUE? + 0.689 * RS_Ash_ratio)
   T is temp in deg K
   brix is expressed as a percent (80, 90, 75, ect...)
   purity is expressed as a percernt, formula converts to decimal
   RS_Ash_Ratio is expressed as a decimal, values typically between 0.7 - 1.4
   The VALUE? is either 2 or 3, the paper is too pixelated and blurry to tell. trying to research, but for now it seems to be 3, but I cannot tell

   Args:
       brix: Brix, percent (e.g. 80, 90, 75).
       purity: Purity, percent - normalized to a decimal internally.
       temp_deg_F: Temperature, deg F (converted to Kelvin internally).
       RS_Ash_ratio: Reducing sugars / ash ratio, decimal, typically 0.7-1.4.
       purity_exponent: The unconfirmed exponent on (purity/100) in the C term -
           2 or 3 per the source paper (illegible in the scanned copy); defaults
           to 3 (current best guess). Pass 2 to compare against the alternative.
           please not that it doesn't seem to make huge difference in calculations
           about a 1-2 % error, fine for sugar factory fluid calcs

   Returns:
       Viscosity, Pa*s (kept in metric - only convert to cP/English units at
       the final SugarStreamFluids output stage, per Rein's piping pressure
       loss formulas being metric throughout).
   """
   T = (temp_deg_F - 32.0) * 5.0 / 9.0 + 273.15
   A = 1.03e-17 * (brix / (100 - brix)) ** 5.82
   B = ((T - 273.15) / T ** 2) ** 4.45
   C = np.exp(0.187 * (purity / 100) ** purity_exponent + 0.689 * RS_Ash_ratio)
   return A / (B * C)

def massecuite_relative_viscosity(L, V, CV):
   """
   Uses equation 15 from the same paper referenced in molasses_viscosity
   mu_rel = np.exp(2.84 * L ** 0.0377 * V * (1 - CV / 12))
   L is the crystal specific grain size in mm
   V is the crystal / molasses volumetric ratio
   CV is the coefficient of variance, though it is very unclear from the paper if CV means C * V due to the nomenclature section where C = coefficient of variance
   The paper is vague on many things. I will assume CV means coefficient of variance because that is how it is written in literally every other peice of liturature
   I am also assuming that CV is meant to plug in as a decimal, so 50 CV = 0.5, the numbers don't make sense otherwise
   plugging it in straight will yeild massecuite viscosities much much lower than the mother liquor, which by experience we all know is false
   I am talking an order of magnitude lower, 0.08 times lower than the mother liquor, that's just not true. 
   Honestly this paper is one of the worst as far as properly documenting proper units for their formulas
   """
   return np.exp(2.84 * L ** 0.0377 * V * (1 - (CV / 100) / 12))

def massecuite_relative_viscosity_A_S(theta):
   """
   This is equation from Ackermann and Shen (1979) referenced in this paper
   Their equation only needs the volume fraction of crystals to the massecuite
   it is messy, but the inputs are simple
   mu_rel = A + B * C * D
   A = 1 - np.pi / (4 * alpha **2)
   B = np.pi / 4 - np.pi / (6 * alpha)
   C = 1 /(alpha ** 2 - 1)
   D = 1 + 2 / np.sqrt(alpha ** 2 - 1) * np.arctan(np.sqrt((alpha + 1) / (aplha - 1)))
   where alpha = (THETA_MAX / theta) ** (1/3)
   and THETA_MAX is assumed to be 0.625
   """
   THETA_MAX = 0.625
   alpha = (THETA_MAX / theta) ** (1/3)
   A = 1 - np.pi / (4 * alpha **2)
   B = np.pi / 4 - np.pi / (6 * alpha)
   C = 1 /(alpha ** 2 - 1)
   D = 1 + 2 / np.sqrt(alpha ** 2 - 1) * np.arctan(np.sqrt((alpha + 1) / (alpha - 1)))
   return A + B * C * D

def massecuite_viscosity(mu_rel, mu_mother_liquor):
   """
   Pass the relative massecuite viscosity and the viscosity of the mother liquor from the molasses viscosity formula
   """
   return mu_rel * mu_mother_liquor
 
if __name__ == '__main__':
    """
    This short demo script will take a massive range of brix and temps and put it into a chart to show the 
    viscostiy in Pa*s to prove the validity of it. Y axis is in log format so small values are readable
    """
    brix_array = np.arange(75, 90, .01)
    temp_array = np.arange(100, 150, 0.01)
    B, T = np.meshgrid(brix_array, temp_array)
    print(f"brix array: {brix_array}")
    mu = molasses_viscosity(brix=B, purity=35, temp_deg_F=T, RS_Ash_ratio=.7)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot(B, mu)
    plt.yscale('log')
    ax.grid()
    ax.set_xlabel(f'Brix \nThe bottom of each line is {temp_array[-1]:.0f} deg F \nThe top of each line is {temp_array[0]:.0f} deg F')
    ax.set_ylabel('Viscosity Pa * s')
    ax.set_title("Viscosity vs Brix over the range of 100 to 150 deg F")
    # plt.show()

    # Now to check the relative viscosity calculations vs the real data
    volumetric_ratios = np.array([0.5, 0.9, 0.9, 1.0, 1.0, 0.317, 0.362, 0.408, 0.468, 0.481, 0.542, 0.317, 0.84, 0.139, 0.704])
    theta_values = volumetric_ratios / (1 + volumetric_ratios)
    crystal_sizes = np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.64, 0.64, 0.64, 0.64, 0.64, 0.64, 0.144, 0.75, 0.131, 0.55])
    CV_values = np.array([0.31, 0.31, 0.31, 0.31, 0.31, 0.36, 0.36, 0.36, 0.36, 0.36, 0.36, 0.25, 0.29, 0.18, 0.38])
    measured_relative_viscosities = np.sort(np.array([2.7, 7.43, 7.4, 9.38, 7.5, 2.22, 2.54, 2.59, 2.80, 3.07, 4.63, 2.84, 6.58, 2.54, 7.48]))
    calculated_relative_viscosities = np.sort(massecuite_relative_viscosity(L=crystal_sizes, V=volumetric_ratios, CV=CV_values))
    A_and_S_calc_rel_visc = np.sort(massecuite_relative_viscosity_A_S(theta_values))
    correlation_matrix = np.corrcoef(measured_relative_viscosities, A_and_S_calc_rel_visc)
    r_value = correlation_matrix[0, 1]
    r2 = r_value ** 2
    print(f"R^2 Score: {r2:.4f}")
    print(measured_relative_viscosities)
    print(calculated_relative_viscosities)
    print(A_and_S_calc_rel_visc)
    """ Unwrap to see graph
    fig2, ax2 = plt.subplots()
    ax2.plot(measured_relative_viscosities, A_and_S_calc_rel_visc)
    ax2.grid()
    ax2.set_xlabel('Measured Relative Viscosities')
    ax2.set_ylabel("Calculated Relative Viscosities")
    ax2.set_title("Calculated relative viscosities vs measured relative viscosities")
    plt.show()
    """
    K = molasses_consistency(brix=93, purity=35, temp_deg_F=113, grade='C')
    print(K)

from collections import namedtuple

TwoK = namedtuple("TwoK", ["K1", "Kinf"])

TWO_K = {
    "elbows": {
        "90": {
            "standard_screwed":          TwoK(800, 0.40),   # R/D = 1
            "standard_flanged_welded":   TwoK(800, 0.25),   # R/D = 1
            "long_radius_all":           TwoK(800, 0.20),   # R/D = 1.5
            # Mitered elbows, R/D = 1.5
            "mitered_1_weld_90":         TwoK(1000, 1.15),
            "mitered_2_weld_45":         TwoK(800, 0.35),
            "mitered_3_weld_30":         TwoK(800, 0.30),
            "mitered_4_weld_22p5":       TwoK(800, 0.27),
            "mitered_5_weld_18":         TwoK(800, 0.25),
        },
        "45": {
            "standard_all":              TwoK(500, 0.20),   # R/D = 1
            "long_radius_all":           TwoK(500, 0.15),   # R/D = 1.5
            "mitered_1_weld_45":         TwoK(500, 0.25),
            "mitered_2_weld_22p5":       TwoK(500, 0.15),
        },
        "180": {
            "standard_screwed":          TwoK(1000, 0.60),  # R/D = 1
            "standard_flanged_welded":   TwoK(1000, 0.35),  # R/D = 1
            "long_radius_all":           TwoK(1000, 0.30),  # R/D = 1.5
        },
    },
    "tees": {
        "used_as_elbow": {
            "standard_screwed":          TwoK(500, 0.70),
            "long_radius_screwed":       TwoK(800, 0.40),
            "standard_flanged_welded":   TwoK(800, 0.80),
            "stub_in_branch":            TwoK(1000, 1.00),
        },
        "run_through": {
            "screwed":                   TwoK(200, 0.10),
            "flanged_welded":            TwoK(150, 0.50),
            "stub_in_branch":            TwoK(100, 0.00),
        },
    },
    "valves": {
        "gate_ball_plug": {
            "full_line_beta_1.0":        TwoK(300, 0.10),
            "reduced_beta_0.9":          TwoK(500, 0.15),
            "reduced_beta_0.8":          TwoK(1000, 0.25),
        },
        "globe_standard":                TwoK(1500, 4.00),
        "globe_angle_or_y":              TwoK(1000, 2.00),
        "diaphragm_dam":                 TwoK(1000, 2.00),
        "butterfly":                     TwoK(800, 0.25),
        "check": {
            "lift":                      TwoK(2000, 10.00),
            "swing":                     TwoK(1500, 1.50),
            "tilting_disk":              TwoK(1000, 0.50),
        },
    },
    "pipe": {
        "entrance":                      TwoK(160, 1.00),
        "exit":                          TwoK(0, 1.00),
    },
}