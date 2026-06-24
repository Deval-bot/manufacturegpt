# planner.py
# ════════════════════════════════════════════════════════════════
# THE COGNITIVE CORE (grounded, industry-aware planner)
# ════════════════════════════════════════════════════════════════
# Uses Google Gemini (free) with Groq backup.
# Now reads industry knowledge from industries.py to ground the LLM,
# preventing hallucination and forcing industry-specific depth.
#
# Includes Checkpoint B: intent confirmation (interpret_task) — the
# AI reflects back what it understood BEFORE planning, so a human can
# confirm or correct interpretation at the cheapest possible point.
# ════════════════════════════════════════════════════════════════

import json
import os
from dotenv import load_dotenv

# Import the knowledge layer
from industries import build_equipment_context, build_example_block, get_industry

load_dotenv()

# ── SETUP GEMINI ──────────────────────────────────────────
import google.generativeai as genai

gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    genai.configure(api_key=gemini_key)
    print("Gemini ready")
else:
    print("WARNING: No Gemini key found in .env")

# ── SETUP GROQ ────────────────────────────────────────────
try:
    from groq import Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        groq_client = Groq(api_key=groq_key)
        print("Groq ready as backup")
    else:
        groq_client = None
except ImportError:
    groq_client = None


# ════════════════════════════════════════════════════════════════
# CHECKPOINT B — INTENT CONFIRMATION
# Before any planning, the AI reflects back what it understood.
# This catches misunderstandings at the cheapest possible point.
# ════════════════════════════════════════════════════════════════

def interpret_task(task, industry_key):
    """
    Returns the AI's interpretation of the task for human confirmation.
    Does NOT plan yet — just confirms understanding.
    """
    context = build_equipment_context(industry_key)

    prompt = f"""
{context}

A user has described this manufacturing task:
"{task}"

Before planning, summarise your understanding in this exact JSON format
(no markdown, just JSON):
{{
    "understood_goal": "one sentence: what the user wants to achieve",
    "equipment_needed": ["list", "of", "equipment", "from the available list"],
    "task_type": "sequential or conditional or parallel",
    "missing_or_unclear": "anything vague or any equipment the task needs that is NOT in the available list — or 'nothing' if all clear",
    "estimated_steps": "rough number of steps you expect"
}}
"""
    raw = _call_llm(prompt, system="You are a manufacturing planning assistant. Return only JSON.")
    return _parse_json(raw)


# ════════════════════════════════════════════════════════════════
# THE GROUNDED PROMPT BUILDER
# ════════════════════════════════════════════════════════════════

def build_system_prompt(industry_key):
    """Builds the full grounded system prompt with context + example."""
    context = build_equipment_context(industry_key)
    example = build_example_block(industry_key)

    return f"""
You are an expert manufacturing process planning engineer.

{context}

CRITICAL RULES — these prevent errors:
1. You may ONLY use equipment and APIs from the AVAILABLE EQUIPMENT list above.
   If the task seems to need equipment NOT in the list, do NOT invent it —
   instead add a note in the "warnings" field naming what is missing.
2. Use ONLY the valid data types listed.
3. Your workflow MUST respect every safety rule listed.
4. The output of each step must feed logically into the next step's input.
5. Generate realistic, INDUSTRY-SPECIFIC steps — not generic placeholders.
   Match the depth shown in the example below.

{example}

Now follow this Chain-of-Thought process:
STEP 1 - IDENTIFY the objects, actions, and equipment needed.
STEP 2 - CLASSIFY the task type (sequential / conditional / parallel).
STEP 3 - DECOMPOSE into steps, each using ONE piece of equipment.
STEP 4 - CONNECT steps so outputs feed into inputs with matching data types.

Return ONLY valid JSON (no markdown, no ```json blocks) in this format:
{{
    "task_name": "short descriptive name",
    "task_type": "sequential",
    "industry": "{industry_key}",
    "reasoning": "your step by step thinking",
    "warnings": "any equipment the task needed but was not available, or 'none'",
    "steps": [
        {{
            "step_id": 1,
            "description": "what this step does",
            "component": "equipment name from the available list",
            "api": "function name from that equipment's API list",
            "input_data": {{"type": "DATA_TYPE", "source": "user_input or step_N_output", "value": "parameter_name"}},
            "output_data": {{"type": "DATA_TYPE", "value": "output_name"}}
        }}
    ]
}}
"""


# ════════════════════════════════════════════════════════════════
# LLM CALLERS (Gemini primary, Groq backup)
# ════════════════════════════════════════════════════════════════

def _call_llm(prompt, system="You are a helpful assistant. Return only JSON."):
    """Internal: tries Gemini, falls back to Groq. Returns raw text."""
    if gemini_key:
        try:
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system,
                generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
            )
            return model.generate_content(prompt).text
        except Exception as e:
            print(f"Gemini failed: {e}. Trying Groq...")

    if groq_client:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
        )
        return resp.choices[0].message.content

    raise Exception("No LLM available. Check API keys in .env")


def _parse_json(raw):
    """Internal: safely parse JSON, cleaning markdown if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split('\n')
        raw = '\n'.join(lines[1:-1])
    return json.loads(raw)


# ════════════════════════════════════════════════════════════════
# MAIN: GENERATE WORKFLOW (now industry-aware)
# ════════════════════════════════════════════════════════════════

def generate_workflow(task, industry_key="steel"):
    """
    Generates a grounded, industry-specific workflow.
    industry_key selects which knowledge profile to ground the LLM with.
    """
    print(f"Generating workflow for industry: {industry_key}")
    system = build_system_prompt(industry_key)
    user_msg = f"""
Create a manufacturing workflow for this task:

TASK: {task}

Remember: use ONLY available equipment, respect safety rules,
match the example's depth, return ONLY JSON.
"""
    raw = _call_llm(user_msg if False else system + "\n\nUSER TASK:\n" + task)
    # Note: we send the grounded system prompt + task together for reliability
    workflow = _parse_json(raw)
    print("Workflow generated.")
    return workflow


# ════════════════════════════════════════════════════════════════
# QUICK TEST
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_task = (
        "Charge raw material into the blast furnace, control temperature "
        "to tap molten iron, transport via ladle to the basic oxygen furnace, "
        "blow oxygen to refine into steel, then pour into the continuous caster "
        "to produce slabs"
    )

    print("\n" + "="*60)
    print("CHECKPOINT B — INTENT CONFIRMATION:")
    print("="*60)
    interpretation = interpret_task(test_task, "steel")
    print(json.dumps(interpretation, indent=2))

    print("\n" + "="*60)
    print("GENERATED STEEL WORKFLOW:")
    print("="*60)
    workflow = generate_workflow(test_task, "steel")
    print(json.dumps(workflow, indent=2))
    print(f"\nSteps: {len(workflow.get('steps', []))}")
    print(f"Warnings: {workflow.get('warnings', 'none')}")