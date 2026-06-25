# simulator.py
# ════════════════════════════════════════════════════════════════
# THE FLOW SIMULATION LAYER (the digital twin bridge)
# ════════════════════════════════════════════════════════════════
# Computes cycle time, throughput, and bottleneck from step durations.
# Durations follow the "AI proposes, human approves" model with
# provenance tagging so every number's source is transparent.
#
# Honest scope: this is PLANNING-GRADE simulation using estimated or
# user-entered durations — excellent for comparing options and finding
# bottlenecks, not a substitute for calibrated industrial simulation.
# ════════════════════════════════════════════════════════════════

import json
from planner import _call_llm, _parse_json


# ════════════════════════════════════════════════════════════════
# STEP 1: AI PROPOSES DURATIONS (with reasoning) — for human review
# ════════════════════════════════════════════════════════════════

def propose_durations(workflow, industry_key):
    """
    Asks the LLM to estimate a duration (in seconds) for each step,
    WITH a one-line basis for each estimate. These are DRAFTS the
    human will review, approve, or override.
    """
    steps_summary = []
    for s in workflow.get("steps", []):
        steps_summary.append(
            f"Step {s['step_id']}: {s['description']} "
            f"[equipment: {s.get('component','')}]"
        )
    steps_text = "\n".join(steps_summary)

    prompt = f"""
You are a manufacturing operations expert estimating cycle times.

Industry: {industry_key}
Here are the process steps:
{steps_text}

For each step, estimate a realistic duration in SECONDS and give a
one-line basis for your estimate. These are planning estimates that
a human engineer will review and correct with real data.

Return ONLY valid JSON (no markdown) in this format:
{{
    "durations": [
        {{
            "step_id": 1,
            "duration_seconds": 8,
            "basis": "one-line reason for this estimate"
        }}
    ]
}}

Be realistic for the industry. Heavy/thermal steps (furnaces, ovens,
casting) take much longer than quick mechanical moves.
"""
    raw = _call_llm(
        prompt,
        system="You are a manufacturing operations expert. Return only JSON."
    )
    parsed = _parse_json(raw)
    return parsed.get("durations", [])


# ════════════════════════════════════════════════════════════════
# STEP 2: BUILD THE DURATION TABLE with provenance tags
# ════════════════════════════════════════════════════════════════

def build_duration_table(workflow, ai_durations):
    """
    Combines workflow steps with AI-proposed durations into a table,
    each tagged with provenance. Initially all are 'ai_estimated'.
    The human will later flip some to 'user_entered' or 'user_approved'.
    """
    ai_map = {d["step_id"]: d for d in ai_durations}
    table = []
    for step in workflow.get("steps", []):
        sid = step["step_id"]
        ai = ai_map.get(sid, {})
        table.append({
            "step_id": sid,
            "description": step["description"],
            "component": step.get("component", ""),
            "duration_seconds": ai.get("duration_seconds", 10),
            "basis": ai.get("basis", "default estimate"),
            "provenance": "ai_estimated"   # ai_estimated | user_entered | user_approved
        })
    return table


# ════════════════════════════════════════════════════════════════
# STEP 3: THE SIMULATION CALCULATIONS (the operations core)
# ════════════════════════════════════════════════════════════════

def simulate(duration_table):
    """
    Computes the key flow metrics from step durations.

    Logic (sequential line):
    - cycle_time = sum of all step durations (one unit start to finish)
    - bottleneck = the slowest single step (limits line throughput)
    - throughput = 3600 / bottleneck_duration (units per hour, steady state)
    - utilization per step = step_duration / bottleneck_duration
    """
    if not duration_table:
        return None

    durations = [s["duration_seconds"] for s in duration_table]
    cycle_time = sum(durations)

    # Find the bottleneck (slowest step)
    bottleneck = max(duration_table, key=lambda s: s["duration_seconds"])
    bottleneck_duration = bottleneck["duration_seconds"]

    # Throughput: steady-state, a unit completes every bottleneck-duration
    throughput_per_hour = round(3600 / bottleneck_duration, 1) if bottleneck_duration > 0 else 0

    # Utilization of each step relative to the bottleneck
    for step in duration_table:
        if bottleneck_duration > 0:
            step["utilization_pct"] = round(
                (step["duration_seconds"] / bottleneck_duration) * 100
            )
        else:
            step["utilization_pct"] = 0

    # How much of the total cycle time does the bottleneck represent?
    bottleneck_share = round((bottleneck_duration / cycle_time) * 100) if cycle_time > 0 else 0

    return {
        "cycle_time_seconds": cycle_time,
        "cycle_time_minutes": round(cycle_time / 60, 2),
        "bottleneck_step_id": bottleneck["step_id"],
        "bottleneck_description": bottleneck["description"],
        "bottleneck_duration": bottleneck_duration,
        "bottleneck_share_pct": bottleneck_share,
        "throughput_per_hour": throughput_per_hour,
        "throughput_per_8h_shift": round(throughput_per_hour * 8),
        "duration_table": duration_table
    }


# ════════════════════════════════════════════════════════════════
# STEP 4: PROVENANCE SUMMARY (the authenticity/transparency metric)
# ════════════════════════════════════════════════════════════════

def provenance_summary(duration_table):
    """
    Reports how many durations are AI-estimated vs human-grounded.
    This is the transparency metric — a DX team sees at a glance how
    much of the model rests on real data vs estimates.
    """
    total = len(duration_table)
    if total == 0:
        return {"grounded_pct": 0, "ai": 0, "user": 0, "approved": 0}

    ai = sum(1 for s in duration_table if s["provenance"] == "ai_estimated")
    user = sum(1 for s in duration_table if s["provenance"] == "user_entered")
    approved = sum(1 for s in duration_table if s["provenance"] == "user_approved")

    # "Grounded" = human has either entered or explicitly approved
    grounded = user + approved
    grounded_pct = round((grounded / total) * 100)

    return {
        "total": total,
        "ai_estimated": ai,
        "user_entered": user,
        "user_approved": approved,
        "grounded_pct": grounded_pct
    }


# ════════════════════════════════════════════════════════════════
# QUICK TEST
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # A small fake steel workflow to test the math
    test_workflow = {
        "steps": [
            {"step_id": 1, "description": "Charge raw material", "component": "blast_furnace"},
            {"step_id": 2, "description": "Tap molten iron", "component": "blast_furnace"},
            {"step_id": 3, "description": "Blow oxygen to refine", "component": "basic_oxygen_furnace"},
            {"step_id": 4, "description": "Cast into slabs", "component": "continuous_caster"}
        ]
    }

    print("Asking AI to propose durations...")
    ai_durations = propose_durations(test_workflow, "steel")
    print(json.dumps(ai_durations, indent=2))

    table = build_duration_table(test_workflow, ai_durations)
    result = simulate(table)

    print("\n" + "="*55)
    print("SIMULATION RESULT")
    print("="*55)
    print(f"Cycle time: {result['cycle_time_seconds']}s "
          f"({result['cycle_time_minutes']} min)")
    print(f"Bottleneck: Step {result['bottleneck_step_id']} — "
          f"{result['bottleneck_description']} "
          f"({result['bottleneck_duration']}s, "
          f"{result['bottleneck_share_pct']}% of cycle)")
    print(f"Throughput: {result['throughput_per_hour']} units/hour "
          f"({result['throughput_per_8h_shift']} per 8h shift)")

    print("\nProvenance:")
    prov = provenance_summary(table)
    print(f"  {prov['grounded_pct']}% grounded "
          f"({prov['ai_estimated']} AI-estimated, "
          f"{prov['user_entered']} user-entered)")