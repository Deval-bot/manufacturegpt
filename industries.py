# industries.py
# ════════════════════════════════════════════════════════════════
# THE KNOWLEDGE LAYER (Tier 1 — pre-built industry templates)
# ════════════════════════════════════════════════════════════════
# This file is the foundation of ManufactureGPT's anti-hallucination
# strategy. Each industry profile is rich, structured domain knowledge
# that gets injected into the LLM before it plans — so the AI reasons
# over REAL equipment, not its imagination.
#
# Design principle: SPECIFIC IN -> SPECIFIC OUT.
# The depth of these profiles directly determines output quality.
#
# Each profile contains:
#   display_name   : friendly name for the UI
#   description    : one-line industry context
#   equipment      : equipment_name -> list of valid API functions
#   data_types     : valid data types for this industry's signals
#   safety_rules   : industry-specific rules the validator enforces
#   reasoning_hints: what the LLM should think about for THIS industry
#   example_workflow: a few-shot example showing the EXPECTED depth
#   example_tasks  : ready-to-use prompts for the UI
# ════════════════════════════════════════════════════════════════


INDUSTRIES = {

    # ────────────────────────────────────────────────────────────
    # INDUSTRY 1: STEEL & METALS  (FLAGSHIP — grounded in SAIL-type plants)
    # ────────────────────────────────────────────────────────────
    "steel": {
        "display_name": "Steel & Metals Production",
        "description": (
            "Integrated steel plant processes from furnace to rolling mill — "
            "blast furnace, basic oxygen furnace, continuous casting, "
            "reheating and hot/cold rolling."
        ),
        "equipment": {
            "blast_furnace": [
                "chargeRawMaterial", "controlTemperature", "adjustAirBlast",
                "monitorPressure", "tapMoltenIron", "getTemperature"
            ],
            "basic_oxygen_furnace": [
                "chargeHotMetal", "blowOxygen", "addFlux",
                "measureCarbon", "tapSteel", "getTemperature"
            ],
            "ladle": [
                "receiveMolten", "addAlloys", "stir",
                "transport", "pourToCaster", "getTemperature"
            ],
            "continuous_caster": [
                "receiveLadle", "controlMoldLevel", "coolStrand",
                "cutSlab", "getCastingSpeed", "monitorTemperature"
            ],
            "reheating_furnace": [
                "loadSlab", "controlTemperature", "soakSlab",
                "dischargeSlab", "getTemperature"
            ],
            "rolling_mill": [
                "loadSlab", "rollPass", "adjustRollGap",
                "controlSpeed", "measureThickness", "coilProduct"
            ],
            "cooling_bed": [
                "receiveProduct", "controlCoolingRate",
                "monitorTemperature", "transferOut"
            ],
            "crane": [
                "lift", "transport", "lower", "getPosition", "reset"
            ],
            "sensor_system": [
                "measureTemperature", "measureThickness",
                "detectSurfaceDefect", "measureDimension", "getReading"
            ],
            "plc": [
                "sendSignal", "receiveSignal", "setOutput",
                "getInput", "activateInterlock"
            ]
        },
        "data_types": ["STRING", "DOUBLE", "INT", "BOOL", "ARRAY", "TEMPERATURE"],
        "safety_rules": [
            "Furnace must reach target temperature before tapping molten metal",
            "Ladle temperature must be verified before pouring to caster",
            "Crane must confirm clear path before transporting molten material",
            "PLC interlock must be active during any high-temperature operation",
            "Cooling rate must be controlled before product handling to avoid thermal stress"
        ],
        "reasoning_hints": (
            "Think about temperature sequencing — every thermal step must verify "
            "temperature before proceeding. Molten metal handling is safety-critical. "
            "Processes are largely sequential and continuous. Consider that material "
            "flows from furnace to refining to casting to rolling, with temperature "
            "control at every transfer."
        ),
        "example_workflow": {
            "task_name": "Slab Production from Molten Steel",
            "task_type": "sequential",
            "steps": [
                {
                    "step_id": 1,
                    "description": "Receive molten steel from BOF into the ladle and verify temperature",
                    "component": "ladle",
                    "api": "receiveMolten",
                    "input_data": {"type": "TEMPERATURE", "source": "user_input", "value": "molten_steel_temp"},
                    "output_data": {"type": "TEMPERATURE", "value": "ladle_temp_verified"}
                },
                {
                    "step_id": 2,
                    "description": "Add alloying elements to achieve target steel grade",
                    "component": "ladle",
                    "api": "addAlloys",
                    "input_data": {"type": "STRING", "source": "user_input", "value": "target_grade_spec"},
                    "output_data": {"type": "STRING", "value": "alloyed_composition"}
                },
                {
                    "step_id": 3,
                    "description": "Pour molten steel from ladle into the continuous caster mold",
                    "component": "ladle",
                    "api": "pourToCaster",
                    "input_data": {"type": "TEMPERATURE", "source": "step_1_output", "value": "ladle_temp_verified"},
                    "output_data": {"type": "BOOL", "value": "pour_complete"}
                },
                {
                    "step_id": 4,
                    "description": "Cool the strand in the continuous caster to solidify steel",
                    "component": "continuous_caster",
                    "api": "coolStrand",
                    "input_data": {"type": "BOOL", "source": "step_3_output", "value": "pour_complete"},
                    "output_data": {"type": "TEMPERATURE", "value": "solidified_strand_temp"}
                },
                {
                    "step_id": 5,
                    "description": "Cut the solidified strand into slabs of specified length",
                    "component": "continuous_caster",
                    "api": "cutSlab",
                    "input_data": {"type": "DOUBLE", "source": "user_input", "value": "target_slab_length"},
                    "output_data": {"type": "ARRAY", "value": "slab_dimensions"}
                }
            ]
        },
        "example_tasks": [
            "Charge raw material into the blast furnace, control temperature to tap molten iron, transport via ladle to the basic oxygen furnace, blow oxygen to refine into steel, then pour into the continuous caster to produce slabs",
            "Load a steel slab into the reheating furnace, soak to rolling temperature, transfer to the rolling mill, roll through multiple passes to target thickness, then coil the finished product",
            "Receive molten steel in the ladle, add alloying elements, stir for homogeneity, pour into the continuous caster, cool the strand, and cut slabs to length"
        ]
    },

    # ────────────────────────────────────────────────────────────
    # INDUSTRY 2: ELECTRONICS ASSEMBLY
    # ────────────────────────────────────────────────────────────
    "electronics": {
        "display_name": "Electronics Assembly",
        "description": (
            "Discrete component assembly — PCB population, CPU placement, "
            "connector assembly using robotic arms and vision systems."
        ),
        "equipment": {
            "robotic_arm": [
                "moveToPosition", "quickMove", "loadMove",
                "resetHome", "getPosition", "pickObject", "placeObject"
            ],
            "suction_cup": [
                "activate", "deactivate", "checkPressure", "grip", "release"
            ],
            "depth_camera": [
                "captureImage", "detectObjects", "getCoordinates", "saveImage"
            ],
            "vision_system": [
                "detectDefects", "classifyObject", "runInference", "getBoundingBoxes"
            ],
            "plc": [
                "sendSignal", "receiveSignal", "setOutput", "getInput"
            ],
            "conveyor": [
                "start", "stop", "setSpeed", "getPosition", "moveTo"
            ],
            "reset": [
                "reset", "returnHome", "initialize"
            ]
        },
        "data_types": ["STRING", "DOUBLE", "INT", "BOOL", "ARRAY"],
        "safety_rules": [
            "Robotic arm must move to a safe height before any horizontal move",
            "End effector must deactivate before arm returns home",
            "Vision detection must complete before pick operation begins",
            "Conveyor must stop before robotic arm enters its workspace"
        ],
        "reasoning_hints": (
            "Think about collision avoidance — arm moves to safe height first. "
            "Vision must locate before the arm picks. Processes are discrete and "
            "often sequential, but inspection can run in parallel. Always reset "
            "the arm to home at the end."
        ),
        "example_workflow": {
            "task_name": "CPU Placement on Motherboard",
            "task_type": "sequential",
            "steps": [
                {
                    "step_id": 1,
                    "description": "Capture image of parts tray to locate the CPU",
                    "component": "depth_camera",
                    "api": "captureImage",
                    "input_data": {"type": "STRING", "source": "user_input", "value": "tray_location"},
                    "output_data": {"type": "STRING", "value": "image_path"}
                },
                {
                    "step_id": 2,
                    "description": "Detect CPU coordinates from the captured image",
                    "component": "depth_camera",
                    "api": "getCoordinates",
                    "input_data": {"type": "STRING", "source": "step_1_output", "value": "image_path"},
                    "output_data": {"type": "ARRAY", "value": "cpu_coordinates"}
                },
                {
                    "step_id": 3,
                    "description": "Move robotic arm to a safe height above the CPU",
                    "component": "robotic_arm",
                    "api": "quickMove",
                    "input_data": {"type": "ARRAY", "source": "step_2_output", "value": "cpu_coordinates"},
                    "output_data": {"type": "ARRAY", "value": "position_above_cpu"}
                },
                {
                    "step_id": 4,
                    "description": "Activate suction cup to grip the CPU",
                    "component": "suction_cup",
                    "api": "activate",
                    "input_data": {"type": "ARRAY", "source": "step_3_output", "value": "position_above_cpu"},
                    "output_data": {"type": "BOOL", "value": "cpu_gripped"}
                },
                {
                    "step_id": 5,
                    "description": "Return robotic arm to home position",
                    "component": "robotic_arm",
                    "api": "resetHome",
                    "input_data": {"type": "BOOL", "source": "step_4_output", "value": "cpu_gripped"},
                    "output_data": {"type": "BOOL", "value": "arm_home"}
                }
            ]
        },
        "example_tasks": [
            "Use a robotic arm with suction cup to pick a CPU from a parts tray and place it onto a motherboard socket, then reset to home position",
            "Use a depth camera and robotic arm to detect and sort circular, square, and hexagonal components into bins by shape"
        ]
    },

    # ────────────────────────────────────────────────────────────
    # INDUSTRY 3: FOOD PROCESSING
    # ────────────────────────────────────────────────────────────
    "food": {
        "display_name": "Food Processing",
        "description": (
            "Food production lines — mixing, cooking, filling, packaging "
            "and quality inspection with traceability."
        ),
        "equipment": {
            "mixer": [
                "loadIngredients", "mix", "controlSpeed", "discharge", "getStatus"
            ],
            "oven": [
                "loadProduct", "setTemperature", "bake", "unload", "getTemperature"
            ],
            "filling_machine": [
                "receiveContainer", "fillProduct", "measureVolume", "dispense", "getFillLevel"
            ],
            "conveyor": [
                "start", "stop", "setSpeed", "getPosition"
            ],
            "metal_detector": [
                "scan", "detectContaminant", "rejectProduct", "getReading"
            ],
            "labelling_machine": [
                "applyLabel", "printBatchCode", "verifyLabel", "getStatus"
            ],
            "packaging_unit": [
                "wrapProduct", "sealPackage", "countUnits", "getStatus"
            ],
            "weighing_scale": [
                "measureWeight", "checkTolerance", "getReading"
            ],
            "plc": [
                "sendSignal", "receiveSignal", "setOutput", "getInput"
            ]
        },
        "data_types": ["STRING", "DOUBLE", "INT", "BOOL", "ARRAY", "TEMPERATURE", "WEIGHT"],
        "safety_rules": [
            "Metal detector must scan every product before packaging",
            "Oven temperature must be verified before loading product",
            "Weight must be within tolerance before labelling and packaging",
            "Batch code must be printed before product leaves the line for traceability"
        ],
        "reasoning_hints": (
            "Think about food safety and traceability — every product passes a "
            "metal detector before packaging, and a batch code is applied for "
            "traceability. Temperature control matters for cooking steps. "
            "Weight tolerance checks gate the packaging stage."
        ),
        "example_workflow": {
            "task_name": "Baked Product Line",
            "task_type": "sequential",
            "steps": [
                {
                    "step_id": 1,
                    "description": "Load ingredients into the mixer",
                    "component": "mixer",
                    "api": "loadIngredients",
                    "input_data": {"type": "ARRAY", "source": "user_input", "value": "ingredient_list"},
                    "output_data": {"type": "BOOL", "value": "ingredients_loaded"}
                },
                {
                    "step_id": 2,
                    "description": "Mix ingredients to a uniform batter",
                    "component": "mixer",
                    "api": "mix",
                    "input_data": {"type": "BOOL", "source": "step_1_output", "value": "ingredients_loaded"},
                    "output_data": {"type": "STRING", "value": "batter_ready"}
                },
                {
                    "step_id": 3,
                    "description": "Bake the product in the oven at set temperature",
                    "component": "oven",
                    "api": "bake",
                    "input_data": {"type": "TEMPERATURE", "source": "user_input", "value": "bake_temperature"},
                    "output_data": {"type": "STRING", "value": "baked_product"}
                },
                {
                    "step_id": 4,
                    "description": "Scan baked product with metal detector for contaminants",
                    "component": "metal_detector",
                    "api": "scan",
                    "input_data": {"type": "STRING", "source": "step_3_output", "value": "baked_product"},
                    "output_data": {"type": "BOOL", "value": "scan_passed"}
                },
                {
                    "step_id": 5,
                    "description": "Apply batch code label for traceability",
                    "component": "labelling_machine",
                    "api": "printBatchCode",
                    "input_data": {"type": "BOOL", "source": "step_4_output", "value": "scan_passed"},
                    "output_data": {"type": "STRING", "value": "labelled_product"}
                }
            ]
        },
        "example_tasks": [
            "Load ingredients into the mixer, mix to a uniform batter, transfer to the oven, bake at set temperature, cool on the conveyor, then package and apply batch labels",
            "Fill product into containers, verify fill volume, weigh each unit, scan with metal detector, then label and package compliant units"
        ]
    }
}


# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# Clean interface so planner.py and validator.py never touch the
# raw dictionary directly. This is the "seam" that lets us swap in
# user-defined industries (Tier 2) and full RAG (Tier 3) later.
# ════════════════════════════════════════════════════════════════

def get_industry_list():
    """Returns {key: display_name} for the UI dropdown."""
    return {key: data["display_name"] for key, data in INDUSTRIES.items()}


def get_industry(industry_key):
    """Returns the full profile. Falls back to steel if key unknown."""
    return INDUSTRIES.get(industry_key, INDUSTRIES["steel"])


def get_equipment_apis(industry_key):
    """Returns the equipment->APIs dict for validator.py."""
    return get_industry(industry_key)["equipment"]


def get_data_types(industry_key):
    """Returns valid data types for validator.py."""
    return get_industry(industry_key)["data_types"]


def get_safety_rules(industry_key):
    """Returns safety rules for validator.py and the prompt."""
    return get_industry(industry_key)["safety_rules"]


def get_example_tasks(industry_key):
    """Returns example task prompts for the UI."""
    return get_industry(industry_key)["example_tasks"]


def build_equipment_context(industry_key):
    """
    Builds the grounding text injected into the LLM prompt.
    THIS IS THE ANTI-HALLUCINATION CORE — it tells the LLM exactly
    what equipment exists and constrains it to use only this.
    """
    industry = get_industry(industry_key)
    lines = []
    lines.append(f"INDUSTRY CONTEXT: You are planning for a {industry['display_name']} facility.")
    lines.append(f"Description: {industry['description']}")
    lines.append("")
    lines.append("AVAILABLE EQUIPMENT — you may ONLY use equipment and APIs from this list:")
    for equipment, apis in industry["equipment"].items():
        lines.append(f"  - {equipment}: {', '.join(apis)}")
    lines.append("")
    lines.append(f"VALID DATA TYPES — use only these: {', '.join(industry['data_types'])}")
    lines.append("")
    lines.append("SAFETY RULES — your workflow MUST respect these:")
    for rule in industry["safety_rules"]:
        lines.append(f"  - {rule}")
    lines.append("")
    lines.append(f"REASONING GUIDANCE for this industry: {industry['reasoning_hints']}")
    return "\n".join(lines)


def build_example_block(industry_key):
    """
    Returns a few-shot example workflow as formatted JSON text.
    This forces the LLM to match the DEPTH and STRUCTURE shown,
    countering the 'generic shallow output' problem.
    """
    import json
    industry = get_industry(industry_key)
    example = industry.get("example_workflow")
    if not example:
        return ""
    return (
        "Here is an EXAMPLE of the depth and structure expected "
        f"for this industry:\n{json.dumps(example, indent=2)}"
    )


# ════════════════════════════════════════════════════════════════
# QUICK TEST
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("AVAILABLE INDUSTRIES:")
    for key, name in get_industry_list().items():
        print(f"  {key} -> {name}")

    print("\n" + "="*60)
    print("STEEL — GROUNDING CONTEXT (what the LLM will read):")
    print("="*60)
    print(build_equipment_context("steel"))

    print("\n" + "="*60)
    print("STEEL — FEW-SHOT EXAMPLE (forces output depth):")
    print("="*60)
    print(build_example_block("steel"))