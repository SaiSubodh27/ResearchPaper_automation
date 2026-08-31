"""
Material Science Taxonomy & Keyword Definitions
"""

from typing import List, Dict

MATERIAL_SCIENCE_SUBFIELDS: Dict[str, List[str]] = {
    "energy_materials": [
        "battery materials", "lithium ion battery", "solid state electrolyte",
        "cathode material", "anode material", "sodium ion battery"
    ],
    "perovskites_photovoltaics": [
        "perovskite solar cells", "halide perovskites", "photovoltaic materials",
        "solar cell efficiency", "photoanode"
    ],
    "nanomaterials_2d": [
        "graphene", "2D materials", "MXenes", "transition metal dichalcogenides",
        "nanoparticles", "nanocomposites", "carbon nanotubes"
    ],
    "alloys_metallurgy": [
        "high entropy alloys", "superalloys", "shape memory alloys",
        "metallurgy", "grain boundary", "microstructure"
    ],
    "polymers_biomaterials": [
        "conjugated polymers", "hydrogels", "biodegradable polymers",
        "polymer electrolytes", "biomaterials"
    ],
    "superconductors_quantum": [
        "high temperature superconductors", "topological insulators",
        "quantum materials", "ferroelectric materials"
    ],
    "materials_informatics": [
        "materials discovery", "density functional theory", "DFT calculation",
        "crystal structure prediction", "CALPHAD", "materials genome"
    ]
}

def get_default_queries() -> List[str]:
    """Returns a curated list of search queries covering major Material Science topics."""
    queries = [
        "material science discovery",
        "perovskite solar cells",
        "solid state battery materials",
        "graphene 2D materials",
        "high entropy alloys",
        "density functional theory materials"
    ]
    return queries
