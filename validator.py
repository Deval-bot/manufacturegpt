# validator.py
# Implements the Finite State Machine (FSM) validator from LLMAPM paper
# Checks the AI-generated workflow for 4 types of errors before deployment

# The 4 error types from the paper:
# Error 1 - Deadlock: a step loops forever
# Error 2 - Data Mismatch: wrong data type passed between steps  
# Error 3 - API Error: component calls a function it doesn't have
# Error 4 - Skip Error: a step is defined but never executed


# ── VALID DATA TYPES ──────────────────────────────────────
# From the LLMAPM paper specification

VALID_TYPES = {"STRING", "DOUBLE", "INT", "BOOL", "ARRAY"}


# ── KNOWN EQUIPMENT AND THEIR VALID APIs ──────────────────
# In a real factory system this comes from a database
# Here we define the common equipment from the paper's experiments

EQUIPMENT_APIS = {
    "robotic_arm": [
        "ur5_quickMove", "ur5_loadMove", "ur5_reset",
        "moveToPosition", "moveHome", "quickMove",
        "loadMove", "resetHome", "getPosition"
    ],
    "suction_cup": [
        "activate", "deactivate", "checkPressure",
        "grip", "release", "suck", "release"
    ],
    "depth_camera": [
        "captureImage", "capture_image", "detectObjects",
        "detect_objects", "getCoordinates", "get_coordinates",
        "hikvision_laser", "saveImage", "save_image"
    ],
    "vision_system": [
        "detectDefects", "detect_defects", "classifyObject",
        "classify_object", "yoloInference", "yolo_inference",
        "getBoundingBoxes", "runInference"
    ],
    "plc": [
        "sendSignal", "send_signal", "receiveSignal",
        "moveConveyor", "move_conveyor", "lockPosition",
        "setOutput", "getInput", "start", "stop"
    ],
    "conveyor": [
        "start", "stop", "setSpeed", "set_speed",
        "getPosition", "moveTo", "move_to"
    ],
    "gripper": [
        "open", "close", "getForce", "setForce", "grip", "release"
    ],
    "reset": [
        "reset", "returnHome", "return_home", "initialize", "home"
    ]
}


# ── FSM STATE CLASS ───────────────────────────────────────
# Each step in the workflow gets its own mini state machine
# State 0 = not yet executed
# State 1 = currently executing
# After execution completes → back to 0, recorded as done

class StepFSM:
    def __init__(self, step_id):
        self.step_id = step_id
        self.state = 0
        self.execution_count = 0

    def start(self):
        # Transition: 0 → 1
        self.state = 1
        self.execution_count += 1

    def finish(self):
        # Transition: 1 → 0
        self.state = 0

    def is_deadlocked(self):
        # From LLMAPM paper: error if executed more than 50 times
        return self.execution_count > 50


# ── MAIN VALIDATION FUNCTION ──────────────────────────────

def validate_workflow(workflow):
    """
    Runs all four checks from Algorithm 1 in the LLMAPM paper.
    Returns a dictionary with validation results.
    """

    errors = []
    warnings = []
    steps = workflow.get("steps", [])

    if not steps:
        return {
            "is_valid": False,
            "errors": [{"error_type": 4, "error_name": "No Steps",
                        "step_id": 0, "message": "Workflow has no steps."}],
            "warnings": [],
            "total_steps": 0,
            "executed_steps": 0
        }

    # Create an FSM for every step
    fsm_map = {step["step_id"]: StepFSM(step["step_id"]) for step in steps}

    # ── CHECK 1: DATA TYPE VALIDATION (Error Type 2) ──────
    # Every input and output must use a valid data type

    for step in steps:
        sid = step["step_id"]
        in_type = step.get("input_data", {}).get("type", "").upper()
        out_type = step.get("output_data", {}).get("type", "").upper()

        if in_type and in_type not in VALID_TYPES:
            errors.append({
                "error_type": 2,
                "error_name": "Invalid Data Type",
                "step_id": sid,
                "message": (
                    f"Step {sid} input type '{in_type}' is not valid. "
                    f"Must be one of: {', '.join(VALID_TYPES)}"
                )
            })

        if out_type and out_type not in VALID_TYPES:
            errors.append({
                "error_type": 2,
                "error_name": "Invalid Data Type",
                "step_id": sid,
                "message": (
                    f"Step {sid} output type '{out_type}' is not valid. "
                    f"Must be one of: {', '.join(VALID_TYPES)}"
                )
            })

    # ── CHECK 2: DATA FLOW VALIDATION (Error Type 2) ──────
    # Output type of step N must match input type of step N+1

    for i in range(len(steps) - 1):
        current = steps[i]
        nxt = steps[i + 1]

        out_type = current.get("output_data", {}).get("type", "").upper()
        in_type = nxt.get("input_data", {}).get("type", "").upper()
        source = nxt.get("input_data", {}).get("source", "")

        # Only check if next step explicitly takes input from current step
        if f"step_{current['step_id']}" in source:
            if out_type and in_type and out_type != in_type:
                errors.append({
                    "error_type": 2,
                    "error_name": "Data Flow Mismatch",
                    "step_id": nxt["step_id"],
                    "message": (
                        f"Step {current['step_id']} outputs {out_type} "
                        f"but Step {nxt['step_id']} expects {in_type}. "
                        f"Data types must match between connected steps."
                    )
                })

    # ── CHECK 3: API VALIDATION (Error Type 3) ────────────
    # Each component must only call APIs from its known list

    for step in steps:
        sid = step["step_id"]
        component = step.get("component", "").lower().replace(" ", "_")
        api_called = step.get("api", "")

        # Find which equipment category this component belongs to
        matched = None
        for equipment in EQUIPMENT_APIS:
            if equipment in component or component in equipment:
                matched = equipment
                break

        if matched:
            valid_apis = EQUIPMENT_APIS[matched]
            if api_called and api_called not in valid_apis:
                warnings.append({
                    "warning_type": 3,
                    "warning_name": "Unknown API Call",
                    "step_id": sid,
                    "message": (
                        f"Step {sid}: '{api_called}' is not in the "
                        f"known API list for '{matched}'. "
                        f"Valid APIs: {', '.join(valid_apis[:5])}..."
                    )
                })
        else:
            warnings.append({
                "warning_type": 3,
                "warning_name": "Unknown Component",
                "step_id": sid,
                "message": (
                    f"Step {sid}: Component '{component}' is not in "
                    f"the known equipment library. "
                    f"This may be custom equipment — review manually."
                )
            })

    # ── CHECK 4: EXECUTION SIMULATION (Error Types 1 and 4) 
    # Simulate running every step through the FSM
    # Check for deadlocks and skipped steps

    executed_ids = []

    for step in steps:
        sid = step["step_id"]
        fsm = fsm_map[sid]

        fsm.start()     # State 0 → 1

        # Error Type 1: Deadlock check
        if fsm.is_deadlocked():
            errors.append({
                "error_type": 1,
                "error_name": "Deadlock Detected",
                "step_id": sid,
                "message": (
                    f"Step {sid} executed {fsm.execution_count} times. "
                    f"Possible infinite loop. Add an exit condition."
                )
            })

        fsm.finish()    # State 1 → 0
        executed_ids.append(sid)

    # Error Type 4: Skip check
    all_ids = [step["step_id"] for step in steps]
    skipped = [sid for sid in all_ids if sid not in executed_ids]

    for sid in skipped:
        errors.append({
            "error_type": 4,
            "error_name": "Step Skipped",
            "step_id": sid,
            "message": (
                f"Step {sid} was defined but never executed. "
                f"The workflow sequence is broken."
            )
        })

    # ── RETURN RESULTS ────────────────────────────────────
    return {
        "is_valid": len(errors) == 0,
        "total_steps": len(steps),
        "executed_steps": len(executed_ids),
        "errors": errors,
        "warnings": warnings
    }


# ── QUICK TEST ────────────────────────────────────────────
# Run: python validator.py

if __name__ == "__main__":

    # Test workflow with one intentional data type error
    test_workflow = {
        "task_name": "Test Assembly",
        "task_type": "sequential",
        "steps": [
            {
                "step_id": 1,
                "description": "Move arm above CPU",
                "component": "robotic_arm",
                "api": "ur5_quickMove",
                "input_data": {"type": "ARRAY", "source": "user_input",
                               "value": "start_pos"},
                "output_data": {"type": "STRING",  # Intentional wrong type
                                "value": "position_above"}
            },
            {
                "step_id": 2,
                "description": "Lower arm to CPU",
                "component": "robotic_arm",
                "api": "ur5_loadMove",
                "input_data": {"type": "ARRAY",    # Expects ARRAY, gets STRING
                               "source": "step_1_output",
                               "value": "position"},
                "output_data": {"type": "ARRAY", "value": "contact_pos"}
            },
            {
                "step_id": 3,
                "description": "Activate suction",
                "component": "suction_cup",
                "api": "activate",
                "input_data": {"type": "BOOL", "source": "user_input",
                               "value": "activate_flag"},
                "output_data": {"type": "BOOL", "value": "suction_on"}
            }
        ]
    }

    result = validate_workflow(test_workflow)

    print("\n" + "="*50)
    print("FSM VALIDATION REPORT")
    print("="*50)
    print(f"Valid: {result['is_valid']}")
    print(f"Steps: {result['total_steps']}")
    print(f"Errors: {len(result['errors'])}")
    print(f"Warnings: {len(result['warnings'])}")

    if result["errors"]:
        print("\nERRORS FOUND:")
        for e in result["errors"]:
            print(f"  [Type {e['error_type']}] Step {e['step_id']}: "
                  f"{e['error_name']}")
            print(f"  → {e['message']}")

    if result["warnings"]:
        print("\nWARNINGS:")
        for w in result["warnings"]:
            print(f"  [Type {w['warning_type']}] Step {w['step_id']}: "
                  f"{w['warning_name']}")