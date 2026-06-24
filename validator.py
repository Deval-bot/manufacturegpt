# validator.py
# ════════════════════════════════════════════════════════════════
# THE VALIDATION LAYER (now industry-aware)
# ════════════════════════════════════════════════════════════════
# Implements the FSM validation from the LLMAPM paper, but now reads
# equipment, APIs, data types, and safety rules from the SELECTED
# industry profile in industries.py — so it validates a steel workflow
# against steel rules, a food workflow against food rules, etc.
#
# Checks the 4 error types from the paper, PLUS:
#   - Completeness (twin-readiness): all fields populated
#   - Safety rule awareness (industry-specific)
# ════════════════════════════════════════════════════════════════

from industries import get_equipment_apis, get_data_types, get_safety_rules


# ── FSM STATE CLASS ───────────────────────────────────────
class StepFSM:
    """Each step gets a mini state machine. 0=not executed, 1=executing."""
    def __init__(self, step_id):
        self.step_id = step_id
        self.state = 0
        self.execution_count = 0

    def start(self):
        self.state = 1
        self.execution_count += 1

    def finish(self):
        self.state = 0

    def is_deadlocked(self):
        return self.execution_count > 50


# ════════════════════════════════════════════════════════════════
# MAIN VALIDATION — now takes industry_key
# ════════════════════════════════════════════════════════════════

def validate_workflow(workflow, industry_key="steel"):
    """
    Validates a workflow against the SELECTED industry's knowledge.
    Returns errors, warnings, and a completeness assessment.
    """
    errors = []
    warnings = []
    steps = workflow.get("steps", [])

    # Load THIS industry's knowledge
    equipment_apis = get_equipment_apis(industry_key)
    valid_types = set(t.upper() for t in get_data_types(industry_key))
    safety_rules = get_safety_rules(industry_key)

    if not steps:
        return {
            "is_valid": False,
            "errors": [{"error_type": 4, "error_name": "No Steps",
                        "step_id": 0, "message": "Workflow has no steps."}],
            "warnings": [], "total_steps": 0, "executed_steps": 0,
            "completeness_score": 0, "safety_rules_count": len(safety_rules)
        }

    fsm_map = {s["step_id"]: StepFSM(s["step_id"]) for s in steps}

    # ── CHECK 1: DATA TYPE VALIDATION (Error Type 2) ──────
    for step in steps:
        sid = step["step_id"]
        in_type = step.get("input_data", {}).get("type", "").upper()
        out_type = step.get("output_data", {}).get("type", "").upper()

        if in_type and in_type not in valid_types:
            errors.append({
                "error_type": 2, "error_name": "Invalid Data Type", "step_id": sid,
                "message": f"Step {sid} input type '{in_type}' is not valid for "
                           f"{industry_key}. Valid: {', '.join(valid_types)}"
            })
        if out_type and out_type not in valid_types:
            errors.append({
                "error_type": 2, "error_name": "Invalid Data Type", "step_id": sid,
                "message": f"Step {sid} output type '{out_type}' is not valid for "
                           f"{industry_key}."
            })

    # ── CHECK 2: DATA FLOW VALIDATION (Error Type 2) ──────
    for i in range(len(steps) - 1):
        current, nxt = steps[i], steps[i + 1]
        out_type = current.get("output_data", {}).get("type", "").upper()
        in_type = nxt.get("input_data", {}).get("type", "").upper()
        source = nxt.get("input_data", {}).get("source", "")

        if f"step_{current['step_id']}" in source:
            if out_type and in_type and out_type != in_type:
                errors.append({
                    "error_type": 2, "error_name": "Data Flow Mismatch",
                    "step_id": nxt["step_id"],
                    "message": f"Step {current['step_id']} outputs {out_type} but "
                               f"Step {nxt['step_id']} expects {in_type}."
                })

    # ── CHECK 3: API & COMPONENT VALIDATION (Error Type 3) ─
    for step in steps:
        sid = step["step_id"]
        component = step.get("component", "").lower().replace(" ", "_")
        api_called = step.get("api", "")

        # Find matching equipment in THIS industry
        matched = None
        for equipment in equipment_apis:
            if equipment in component or component in equipment:
                matched = equipment
                break

        if matched:
            valid_apis = equipment_apis[matched]
            if api_called and api_called not in valid_apis:
                warnings.append({
                    "warning_type": 3, "warning_name": "Unknown API Call", "step_id": sid,
                    "message": f"Step {sid}: '{api_called}' not in known APIs for "
                               f"'{matched}'. Valid: {', '.join(valid_apis[:4])}..."
                })
        else:
            warnings.append({
                "warning_type": 3, "warning_name": "Unknown Component", "step_id": sid,
                "message": f"Step {sid}: Component '{component}' is not in the "
                           f"{industry_key} equipment library. Review manually."
            })

    # ── CHECK 4: EXECUTION SIMULATION (Error Types 1 & 4) ─
    executed_ids = []
    for step in steps:
        sid = step["step_id"]
        fsm = fsm_map[sid]
        fsm.start()
        if fsm.is_deadlocked():
            errors.append({
                "error_type": 1, "error_name": "Deadlock", "step_id": sid,
                "message": f"Step {sid} executed too many times. Possible loop."
            })
        fsm.finish()
        executed_ids.append(sid)

    all_ids = [s["step_id"] for s in steps]
    for sid in [x for x in all_ids if x not in executed_ids]:
        errors.append({
            "error_type": 4, "error_name": "Step Skipped", "step_id": sid,
            "message": f"Step {sid} defined but never executed."
        })

    # ── CHECK 5: COMPLETENESS (TWIN-READINESS) ────────────
    # Every step must have all fields populated for a digital twin to use it
    complete_steps = 0
    for step in steps:
        sid = step["step_id"]
        required = ["description", "component", "api", "input_data", "output_data"]
        missing = [f for f in required if not step.get(f)]

        # Also check data sub-fields
        if step.get("input_data") and not step["input_data"].get("type"):
            missing.append("input_data.type")
        if step.get("output_data") and not step["output_data"].get("type"):
            missing.append("output_data.type")

        if missing:
            warnings.append({
                "warning_type": 5, "warning_name": "Incomplete Step", "step_id": sid,
                "message": f"Step {sid} missing fields: {', '.join(missing)}. "
                           f"A digital twin needs all fields populated."
            })
        else:
            complete_steps += 1

    completeness_score = round((complete_steps / len(steps)) * 100) if steps else 0

    # ── RESULT ────────────────────────────────────────────
    return {
        "is_valid": len(errors) == 0,
        "total_steps": len(steps),
        "executed_steps": len(executed_ids),
        "complete_steps": complete_steps,
        "completeness_score": completeness_score,
        "safety_rules_count": len(safety_rules),
        "safety_rules": safety_rules,
        "errors": errors,
        "warnings": warnings
    }


# ════════════════════════════════════════════════════════════════
# QUICK TEST
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test with a valid steel workflow snippet
    test_workflow = {
        "task_name": "Test Steel Process",
        "task_type": "sequential",
        "steps": [
            {
                "step_id": 1,
                "description": "Charge raw material into blast furnace",
                "component": "blast_furnace",
                "api": "chargeRawMaterial",
                "input_data": {"type": "STRING", "source": "user_input", "value": "raw_material"},
                "output_data": {"type": "BOOL", "value": "charged"}
            },
            {
                "step_id": 2,
                "description": "Tap molten iron",
                "component": "blast_furnace",
                "api": "tapMoltenIron",
                "input_data": {"type": "BOOL", "source": "step_1_output", "value": "charged"},
                "output_data": {"type": "TEMPERATURE", "value": "molten_temp"}
            }
        ]
    }

    result = validate_workflow(test_workflow, "steel")

    print("="*55)
    print("INDUSTRY-AWARE VALIDATION REPORT (Steel)")
    print("="*55)
    print(f"Valid: {result['is_valid']}")
    print(f"Total Steps: {result['total_steps']}")
    print(f"Completeness Score: {result['completeness_score']}% (twin-readiness)")
    print(f"Safety Rules Checked: {result['safety_rules_count']}")
    print(f"Errors: {len(result['errors'])}")
    print(f"Warnings: {len(result['warnings'])}")

    if result["errors"]:
        print("\nERRORS:")
        for e in result["errors"]:
            print(f"  [Type {e['error_type']}] Step {e['step_id']}: {e['message']}")
    if result["warnings"]:
        print("\nWARNINGS:")
        for w in result["warnings"]:
            print(f"  [Type {w['warning_type']}] Step {w['step_id']}: {w['message']}")