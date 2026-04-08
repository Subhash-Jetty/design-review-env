"""
Design Catalog — Procedural Design Generation Engine

Generates realistic engineering designs across 4 domains with
planted flaws at configurable difficulty levels. Each design has:

  - 5-15 components with realistic engineering parameters
  - 1-6 planted flaws grounded in real engineering standards
  - Physics-backed parameters (stresses, loads, dimensions)
  - Standard references (AISC, ASME, AGMA, IBC)

Domains:
  1. Bridge Truss (Warren/Pratt/Howe)
  2. Pressure Vessel (Cylindrical/Spherical)
  3. Gear Assembly (Spur/Helical)
  4. Building Frame (Multi-story steel)
"""

import random
import math
from typing import Dict, Any, List, Tuple


# ── Constants ────────────────────────────────────────────────────────────

DIFFICULTY_CONFIG = {
    "easy": {"num_components": (5, 7), "num_flaws": (1, 2), "max_steps": 20, "flaw_obviousness": "high"},
    "medium": {"num_components": (7, 10), "num_flaws": (2, 4), "max_steps": 30, "flaw_obviousness": "medium"},
    "hard": {"num_components": (10, 15), "num_flaws": (3, 6), "max_steps": 40, "flaw_obviousness": "low"},
}


# ── Bridge Truss Generator ──────────────────────────────────────────────

def _generate_bridge_truss(rng: random.Random, difficulty: str) -> Tuple[Dict[str, Dict], List[Dict], Dict]:
    """Generate a bridge truss design with components and planted flaws."""
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_comp = rng.randint(*cfg["num_components"])

    truss_types = ["Warren", "Pratt", "Howe", "K-truss"]
    truss_type = rng.choice(truss_types)
    span_m = rng.choice([15, 20, 25, 30, 40])
    design_load_kn = rng.choice([100, 150, 200, 250])

    components = {}
    flaw_candidates = []

    # Top/bottom chords
    for i, pos in enumerate(["top_chord", "bottom_chord"]):
        comp_id = f"{pos}_{i+1}"
        depth = rng.choice([200, 250, 300, 350, 400])
        flange_t = rng.choice([8, 10, 12, 14, 16])
        I = int(depth ** 3 * flange_t * 0.04)  # approximate I-beam
        components[comp_id] = {
            "component_type": "chord",
            "name": f"{pos.replace('_', ' ').title()}",
            "profile": f"W{depth}x{int(depth*0.15)}",
            "material": "A992 Steel",
            "depth_mm": depth,
            "flange_thickness_mm": flange_t,
            "length_m": span_m / 2,
            "moment_of_inertia_mm4": I,
            "max_load_kn": design_load_kn,
            "axial_load_kn": design_load_kn * 0.7,
            "k_factor": 1.0,
        }

    # Diagonal members
    num_diags = min(num_comp - 4, rng.randint(3, 6))
    for i in range(num_diags):
        comp_id = f"diagonal_{i+1}"
        angle = rng.choice([45, 50, 55, 60])
        length = span_m / (2 * math.cos(math.radians(angle)))
        depth = rng.choice([100, 120, 150, 180])
        flange_t = rng.choice([6, 8, 10])
        I = int(depth ** 3 * flange_t * 0.03)
        components[comp_id] = {
            "component_type": "member",
            "name": f"Diagonal Member {i+1}",
            "profile": f"L{depth}x{depth}x{flange_t}",
            "material": "A36 Steel",
            "depth_mm": depth,
            "flange_thickness_mm": flange_t,
            "length_m": round(length, 2),
            "moment_of_inertia_mm4": I,
            "max_load_kn": design_load_kn * 0.4,
            "axial_load_kn": design_load_kn * 0.35,
            "k_factor": 1.0,
            "angle_degrees": angle,
        }

    # Gusset plates
    num_gussets = min(num_comp - len(components) - 1, rng.randint(1, 3))
    for i in range(num_gussets):
        comp_id = f"gusset_plate_{i+1}"
        num_bolts = rng.choice([4, 6, 8])
        bolt_dia = rng.choice([16, 20, 22, 24])
        weld_size = rng.choice([3, 4, 5, 6, 8])
        components[comp_id] = {
            "component_type": "connection",
            "name": f"Gusset Plate GP-{i+1}",
            "material": "A36 Steel",
            "thickness_mm": rng.choice([10, 12, 16, 20]),
            "num_bolts": num_bolts,
            "bolt_diameter_mm": bolt_dia,
            "bolt_type": "A325",
            "weld_size_mm": weld_size,
            "weld_length_mm": rng.choice([80, 100, 120, 150, 200]),
            "weld_demand_kn": design_load_kn * 0.3,
            "bolt_demand_kn": design_load_kn * 0.25,
        }

    # Bearing / support
    comp_id = "bearing_pad_1"
    components[comp_id] = {
        "component_type": "bearing",
        "name": "Bearing Pad (West Abutment)",
        "material": "Neoprene Pad",
        "width_mm": rng.choice([200, 250, 300]),
        "length_mm": rng.choice([300, 400, 500]),
        "thickness_mm": rng.choice([25, 38, 50]),
        "max_bearing_pressure_mpa": 7.0,
        "applied_pressure_mpa": round(design_load_kn / (0.3 * 0.4) / 1000, 2),
    }

    # Generate flaws
    flaws = _plant_flaws_bridge(rng, components, difficulty, design_load_kn)

    design_info = {
        "design_type": "bridge_truss",
        "truss_type": truss_type,
        "span_m": span_m,
        "design_load_kn": design_load_kn,
        "summary": f"A single-span {truss_type} truss bridge ({span_m}m span) designed for {design_load_kn}kN vehicular loading. Steel structure conforming to AISC 360-22.",
        "requirements": f"Must support {design_load_kn}kN cyclic loading. Max deflection L/360. All steel per AISC 360-22. Welds per AWS D1.1. Bolts per RCSC specification.",
        "applicable_standards": ["AISC 360-22", "AWS D1.1", "AASHTO LRFD", "RCSC Bolt Spec"],
    }

    return components, flaws, design_info


def _plant_flaws_bridge(rng, components, difficulty, design_load):
    """Plant realistic flaws in bridge components."""
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_flaws = rng.randint(*cfg["num_flaws"])
    flaws = []
    comp_ids = list(components.keys())
    rng.shuffle(comp_ids)

    flaw_pool = [
        lambda cid: {
            "component_id": cid,
            "issue_type": "structural",
            "severity": "major",
            "description": f"Flange thickness ({components[cid].get('flange_thickness_mm', 8)}mm) is below AISC minimum for the applied loading. Requires min {components[cid].get('flange_thickness_mm', 8) + 4}mm.",
            "standard": "AISC 360-22 Section F2",
            "flaw_action": lambda c: c.update({"flange_thickness_mm": max(4, c.get("flange_thickness_mm", 8) - 4)}),
        },
        lambda cid: {
            "component_id": cid,
            "issue_type": "safety",
            "severity": "critical",
            "description": f"Weld size ({components[cid].get('weld_size_mm', 3)}mm) is insufficient for dynamic bridge loads. AISC Table J2.4 requires minimum {components[cid].get('weld_size_mm', 3) + 3}mm for this material thickness.",
            "standard": "AISC 360-22 Table J2.4",
            "flaw_action": lambda c: c.update({"weld_size_mm": max(2, c.get("weld_size_mm", 5) - 3)}),
        },
        lambda cid: {
            "component_id": cid,
            "issue_type": "dimensional",
            "severity": "major",
            "description": f"Member length ({components[cid].get('length_m', 5)}m) with current cross-section produces slenderness ratio exceeding AISC limit of 200 for compression members.",
            "standard": "AISC 360-22 Section E2",
            "flaw_action": lambda c: c.update({"length_m": c.get("length_m", 5) * 1.5}),
        },
        lambda cid: {
            "component_id": cid,
            "issue_type": "material",
            "severity": "minor",
            "description": "Material specification uses A36 Steel where A992 is required for primary structural members in bridge applications per AASHTO LRFD.",
            "standard": "AASHTO LRFD Section 6.4.1",
            "flaw_action": lambda c: None,
        },
        lambda cid: {
            "component_id": cid,
            "issue_type": "fatigue",
            "severity": "critical",
            "description": f"Connection detail category E' with {components[cid].get('num_bolts', 4)} bolts at this stress range has fatigue life below 2 million cycles required for bridge service.",
            "standard": "AISC 360-22 Appendix 3",
            "flaw_action": lambda c: c.update({"num_bolts": max(2, c.get("num_bolts", 4) - 2)}),
        },
        lambda cid: {
            "component_id": cid,
            "issue_type": "tolerance",
            "severity": "minor",
            "description": f"Bolt hole spacing ({components[cid].get('bolt_diameter_mm', 20) * 2.5:.0f}mm) is below the minimum edge distance requirement of {components[cid].get('bolt_diameter_mm', 20) * 3:.0f}mm.",
            "standard": "AISC 360-22 Table J3.4",
            "flaw_action": lambda c: None,
        },
    ]

    for i in range(min(num_flaws, len(comp_ids))):
        cid = comp_ids[i]
        valid_flaws = [f for f in flaw_pool if _flaw_applicable(f, cid, components)]
        if valid_flaws:
            flaw_fn = rng.choice(valid_flaws)
            flaw = flaw_fn(cid)
            flaw.pop("flaw_action", None)
            flaws.append(flaw)
            flaw_pool.remove(flaw_fn)

    return flaws


def _flaw_applicable(flaw_fn, cid, components):
    """Check if a flaw template is applicable to a component."""
    try:
        flaw = flaw_fn(cid)
        issue = flaw.get("issue_type", "")
        comp = components[cid]
        ct = comp.get("component_type", "")
        if issue == "structural" and ct not in ("chord", "member", "beam", "column", "brace"):
            return False
        if issue == "safety" and "weld_size_mm" not in comp:
            return False
        if issue == "fatigue" and "num_bolts" not in comp:
            return False
        if issue == "tolerance" and "bolt_diameter_mm" not in comp:
            return False
        if issue == "dimensional" and "length_m" not in comp:
            return False
        return True
    except Exception:
        return False


# ── Pressure Vessel Generator ────────────────────────────────────────────

def _generate_pressure_vessel(rng: random.Random, difficulty: str) -> Tuple[Dict, List, Dict]:
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_comp = rng.randint(*cfg["num_components"])

    vessel_type = rng.choice(["cylindrical", "spherical"])
    design_pressure = rng.choice([1.0, 1.5, 2.0, 3.0, 5.0])
    inner_radius = rng.choice([300, 500, 750, 1000])
    shell_thickness = rng.choice([6, 8, 10, 12, 16, 20])

    components = {}

    # Main shell
    components["shell_1"] = {
        "component_type": "shell",
        "name": "Main Cylindrical Shell",
        "material": "SA-516 Gr70",
        "vessel_type": vessel_type,
        "inner_radius_mm": inner_radius,
        "wall_thickness_mm": shell_thickness,
        "length_mm": rng.choice([2000, 3000, 4000, 5000]),
        "design_pressure_mpa": design_pressure,
        "design_temperature_c": rng.choice([150, 200, 250, 300, 350]),
        "corrosion_allowance_mm": rng.choice([1.5, 2.0, 3.0]),
    }

    # Heads
    for i, pos in enumerate(["left_head", "right_head"]):
        head_type = rng.choice(["ellipsoidal_2:1", "hemispherical", "torispherical"])
        components[pos] = {
            "component_type": "shell",
            "name": f"{pos.replace('_', ' ').title()} ({head_type})",
            "material": "SA-516 Gr70",
            "head_type": head_type,
            "inner_radius_mm": inner_radius,
            "wall_thickness_mm": shell_thickness + rng.choice([-2, 0, 2]),
            "design_pressure_mpa": design_pressure,
            "crown_radius_mm": inner_radius * (0.9 if head_type == "torispherical" else 1.0),
        }

    # Nozzles
    num_nozzles = min(num_comp - 4, rng.randint(2, 4))
    for i in range(num_nozzles):
        nozzle_dia = rng.choice([50, 80, 100, 150, 200])
        components[f"nozzle_{i+1}"] = {
            "component_type": "nozzle",
            "name": f"Nozzle N-{i+1} ({rng.choice(['inlet', 'outlet', 'drain', 'vent'])})",
            "material": "SA-516 Gr70",
            "inner_diameter_mm": nozzle_dia,
            "inner_radius_mm": nozzle_dia / 2,
            "wall_thickness_mm": rng.choice([4, 6, 8, 10]),
            "design_pressure_mpa": design_pressure,
            "reinforcement_pad_mm": rng.choice([0, 6, 10, 12]),
            "weld_size_mm": rng.choice([3, 4, 5, 6]),
            "weld_length_mm": round(math.pi * nozzle_dia, 0),
            "weld_demand_kn": design_pressure * nozzle_dia * 0.5,
        }

    # Flanges
    if len(components) < num_comp:
        components["flange_1"] = {
            "component_type": "flange",
            "name": "Main Manway Flange (ASME B16.5)",
            "material": "SA-105",
            "nominal_size_mm": 450,
            "pressure_class": rng.choice([150, 300, 600]),
            "num_bolts": rng.choice([16, 20, 24]),
            "bolt_diameter_mm": rng.choice([20, 22, 24, 27]),
            "gasket_type": rng.choice(["spiral_wound", "ring_joint", "flat"]),
            "bolt_demand_kn": design_pressure * 200,
        }

    # Support saddle
    if len(components) < num_comp:
        components["saddle_1"] = {
            "component_type": "support",
            "name": "Saddle Support S-1",
            "material": "A36 Steel",
            "contact_angle_degrees": rng.choice([120, 150, 180]),
            "weld_size_mm": rng.choice([5, 6, 8]),
            "weld_length_mm": rng.choice([200, 300, 400]),
            "weld_demand_kn": design_pressure * inner_radius * 0.1,
        }

    # Plant flaws
    flaws = _plant_flaws_vessel(rng, components, difficulty, design_pressure)

    design_info = {
        "design_type": "pressure_vessel",
        "vessel_type": vessel_type,
        "design_pressure_mpa": design_pressure,
        "inner_radius_mm": inner_radius,
        "summary": f"A {vessel_type} pressure vessel (ID={inner_radius*2}mm) rated for {design_pressure}MPa service. Construction per ASME BPVC Section VIII Division 1.",
        "requirements": f"Design pressure {design_pressure}MPa. Hydrotest at {design_pressure * 1.5}MPa. All welds radiographically examined. PWHT required above 32mm thickness.",
        "applicable_standards": ["ASME BPVC VIII-1", "ASME B16.5", "ASME B31.3", "AWS D1.1"],
    }

    return components, flaws, design_info


def _plant_flaws_vessel(rng, components, difficulty, design_pressure):
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_flaws = rng.randint(*cfg["num_flaws"])
    flaws = []
    comp_ids = list(components.keys())
    rng.shuffle(comp_ids)

    flaw_templates = [
        {"issue_type": "structural", "severity": "critical",
         "description": "Wall thickness is below ASME minimum required thickness for the design pressure. Hoop stress exceeds allowable.",
         "standard": "ASME BPVC VIII-1 UG-27", "needs": "wall_thickness_mm"},
        {"issue_type": "safety", "severity": "critical",
         "description": "Nozzle opening lacks adequate reinforcement per ASME UG-37. Area replacement insufficient.",
         "standard": "ASME BPVC VIII-1 UG-37", "needs": "reinforcement_pad_mm"},
        {"issue_type": "material", "severity": "major",
         "description": "Material SA-516 Gr70 requires PWHT above 32mm thickness per ASME UCS-56, but no PWHT is specified.",
         "standard": "ASME BPVC VIII-1 UCS-56", "needs": "wall_thickness_mm"},
        {"issue_type": "tolerance", "severity": "minor",
         "description": "Corrosion allowance of 1.5mm is inadequate for the specified service conditions (recommend 3.0mm minimum).",
         "standard": "ASME BPVC VIII-1 UG-25", "needs": "corrosion_allowance_mm"},
        {"issue_type": "safety", "severity": "major",
         "description": "Weld joint efficiency of 0.7 (spot RT) insufficient for vessel service. Full RT (E=1.0) required.",
         "standard": "ASME BPVC VIII-1 UW-12", "needs": "weld_size_mm"},
    ]

    for i in range(min(num_flaws, len(comp_ids), len(flaw_templates))):
        cid = comp_ids[i]
        comp = components[cid]
        for tmpl in flaw_templates:
            if tmpl["needs"] in comp and tmpl not in flaws:
                flaw = {
                    "component_id": cid,
                    "issue_type": tmpl["issue_type"],
                    "severity": tmpl["severity"],
                    "description": tmpl["description"],
                    "standard": tmpl["standard"],
                }
                flaws.append(flaw)
                flaw_templates.remove(tmpl)
                break

    return flaws


# ── Gear Assembly Generator ──────────────────────────────────────────────

def _generate_gear_assembly(rng: random.Random, difficulty: str) -> Tuple[Dict, List, Dict]:
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_comp = rng.randint(*cfg["num_components"])

    gear_type = rng.choice(["spur", "helical"])
    power_kw = rng.choice([5, 10, 15, 25, 50])
    rpm = rng.choice([500, 750, 1000, 1500, 1800])
    gear_ratio = rng.choice([2.0, 3.0, 4.0, 5.0])

    torque_nm = power_kw * 1000 / (2 * math.pi * rpm / 60)
    module = rng.choice([2, 3, 4, 5])
    pinion_teeth = rng.choice([18, 20, 24, 28])
    gear_teeth = int(pinion_teeth * gear_ratio)
    pinion_dia = module * pinion_teeth
    gear_dia = module * gear_teeth

    components = {}

    # Pinion
    components["pinion_1"] = {
        "component_type": "pinion",
        "name": f"Driving Pinion ({gear_type}, Z={pinion_teeth})",
        "material": "4140 Alloy Steel",
        "gear_type": gear_type,
        "num_teeth": pinion_teeth,
        "module_mm": module,
        "pitch_diameter_mm": pinion_dia,
        "face_width_mm": rng.choice([20, 25, 30, 40, 50]),
        "transmitted_force_n": round(torque_nm * 2 / (pinion_dia / 1000), 1),
        "hardness_hrc": rng.choice([28, 32, 40, 48, 55]),
        "allowable_contact_stress_mpa": rng.choice([1000, 1200, 1400]),
        "pressure_angle_deg": rng.choice([20, 25]),
    }

    # Gear
    components["gear_1"] = {
        "component_type": "gear",
        "name": f"Driven Gear ({gear_type}, Z={gear_teeth})",
        "material": "4140 Alloy Steel",
        "gear_type": gear_type,
        "num_teeth": gear_teeth,
        "module_mm": module,
        "pitch_diameter_mm": gear_dia,
        "face_width_mm": components["pinion_1"]["face_width_mm"],
        "transmitted_force_n": components["pinion_1"]["transmitted_force_n"],
        "hardness_hrc": components["pinion_1"]["hardness_hrc"] - rng.choice([0, 2, 5]),
        "allowable_contact_stress_mpa": rng.choice([1000, 1200, 1400]),
        "pressure_angle_deg": components["pinion_1"]["pressure_angle_deg"],
    }

    # Shafts
    for i, name in enumerate(["input_shaft", "output_shaft"]):
        shaft_dia = rng.choice([25, 30, 35, 40, 50])
        components[name] = {
            "component_type": "shaft",
            "name": f"{name.replace('_', ' ').title()}",
            "material": "4140 Alloy Steel",
            "diameter_mm": shaft_dia,
            "length_mm": rng.choice([150, 200, 250, 300]),
            "torque_nm": torque_nm if i == 0 else torque_nm * gear_ratio,
            "keyway_width_mm": rng.choice([6, 8, 10, 12]),
            "keyway_depth_mm": rng.choice([3, 4, 5, 6]),
        }

    # Bearings
    for i, name in enumerate(["bearing_A", "bearing_B"]):
        components[name] = {
            "component_type": "bearing",
            "name": f"Bearing {chr(65+i)} (Deep Groove Ball)",
            "bearing_designation": rng.choice(["6205", "6206", "6208", "6210"]),
            "bore_mm": rng.choice([25, 30, 40, 50]),
            "dynamic_load_rating_kn": rng.choice([14, 20, 30, 40]),
            "applied_radial_load_kn": round(torque_nm / 50, 1),
            "speed_rpm": rpm,
            "required_life_hours": rng.choice([10000, 20000, 50000]),
        }

    # Housing
    if len(components) < num_comp:
        components["housing_1"] = {
            "component_type": "housing",
            "name": "Gearbox Housing",
            "material": "Cast Iron",
            "wall_thickness_mm": rng.choice([6, 8, 10, 12]),
            "mounting_bolt_count": rng.choice([4, 6, 8]),
            "bolt_diameter_mm": rng.choice([10, 12, 16]),
            "bolt_demand_kn": power_kw * 2,
            "seal_type": rng.choice(["lip_seal", "labyrinth", "mechanical"]),
        }

    flaws = _plant_flaws_gear(rng, components, difficulty)

    design_info = {
        "design_type": "gear_assembly",
        "gear_type": gear_type,
        "power_kw": power_kw,
        "rpm": rpm,
        "gear_ratio": gear_ratio,
        "summary": f"A {gear_type} gear reducer ({power_kw}kW, {rpm}RPM input, ratio {gear_ratio}:1). Designed per AGMA 2001-D04.",
        "requirements": f"Transmit {power_kw}kW at {rpm}RPM. Gear ratio {gear_ratio}:1 ±2%. Minimum L10 bearing life 20,000 hours. All gears case-hardened to 55+ HRC per AGMA.",
        "applicable_standards": ["AGMA 2001-D04", "AGMA 2101-D04", "ISO 6336", "ISO 281"],
    }

    return components, flaws, design_info


def _plant_flaws_gear(rng, components, difficulty):
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_flaws = rng.randint(*cfg["num_flaws"])
    flaws = []
    comp_ids = list(components.keys())
    rng.shuffle(comp_ids)

    flaw_templates = [
        {"issue_type": "structural", "severity": "major",
         "description": "Face width is below AGMA recommended minimum (8-12× module). Risk of premature tooth failure.",
         "standard": "AGMA 2001-D04 Section 7", "needs": "face_width_mm"},
        {"issue_type": "material", "severity": "critical",
         "description": "Surface hardness (HRC) is below minimum for the contact stress level. Requires case hardening to 55+ HRC.",
         "standard": "AGMA 2001-D04 Table 3", "needs": "hardness_hrc"},
        {"issue_type": "fatigue", "severity": "major",
         "description": "Bearing L10 life is below the 20,000-hour requirement at the current loading and speed.",
         "standard": "ISO 281", "needs": "dynamic_load_rating_kn"},
        {"issue_type": "dimensional", "severity": "minor",
         "description": "Keyway depth exceeds 25% of shaft diameter, reducing shaft cross-section and torsional capacity significantly.",
         "standard": "DIN 6885", "needs": "keyway_depth_mm"},
        {"issue_type": "safety", "severity": "critical",
         "description": "Shaft diameter is undersized for the applied torque. Torsional shear stress exceeds allowable.",
         "standard": "ASME B106.1M (Shaft Design)", "needs": "diameter_mm"},
    ]

    for i in range(min(num_flaws, len(comp_ids), len(flaw_templates))):
        cid = comp_ids[i]
        comp = components[cid]
        for tmpl in flaw_templates:
            if tmpl["needs"] in comp and tmpl not in flaws:
                flaw = {
                    "component_id": cid,
                    "issue_type": tmpl["issue_type"],
                    "severity": tmpl["severity"],
                    "description": tmpl["description"],
                    "standard": tmpl["standard"],
                }
                flaws.append(flaw)
                flaw_templates.remove(tmpl)
                break

    return flaws


# ── Building Frame Generator ─────────────────────────────────────────────

def _generate_building_frame(rng: random.Random, difficulty: str) -> Tuple[Dict, List, Dict]:
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_comp = rng.randint(*cfg["num_components"])

    num_stories = rng.choice([2, 3, 4, 5])
    bay_width_m = rng.choice([6, 8, 9, 10])
    floor_load_kpa = rng.choice([2.5, 4.0, 5.0, 7.5])
    wind_speed_ms = rng.choice([30, 40, 50])

    components = {}

    # Columns
    num_cols = min(num_comp // 3, rng.randint(2, 4))
    for i in range(num_cols):
        depth = rng.choice([200, 250, 300, 350])
        flange_t = rng.choice([10, 12, 14, 16, 20])
        I = int(depth ** 3 * flange_t * 0.05)
        story_height = rng.choice([3.5, 4.0, 4.5])
        components[f"column_{i+1}"] = {
            "component_type": "column",
            "name": f"Column C-{i+1} (Line {chr(65+i)})",
            "profile": f"W{depth}x{int(depth*0.2)}",
            "material": "A992 Steel",
            "depth_mm": depth,
            "flange_thickness_mm": flange_t,
            "length_m": story_height * num_stories,
            "moment_of_inertia_mm4": I,
            "max_load_kn": floor_load_kpa * bay_width_m ** 2 * num_stories,
            "axial_load_kn": floor_load_kpa * bay_width_m ** 2 * num_stories * 0.8,
            "k_factor": rng.choice([0.65, 0.80, 1.0, 1.2]),
            "story_height_m": story_height,
        }

    # Beams
    num_beams = min(num_comp - len(components) - 2, rng.randint(2, 4))
    for i in range(num_beams):
        depth = rng.choice([250, 300, 360, 400, 450])
        flange_t = rng.choice([8, 10, 12, 14])
        I = int(depth ** 3 * flange_t * 0.04)
        components[f"beam_{i+1}"] = {
            "component_type": "beam",
            "name": f"Floor Beam B-{i+1} (Level {i+2})",
            "profile": f"W{depth}x{int(depth*0.15)}",
            "material": "A992 Steel",
            "depth_mm": depth,
            "flange_thickness_mm": flange_t,
            "length_m": bay_width_m,
            "moment_of_inertia_mm4": I,
            "max_load_kn": floor_load_kpa * bay_width_m * 1.0,
            "distributed_load_kn_m": floor_load_kpa * 1.0,
            "design_moment_kn_m": floor_load_kpa * bay_width_m ** 2 / 8,
        }

    # Bracing
    components["brace_1"] = {
        "component_type": "brace",
        "name": "Lateral Brace X-1",
        "profile": f"HSS{rng.choice([100, 125, 150])}x{rng.choice([100, 125, 150])}x{rng.choice([6, 8, 10])}",
        "material": "A500 Gr C" if rng.random() > 0.5 else "A36 Steel",
        "depth_mm": rng.choice([100, 125, 150]),
        "flange_thickness_mm": rng.choice([6, 8, 10]),
        "length_m": round(math.sqrt(bay_width_m ** 2 + 4 ** 2), 2),
        "moment_of_inertia_mm4": 500000,
        "axial_load_kn": wind_speed_ms * 2,
        "max_load_kn": wind_speed_ms * 2,
        "k_factor": 1.0,
    }

    # Base plate connection
    components["base_plate_1"] = {
        "component_type": "connection",
        "name": "Column Base Plate BP-1",
        "material": "A36 Steel",
        "thickness_mm": rng.choice([20, 25, 30, 38]),
        "num_bolts": rng.choice([4, 6, 8]),
        "bolt_diameter_mm": rng.choice([20, 22, 24, 30]),
        "bolt_type": "A325",
        "weld_size_mm": rng.choice([5, 6, 8, 10]),
        "weld_length_mm": rng.choice([200, 300, 400]),
        "weld_demand_kn": floor_load_kpa * bay_width_m * 5,
        "bolt_demand_kn": floor_load_kpa * bay_width_m * 3,
    }

    flaws = _plant_flaws_building(rng, components, difficulty)

    design_info = {
        "design_type": "building_frame",
        "num_stories": num_stories,
        "bay_width_m": bay_width_m,
        "floor_load_kpa": floor_load_kpa,
        "summary": f"A {num_stories}-story steel moment frame building ({bay_width_m}m bays), designed for {floor_load_kpa}kPa floor loading and {wind_speed_ms}m/s wind. Per AISC 360-22 and IBC.",
        "requirements": f"Floor load {floor_load_kpa}kPa. Wind {wind_speed_ms}m/s (Exposure C). Seismic Design Category D. Max drift H/400. All connections moment-resisting.",
        "applicable_standards": ["AISC 360-22", "AISC 341-22 (Seismic)", "IBC 2021", "ASCE 7-22"],
    }

    return components, flaws, design_info


def _plant_flaws_building(rng, components, difficulty):
    cfg = DIFFICULTY_CONFIG[difficulty]
    num_flaws = rng.randint(*cfg["num_flaws"])
    flaws = []
    comp_ids = list(components.keys())
    rng.shuffle(comp_ids)

    flaw_templates = [
        {"issue_type": "structural", "severity": "critical",
         "description": "Column slenderness ratio exceeds limits for the effective length factor (K). Buckling risk under combined axial + bending loads.",
         "standard": "AISC 360-22 Chapter E", "needs": "k_factor"},
        {"issue_type": "safety", "severity": "critical",
         "description": "Beam deflection exceeds L/360 serviceability limit under full live load. Visual sagging and cracking of finishes expected.",
         "standard": "AISC 360-22 Chapter L / IBC 1604.3", "needs": "distributed_load_kn_m"},
        {"issue_type": "dimensional", "severity": "major",
         "description": "Inter-story drift exceeds H/400 limit under design wind load. Non-structural damage likely.",
         "standard": "ASCE 7-22 Table 12.12-1", "needs": "story_height_m"},
        {"issue_type": "safety", "severity": "major",
         "description": "Base plate weld capacity is insufficient for combined shear and overturning moment from seismic forces.",
         "standard": "AISC 360-22 Chapter J", "needs": "weld_size_mm"},
        {"issue_type": "material", "severity": "minor",
         "description": "Bracing material A36 does not meet minimum toughness requirements for Seismic Design Category D per AISC 341.",
         "standard": "AISC 341-22 Section A3.1", "needs": "depth_mm"},
    ]

    for i in range(min(num_flaws, len(comp_ids), len(flaw_templates))):
        cid = comp_ids[i]
        comp = components[cid]
        for tmpl in flaw_templates:
            if tmpl["needs"] in comp and tmpl not in flaws:
                flaw = {
                    "component_id": cid,
                    "issue_type": tmpl["issue_type"],
                    "severity": tmpl["severity"],
                    "description": tmpl["description"],
                    "standard": tmpl["standard"],
                }
                flaws.append(flaw)
                flaw_templates.remove(tmpl)
                break

    return flaws


# ── Public API ───────────────────────────────────────────────────────────

DOMAIN_GENERATORS = {
    "bridge_truss": _generate_bridge_truss,
    "pressure_vessel": _generate_pressure_vessel,
    "gear_assembly": _generate_gear_assembly,
    "building_frame": _generate_building_frame,
}


def generate_design(
    domain: str = "bridge_truss",
    difficulty: str = "medium",
    seed: int = None,
) -> Tuple[Dict[str, Dict], List[Dict], Dict[str, Any]]:
    """
    Generate a complete engineering design with planted flaws.

    Args:
        domain: One of 'bridge_truss', 'pressure_vessel', 'gear_assembly', 'building_frame'
        difficulty: One of 'easy', 'medium', 'hard'
        seed: Random seed for reproducibility

    Returns:
        (components, flaws, design_info) tuple
    """
    if domain not in DOMAIN_GENERATORS:
        raise ValueError(f"Unknown domain: {domain}. Choose from {list(DOMAIN_GENERATORS.keys())}")
    if difficulty not in DIFFICULTY_CONFIG:
        raise ValueError(f"Unknown difficulty: {difficulty}. Choose from {list(DIFFICULTY_CONFIG.keys())}")

    rng = random.Random(seed)
    return DOMAIN_GENERATORS[domain](rng, difficulty)
