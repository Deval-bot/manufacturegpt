# knowledge_builder.py
# ════════════════════════════════════════════════════════════════
# TIER 2 — USER-DEFINED INDUSTRY BUILDER ("for everyone")
# ════════════════════════════════════════════════════════════════
# Lets a user from ANY industry create their own knowledge profile.
# The LLM proposes a starter profile (removing the blank-page problem),
# then the HUMAN reviews, edits, and approves it (Checkpoint A — the
# highest-leverage human checkpoint, since knowledge quality caps
# everything downstream).
#
# A user-defined industry has the SAME structure as a template, so it
# plugs into planner.py and validator.py with zero changes.
# ════════════════════════════════════════════════════════════════

import json
from planner import _call_llm, _parse_json


def propose_industry_profile(industry_description):
    """
    Uses the LLM to PROPOSE a starter industry profile from a short
    description. This is a DRAFT for human review — not final.
    """
    prompt = f"""
You are a manufacturing domain expert helping build an equipment knowledge
profile for a new industry.

The user describes their industry as:
"{industry_description}"

Propose a realistic starter profile. Include the main equipment found in
such a facility, realistic function names (APIs) for each, the data types
their signals use, and key safety rules.

Return ONLY valid JSON (no markdown) in this exact structure:
{{
    "display_name": "Friendly industry name",
    "description": "one-line description of this industry",
    "equipment": {{
        "equipment_name_one": ["apiFunction1", "apiFunction2", "apiFunction3"],
        "equipment_name_two": ["apiFunction1", "apiFunction2"]
    }},
    "data_types": ["STRING", "DOUBLE", "INT", "BOOL", "ARRAY"],
    "safety_rules": [
        "a key safety or sequencing rule",
        "another important rule"
    ],
    "reasoning_hints": "what to think about when planning processes for this industry"
}}

Rules:
- Use lowercase_with_underscores for equipment names
- Use camelCase for API function names
- Include 5-8 pieces of equipment
- Include 3-5 realistic safety rules
- Keep data_types to the standard set unless the industry truly needs a special one
"""
    raw = _call_llm(
        prompt,
        system="You are a manufacturing domain expert. Return only valid JSON."
    )
    return _parse_json(raw)


def validate_industry_profile(profile):
    """
    Checks a profile (whether AI-proposed or human-edited) is complete
    enough to be usable. This protects against the 'sloppy knowledge'
    problem before the profile is ever used for planning.
    Returns a list of issues (empty list = good to use).
    """
    issues = []

    if not profile.get("display_name"):
        issues.append("Missing industry display name")
    if not profile.get("description"):
        issues.append("Missing industry description")

    equipment = profile.get("equipment", {})
    if not equipment:
        issues.append("No equipment defined — at least one is required")
    else:
        for name, apis in equipment.items():
            if not apis or len(apis) == 0:
                issues.append(f"Equipment '{name}' has no API functions defined")

    if not profile.get("data_types"):
        issues.append("No data types defined")
    if not profile.get("safety_rules"):
        issues.append("No safety rules defined — recommended for quality output")

    return issues


def finalize_profile(profile):
    """
    Adds the few-shot example slot and example_tasks if missing, so the
    user-defined profile has the SAME shape as a template. Ensures it
    plugs into the existing pipeline cleanly.
    """
    # Ensure all keys exist so planner/validator never break
    profile.setdefault("example_workflow", None)
    profile.setdefault("example_tasks", [])
    profile.setdefault("reasoning_hints", "")
    return profile


# ════════════════════════════════════════════════════════════════
# QUICK TEST
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Testing knowledge builder with a NEW industry...")
    print("Industry: 'A textile dyeing and finishing unit'\n")

    proposed = propose_industry_profile("A textile dyeing and finishing unit")

    print("="*55)
    print("AI-PROPOSED PROFILE (for human review — Checkpoint A):")
    print("="*55)
    print(json.dumps(proposed, indent=2))

    print("\n" + "="*55)
    print("PROFILE VALIDATION:")
    print("="*55)
    issues = validate_industry_profile(proposed)
    if issues:
        print("Issues found (human should fix before approving):")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Profile is complete and ready for human approval.")