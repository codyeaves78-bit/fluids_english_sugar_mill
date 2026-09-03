# Oject SugarStreamFluids calculates properties and updates them based on the file sugar_stream_properties.py
# Based on the SugarStream file from the 'https://github.com/codyeaves78-bit/cane-sugar-mill-material-energy-balance' repo

import numpy as np
from sugar_stream_properties_fluids import *

class SugarStreamFluids:
    _count = 0
    """Class to represent the sugar stream, it will calculate properties based on the input parameters and update them as needed"""
    def __init__(self, brix=80, purity=55, flow_lb_per_hr=100, temp_deg_F=140, pressure_psia=14.7, level_ft=0,
                 ml_purity=None, CV=50, L=0.25, grade="C"):
        """
        Initialize the sugar stream with the given parameters, and calculate properties
        Adapted from SugarStream in my old repo
        the new addition for inputs
        ml_purity is for calculating consistency of massecuite streams, everything for massecuite defaults to none if ml_purity is None (default input)
        CV is the coefficient of variance, usally 50 or so for C massecuite, 30-40 is good for other massecuites.
        L is the average crystal size in mm. 0.1 for grain, 0.25 for C massecuite, 0.4-0.5 for B, and 0.6 to 1.0 for A
        grade is "C" (default, C/final molasses and massecuite) or "high" (A/B, high grade) - selects the
            power-law consistency constant and flow behavior index n from Rein (see sugar_stream_properties_fluids
            .MOLASSES_GRADE_PROPERTIES). Use "high" when this stream represents A or B molasses/massecuite.

        Molasses and massecuite flow behavior is modeled with Rein's power-law (Ostwald-de Waele) equations
        (tau = K * gamma_dot ** n) rather than a single Newtonian viscosity, because that's what Rein's own
        pressure-loss-in-piping formulas (eq. 16.17) are built on. K (the "consistency") is given in Pa*s^n -
        it is NOT directly comparable to a Newtonian viscosity in cP. Use head_loss() to get an actual
        pressure drop for a given pipe, which also reports an apparent viscosity (cP) at that flow's own
        shear rate, since apparent viscosity only means something once you know the shear rate.
        You can use the molasses consistency for syrup too, but those values are generally pretty low.
        You can use it for magma consistency too, but be aware that it just gives a general idea.
        """
        SugarStreamFluids._count += 1
        self.stream_id = SugarStreamFluids._count
        self.brix = brix
        self.purity = purity
        self.flow_lb_per_hr = flow_lb_per_hr
        self.temp_deg_F = temp_deg_F
        self.pressure_psia = pressure_psia
        self.level_ft = level_ft
        self.ml_purity = ml_purity # for massecuite consistency calcs
        self.SUCROSE_SG = 1.587 # SPECIFIC GRAVITY OF PURE SUCROSE
        self.CV = CV # coefficient of variance, usually 50 for C massecuite, maybe 30-40 for A and B massecuite and grain
        self.L = L # average crystal size in mm, usually 0.25 for C massecuite, 0.5 for B, 0.8 for A, 0.10 for Grain. Numbers will vary
        self.grade = grade # "C" or "high" - selects the molasses power-law constants (see MOLASSES_GRADE_PROPERTIES)
    
    @property
    def pol(self):
        return self.purity * self.brix / 100 if self.brix > 0 and self.purity > 0 else 0
    
    @property
    def boiling_point_elevation_deg_F(self):
        return bpe_total(self.level_ft, self.brix, self.pressure_psia) if self.brix > 0 else 0
    
    @property
    def cp_btu_per_lb_deg_F(self):
        return get_cp(self.brix) if self.brix > 0 else 1
    
    @property
    def specific_gravity(self):
        return specific_gravity(self.brix) if self.brix > 0 else 1
    
    @property
    def cu_ft_hr(self):
        return self.flow_lb_per_hr / (62.4 * self.specific_gravity)
    
    @property
    def latent_heat_btu_per_lb(self):
        return get_latent_heat(self.pressure_psia) if self.pressure_psia > 0 else 0
    
    @property
    def vapor_saturation_temp_deg_F(self):
        return sat_steam_temp(self.pressure_psia) if self.pressure_psia > 0 else 0
    
    @property
    def solids_flow(self):
        return self.brix * self.flow_lb_per_hr / 100
    
    @property
    def pol_flow(self):
        return self.pol * self.flow_lb_per_hr / 100

    @property
    def flow_behavior_index_n(self):
        return molasses_flow_behavior_index(self.grade)

    @property
    def molasses_consistency_Pa_sn(self):
        return molasses_consistency(brix=self.brix, purity=self.purity, temp_deg_F=self.temp_deg_F, grade=self.grade)

    @property
    def crystal_content_perc_DS(self):
        return (self.purity - self.ml_purity) / (100 - self.ml_purity) * 100 if self.ml_purity is not None else None

    @property
    def crystal_content_perc(self):
        return self.crystal_content_perc_DS * self.brix / 100 if self.ml_purity is not None else None

    @property
    def ml_brix(self):
        perc_mass_in_mother_liquor = 100 - self.crystal_content_perc # mass meaning mass, not massecuite
        perc_brix_in_mother_liquor = self.brix - self.crystal_content_perc
        return perc_brix_in_mother_liquor / perc_mass_in_mother_liquor * 100 if self.ml_purity is not None else None

    @property
    def ml_specific_gravity(self):
        return specific_gravity(self.ml_brix) if self.ml_purity is not None else None

    @property
    def volume_fraction_crystals(self):
        # basis 100 kg massecuite, water density 1000 kg / m3
        volume_total = 100 / (self.specific_gravity * 1000) # m3
        volume_sucrose = self.crystal_content_perc / (self.SUCROSE_SG * 1000) # m3
        return volume_sucrose / volume_total if self.ml_purity is not None else None

    @property
    def volume_ratio_crystals_to_mother_liq(self):
        frac_ml = 1 - self.volume_fraction_crystals
        return self.volume_fraction_crystals / frac_ml

    @property
    def mother_liquor_consistency_Pa_sn(self):
        if self.ml_purity is not None:
            return molasses_consistency(brix=self.ml_brix, purity=self.ml_purity, temp_deg_F=self.temp_deg_F, grade=self.grade)
        else:
            return None

    @property
    def massecuite_relative_viscosity(self):
        return massecuite_relative_viscosity(L=self.L, V=self.volume_ratio_crystals_to_mother_liq, CV=self.CV) if self.ml_purity is not None else None

    @property
    def massecuite_consistency_Pa_sn(self):
        if self.ml_purity is not None:
            return massecuite_viscosity(mu_rel=self.massecuite_relative_viscosity, mu_mother_liquor=self.mother_liquor_consistency_Pa_sn)
        else:
            return None

    def head_loss(self, pipe_ID_inches, pipe_length_ft, use_massecuite=False, K_override=None, n_override=None,
                  fittings=None, elevation_change_ft=0.0):
        """
        Friction head loss, fitting/valve losses, elevation change, and total
        pressure drop for this stream flowing through a pipe, using Rein's
        power-law (Ostwald-de Waele) laminar flow equations (consistency K from
        molasses_consistency, friction head loss from head_loss_meters, fitting
        losses from the Hooper 2-K method via total_fittings_K).

        Velocity is computed from this stream's own flow_lb_per_hr and specific_gravity
        (the bulk stream properties - i.e. the whole massecuite, crystals included, when
        ml_purity is set), same as everywhere else in this class.

        Args:
            pipe_ID_inches: Pipe inside diameter, inches.
            pipe_length_ft: Pipe length, ft.
            use_massecuite: If True, use massecuite_consistency_Pa_sn (mother
                liquor consistency x relative viscosity) instead of the plain
                molasses_consistency_Pa_sn. Requires ml_purity to be set. Ignored
                if K_override is given.
            K_override: If given, use this consistency (Pa*s^n) directly instead
                of computing it from brix/purity/temp/grade - e.g. a viscosity
                (Pa*s) known from a lab test or a trusted chart. Pass n_override=1.0
                alongside it for a plain Newtonian viscosity.
            n_override: If given, use this flow behavior index directly instead
                of the grade-based one.
            fittings: Optional list of (k1, k_max, qty) tuples (see TWO_K /
                flatten_two_k in sugar_stream_properties_fluids.py) - fitting
                and valve losses, evaluated at this flow's own generalized
                Reynolds number (Rein eq. 16.14) and pipe ID.
            elevation_change_ft: Outlet elevation minus inlet elevation, ft.
                Positive if the discharge point is higher than the source;
                added directly to the friction + fittings head loss.

        Returns:
            dict with velocity_fps, K_Pa_sn, n, Re, friction_head_loss_ft,
            fittings_K, fittings_head_loss_ft, elevation_change_ft,
            head_loss_ft (total), pressure_loss_psi (total), and
            apparent_viscosity_cP (the Newtonian-equivalent viscosity at this
            flow's own wall shear rate - only meaningful for this specific
            velocity/pipe combination, not a fixed fluid property).
        """
        if K_override is not None:
            K = K_override
        else:
            if use_massecuite and self.ml_purity is None:
                raise ValueError("use_massecuite=True requires ml_purity to be set")
            K = self.massecuite_consistency_Pa_sn if use_massecuite else self.molasses_consistency_Pa_sn

        n = n_override if n_override is not None else self.flow_behavior_index_n

        D_m = pipe_ID_inches * 0.0254
        L_m = pipe_length_ft * 0.3048
        A_m2 = np.pi / 4.0 * D_m ** 2

        rho_lbft3 = self.specific_gravity * 62.4
        rho_kgm3 = rho_lbft3 * 16.0184634
        mass_flow_kgs = self.flow_lb_per_hr * 0.45359237 / 3600.0
        V_ms = (mass_flow_kgs / rho_kgm3) / A_m2

        Re = reynolds_number_molasses_massecuite(D=D_m, u=V_ms, rho=rho_kgm3, K=K, n=n)

        friction_h_m = head_loss_meters(K=K, L=L_m, D=D_m, n=n, u=V_ms, rho=rho_kgm3)
        friction_h_ft = m_to_ft(friction_h_m)

        fittings_K = total_fittings_K(fittings, Re=Re, D_inches=pipe_ID_inches) if fittings else 0.0
        fittings_h_m = head_loss_meters_fittings(fittings_K, u=V_ms)
        fittings_h_ft = m_to_ft(fittings_h_m)

        total_h_ft = friction_h_ft + fittings_h_ft + elevation_change_ft
        total_dP_psi = head_ft_to_psi(total_h_ft, rho_lbft3)

        gamma_w = ((3 * n + 1) / (4 * n)) * (8 * V_ms / D_m)
        mu_app_cP = K * gamma_w ** (n - 1) * 1000.0

        return {
            "velocity_fps": V_ms * 3.280839895,
            "K_Pa_sn": K,
            "n": n,
            "Re": Re,
            "friction_head_loss_ft": friction_h_ft,
            "fittings_K": fittings_K,
            "fittings_head_loss_ft": fittings_h_ft,
            "elevation_change_ft": elevation_change_ft,
            "head_loss_ft": total_h_ft,
            "pressure_loss_psi": total_dP_psi,
            "apparent_viscosity_cP": mu_app_cP,
        }

    def current_temp_to_bpe_plus_vapor_temp(self):
        """Sets the current temp to the vapor boiling temp + boiling point elevation, useful in evaporator calculations"""
        self.temp_deg_F = self.vapor_saturation_temp_deg_F + self.boiling_point_elevation_deg_F

    def evaporate(self, new_brix=65, new_temp=140):
        """A quick function to transform into syrup, convenient for clarified juice --> syrup for Pan Floor calcs"""
        current_solids = self.solids_flow
        new_flow = 100 / new_brix * current_solids
        # update self
        self.flow_lb_per_hr = new_flow
        self.brix = new_brix
        self.temp_deg_F = new_temp

    def properties(self) -> dict:
        cls = type(self)
        prop_names = [k for k, v in vars(cls).items() if isinstance(v, property)]
        instance_vars = vars(self)
        return {**instance_vars, **{k: getattr(self, k) for k in prop_names}}
    
    def __repr__(self):
        return (f"SugarStreamFluids(brix={self.brix:.2f}, purity={self.purity:.2f}, "
                f"flow={self.flow_lb_per_hr:,.2f} lb/hr, temp={self.temp_deg_F:.2f}°F, "
                f"pressure={self.pressure_psia:.2f} psia, level={self.level_ft:.1f} ft)")
    
    def display_properties(self):
        """Display the properties of the sugar stream in a readable format"""
        props = self.properties()
        for key, value in props.items():
            if isinstance(value, (int, float)):
                print(f"{key}: {value:,.5f}")
            else:
                print(f"{key}: {value}")

    @classmethod
    def copy(cls, stream: 'SugarStreamFluids', **overrides):
        """Create a copy of the stream with optional overrides for any properties"""
        params = {
            'brix': stream.brix,
            'purity': stream.purity,
            'flow_lb_per_hr': stream.flow_lb_per_hr,
            'temp_deg_F': stream.temp_deg_F,
            'pressure_psia': stream.pressure_psia,
            'level_ft': stream.level_ft,
            'ml_purity': stream.ml_purity,
            'CV': stream.CV,
            'L': stream.L,
            'grade': stream.grade,
        }
        params.update(overrides)
        return cls(**params)

if __name__ == "__main__":
    # Example usage
    my_stream = SugarStreamFluids(brix=93, purity=55, flow_lb_per_hr=84000, temp_deg_F=113, pressure_psia=14.7, level_ft=0,
                                  ml_purity=33, CV=50, L=0.25, grade="C")
    print(my_stream.properties())
    my_stream.display_properties()
    print(my_stream.head_loss(pipe_ID_inches=24, pipe_length_ft=100, use_massecuite=True))

    