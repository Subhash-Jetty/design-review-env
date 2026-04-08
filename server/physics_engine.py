"""
Physics Engine — Lightweight Engineering Analysis

Provides realistic (but computationally cheap) engineering formulas
for structural analysis. This is NOT a full FEA solver, but uses
closed-form solutions from engineering handbooks to compute:

  - Beam bending stress and deflection (Euler-Bernoulli)
  - Column buckling load (Euler)
  - Pressure vessel hoop/longitudinal stress
  - Weld capacity (AISC)
  - Bolt shear/tension capacity
  - Gear contact stress (Hertzian/AGMA)
  - Safety factor computation

These calculations allow the environment to generate physics-verifiable
flaws — not just labels, but actual computations showing WHY a component
fails or passes.
"""

import math
from typing import Dict, Any, Optional


class PhysicsEngine:
    """Computes engineering analysis results for design components."""

    # ── Material Database ────────────────────────────────────────────────

    MATERIALS = {
        "A36 Steel": {
            "yield_strength_mpa": 250,
            "ultimate_strength_mpa": 400,
            "elastic_modulus_gpa": 200,
            "density_kg_m3": 7850,
            "poisson_ratio": 0.3,
        },
        "A992 Steel": {
            "yield_strength_mpa": 345,
            "ultimate_strength_mpa": 450,
            "elastic_modulus_gpa": 200,
            "density_kg_m3": 7850,
            "poisson_ratio": 0.3,
        },
        "A325 Bolt Steel": {
            "yield_strength_mpa": 635,
            "ultimate_strength_mpa": 830,
            "elastic_modulus_gpa": 200,
            "density_kg_m3": 7850,
            "poisson_ratio": 0.3,
        },
        "SA-516 Gr70": {
            "yield_strength_mpa": 260,
            "ultimate_strength_mpa": 485,
            "elastic_modulus_gpa": 200,
            "density_kg_m3": 7850,
            "poisson_ratio": 0.3,
        },
        "4140 Alloy Steel": {
            "yield_strength_mpa": 655,
            "ultimate_strength_mpa": 900,
            "elastic_modulus_gpa": 205,
            "density_kg_m3": 7850,
            "poisson_ratio": 0.29,
        },
        "6061-T6 Aluminum": {
            "yield_strength_mpa": 276,
            "ultimate_strength_mpa": 310,
            "elastic_modulus_gpa": 68.9,
            "density_kg_m3": 2700,
            "poisson_ratio": 0.33,
        },
        "Cast Iron": {
            "yield_strength_mpa": 130,
            "ultimate_strength_mpa": 200,
            "elastic_modulus_gpa": 100,
            "density_kg_m3": 7200,
            "poisson_ratio": 0.26,
        },
    }

    # ── Beam Analysis ────────────────────────────────────────────────────

    @staticmethod
    def beam_bending_stress(
        moment_kn_m: float,
        depth_mm: float,
        moment_of_inertia_mm4: float,
    ) -> Dict[str, Any]:
        """
        Compute bending stress using σ = M·y / I (Euler-Bernoulli).

        Args:
            moment_kn_m: Bending moment in kN·m
            depth_mm: Total depth of beam cross-section in mm
            moment_of_inertia_mm4: Moment of inertia in mm⁴
        """
        y = depth_mm / 2.0  # distance to extreme fiber
        M_nmm = moment_kn_m * 1e6  # convert kN·m to N·mm
        if moment_of_inertia_mm4 <= 0:
            return {"error": "Invalid moment of inertia", "stress_mpa": float("inf")}

        stress_mpa = abs(M_nmm * y / moment_of_inertia_mm4)
        return {
            "analysis": "beam_bending_stress",
            "formula": "σ = M·y / I",
            "moment_kn_m": moment_kn_m,
            "depth_mm": depth_mm,
            "y_mm": y,
            "I_mm4": moment_of_inertia_mm4,
            "stress_mpa": round(stress_mpa, 2),
            "unit": "MPa",
        }

    @staticmethod
    def beam_deflection(
        load_kn_m: float,
        length_m: float,
        elastic_modulus_gpa: float,
        moment_of_inertia_mm4: float,
    ) -> Dict[str, Any]:
        """
        Compute maximum deflection for uniformly loaded simply-supported beam.
        δ = 5·w·L⁴ / (384·E·I)
        """
        w = load_kn_m * 1.0  # kN/m
        L = length_m * 1000.0  # mm
        E = elastic_modulus_gpa * 1000.0  # MPa
        I = moment_of_inertia_mm4

        if E <= 0 or I <= 0:
            return {"error": "Invalid E or I", "deflection_mm": float("inf")}

        deflection_mm = (5 * w * L ** 4) / (384 * E * I)
        L_over_ratio = L / deflection_mm if deflection_mm > 0 else float("inf")

        return {
            "analysis": "beam_deflection",
            "formula": "δ = 5wL⁴ / (384EI)",
            "load_kn_m": load_kn_m,
            "length_m": length_m,
            "E_gpa": elastic_modulus_gpa,
            "I_mm4": I,
            "deflection_mm": round(deflection_mm, 3),
            "L_over_delta": round(L_over_ratio, 0),
            "limit_L_over_360": round(L / 360, 2),
            "passes_L360": deflection_mm <= L / 360,
            "unit": "mm",
        }

    # ── Column Buckling ──────────────────────────────────────────────────

    @staticmethod
    def euler_buckling(
        elastic_modulus_gpa: float,
        moment_of_inertia_mm4: float,
        length_m: float,
        k_factor: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Euler critical buckling load: P_cr = π²·E·I / (K·L)²
        """
        E = elastic_modulus_gpa * 1000.0  # MPa
        I = moment_of_inertia_mm4
        KL = k_factor * length_m * 1000.0  # mm

        if KL <= 0:
            return {"error": "Invalid effective length"}

        P_cr = (math.pi ** 2 * E * I) / (KL ** 2)
        P_cr_kn = P_cr / 1000.0

        return {
            "analysis": "euler_buckling",
            "formula": "P_cr = π²EI / (KL)²",
            "E_gpa": elastic_modulus_gpa,
            "I_mm4": I,
            "K_factor": k_factor,
            "length_m": length_m,
            "effective_length_mm": KL,
            "critical_load_kn": round(P_cr_kn, 2),
            "unit": "kN",
        }

    # ── Pressure Vessel ──────────────────────────────────────────────────

    @staticmethod
    def pressure_vessel_stress(
        internal_pressure_mpa: float,
        inner_radius_mm: float,
        wall_thickness_mm: float,
    ) -> Dict[str, Any]:
        """
        Thin-wall pressure vessel stresses:
          Hoop: σ_h = p·r / t
          Longitudinal: σ_l = p·r / (2·t)
        """
        p = internal_pressure_mpa
        r = inner_radius_mm
        t = wall_thickness_mm

        if t <= 0:
            return {"error": "Invalid wall thickness"}

        hoop = p * r / t
        longitudinal = p * r / (2 * t)
        ratio = r / t

        return {
            "analysis": "pressure_vessel_stress",
            "formula_hoop": "σ_h = p·r / t",
            "formula_long": "σ_l = p·r / (2t)",
            "pressure_mpa": p,
            "inner_radius_mm": r,
            "wall_thickness_mm": t,
            "r_over_t_ratio": round(ratio, 1),
            "thin_wall_valid": ratio >= 10,
            "hoop_stress_mpa": round(hoop, 2),
            "longitudinal_stress_mpa": round(longitudinal, 2),
            "governing_stress_mpa": round(hoop, 2),
            "unit": "MPa",
        }

    # ── Weld Capacity ────────────────────────────────────────────────────

    @staticmethod
    def weld_capacity(
        weld_size_mm: float,
        weld_length_mm: float,
        electrode_strength_mpa: float = 480,  # E70xx
    ) -> Dict[str, Any]:
        """
        Fillet weld capacity per AISC:
          R_w = 0.6 × F_EXX × t_w × L_w
          where t_w = 0.707 × weld_size (throat dimension)
        """
        t_w = 0.707 * weld_size_mm
        R_w = 0.6 * electrode_strength_mpa * t_w * weld_length_mm / 1000.0  # kN

        return {
            "analysis": "weld_capacity",
            "formula": "R_w = 0.6 × F_EXX × 0.707a × L",
            "weld_size_mm": weld_size_mm,
            "throat_mm": round(t_w, 2),
            "weld_length_mm": weld_length_mm,
            "electrode_strength_mpa": electrode_strength_mpa,
            "capacity_kn": round(R_w, 2),
            "unit": "kN",
        }

    # ── Bolt Capacity ────────────────────────────────────────────────────

    @staticmethod
    def bolt_capacity(
        bolt_diameter_mm: float,
        num_bolts: int,
        bolt_grade_mpa: float = 830,  # A325
        shear_planes: int = 1,
    ) -> Dict[str, Any]:
        """
        Bolt shear capacity:
          R_n = F_nv × A_b × n_bolts × n_planes
          F_nv = 0.45 × F_u (for bearing-type connections)
        """
        A_b = math.pi * (bolt_diameter_mm / 2) ** 2
        F_nv = 0.45 * bolt_grade_mpa
        R_n = F_nv * A_b * num_bolts * shear_planes / 1000.0  # kN

        return {
            "analysis": "bolt_shear_capacity",
            "formula": "R_n = 0.45·F_u · A_b · n · m",
            "bolt_diameter_mm": bolt_diameter_mm,
            "bolt_area_mm2": round(A_b, 1),
            "num_bolts": num_bolts,
            "shear_planes": shear_planes,
            "bolt_grade_mpa": bolt_grade_mpa,
            "nominal_shear_strength_mpa": round(F_nv, 1),
            "total_capacity_kn": round(R_n, 2),
            "unit": "kN",
        }

    # ── Gear Contact Stress ──────────────────────────────────────────────

    @staticmethod
    def gear_contact_stress(
        transmitted_force_n: float,
        pitch_diameter_mm: float,
        face_width_mm: float,
        elastic_modulus_gpa: float = 200,
        gear_ratio: float = 3.0,
    ) -> Dict[str, Any]:
        """
        Simplified Hertzian gear contact stress (AGMA):
          σ_H = Z_E × √(F_t × K_a / (d × b × Z_I))
        """
        E = elastic_modulus_gpa * 1000  # MPa
        Z_E = math.sqrt(E / (2 * math.pi * (1 - 0.3 ** 2)))
        K_a = 1.25  # application factor
        Z_I = (gear_ratio / (gear_ratio + 1)) / 2

        if pitch_diameter_mm <= 0 or face_width_mm <= 0 or Z_I <= 0:
            return {"error": "Invalid gear parameters"}

        inner = (transmitted_force_n * K_a) / (
            pitch_diameter_mm * face_width_mm * Z_I
        )
        sigma_H = Z_E * math.sqrt(abs(inner))

        return {
            "analysis": "gear_contact_stress",
            "formula": "σ_H = Z_E × √(F_t·K_a / (d·b·Z_I))",
            "transmitted_force_n": transmitted_force_n,
            "pitch_diameter_mm": pitch_diameter_mm,
            "face_width_mm": face_width_mm,
            "elastic_factor_Z_E": round(Z_E, 1),
            "geometry_factor_Z_I": round(Z_I, 4),
            "contact_stress_mpa": round(sigma_H, 1),
            "unit": "MPa",
        }

    # ── Safety Factor ────────────────────────────────────────────────────

    @staticmethod
    def safety_factor(
        capacity: float,
        demand: float,
    ) -> Dict[str, Any]:
        """Compute safety factor = Capacity / Demand."""
        if demand <= 0:
            sf = float("inf")
        else:
            sf = capacity / demand

        status = "PASS" if sf >= 1.5 else ("MARGINAL" if sf >= 1.0 else "FAIL")

        return {
            "analysis": "safety_factor",
            "formula": "SF = Capacity / Demand",
            "capacity": round(capacity, 2),
            "demand": round(demand, 2),
            "safety_factor": round(sf, 3),
            "status": status,
            "minimum_required": 1.5,
        }

    # ── Dispatcher ───────────────────────────────────────────────────────

    @classmethod
    def analyze_component(
        cls,
        component: Dict[str, Any],
        analysis_type: str,
    ) -> Dict[str, Any]:
        """
        Run a specific analysis on a component based on its parameters.
        Returns the analysis results dict.
        """
        comp_type = component.get("component_type", "")
        material_name = component.get("material", "A36 Steel")
        material = cls.MATERIALS.get(material_name, cls.MATERIALS["A36 Steel"])
        E = material["elastic_modulus_gpa"]
        Fy = material["yield_strength_mpa"]
        Fu = material["ultimate_strength_mpa"]

        if analysis_type == "stress":
            if comp_type in ("beam", "member", "chord", "brace"):
                moment = component.get("design_moment_kn_m", component.get("max_load_kn", 50) * component.get("length_m", 3) / 4)
                depth = component.get("depth_mm", 300)
                I = component.get("moment_of_inertia_mm4", 1.5e8)
                result = cls.beam_bending_stress(moment, depth, I)
                sf = cls.safety_factor(Fy, result["stress_mpa"])
                result["yield_strength_mpa"] = Fy
                result["safety_factor"] = sf["safety_factor"]
                result["status"] = sf["status"]
                return result
            elif comp_type in ("shell", "vessel", "nozzle"):
                p = component.get("design_pressure_mpa", 1.5)
                r = component.get("inner_radius_mm", 500)
                t = component.get("wall_thickness_mm", 10)
                result = cls.pressure_vessel_stress(p, r, t)
                sf = cls.safety_factor(Fy, result["hoop_stress_mpa"])
                result["yield_strength_mpa"] = Fy
                result["safety_factor"] = sf["safety_factor"]
                result["status"] = sf["status"]
                return result
            elif comp_type in ("gear", "pinion"):
                F = component.get("transmitted_force_n", 5000)
                d = component.get("pitch_diameter_mm", 100)
                b = component.get("face_width_mm", 30)
                result = cls.gear_contact_stress(F, d, b, E)
                allowable = component.get("allowable_contact_stress_mpa", 1200)
                sf = cls.safety_factor(allowable, result["contact_stress_mpa"])
                result["allowable_contact_stress_mpa"] = allowable
                result["safety_factor"] = sf["safety_factor"]
                result["status"] = sf["status"]
                return result
            else:
                return {"analysis": "stress", "error": f"No stress model for component type '{comp_type}'"}

        elif analysis_type == "deflection":
            w = component.get("distributed_load_kn_m", component.get("max_load_kn", 50) / max(component.get("length_m", 3), 0.1))
            L = component.get("length_m", 3)
            I = component.get("moment_of_inertia_mm4", 1.5e8)
            return cls.beam_deflection(w, L, E, I)

        elif analysis_type == "buckling":
            I = component.get("moment_of_inertia_mm4", 1.5e8)
            L = component.get("length_m", 3)
            K = component.get("k_factor", 1.0)
            result = cls.euler_buckling(E, I, L, K)
            applied = component.get("axial_load_kn", component.get("max_load_kn", 50))
            sf = cls.safety_factor(result["critical_load_kn"], applied)
            result["applied_load_kn"] = applied
            result["safety_factor"] = sf["safety_factor"]
            result["status"] = sf["status"]
            return result

        elif analysis_type == "weld_capacity":
            ws = component.get("weld_size_mm", 5)
            wl = component.get("weld_length_mm", 100)
            result = cls.weld_capacity(ws, wl)
            demand = component.get("weld_demand_kn", 50)
            sf = cls.safety_factor(result["capacity_kn"], demand)
            result["demand_kn"] = demand
            result["safety_factor"] = sf["safety_factor"]
            result["status"] = sf["status"]
            return result

        elif analysis_type == "bolt_capacity":
            bd = component.get("bolt_diameter_mm", 20)
            nb = component.get("num_bolts", 4)
            result = cls.bolt_capacity(bd, nb)
            demand = component.get("bolt_demand_kn", 100)
            sf = cls.safety_factor(result["total_capacity_kn"], demand)
            result["demand_kn"] = demand
            result["safety_factor"] = sf["safety_factor"]
            result["status"] = sf["status"]
            return result

        elif analysis_type == "safety_factor":
            capacity = component.get("capacity", component.get("max_load_kn", 100))
            demand = component.get("demand", component.get("applied_load_kn", 50))
            return cls.safety_factor(capacity, demand)

        else:
            return {
                "error": f"Unknown analysis type: {analysis_type}",
                "available_types": [
                    "stress", "deflection", "buckling",
                    "weld_capacity", "bolt_capacity", "safety_factor",
                ],
            }
