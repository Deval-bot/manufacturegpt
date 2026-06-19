# planner.py
# Handles all AI communication
# Uses Google Gemini (free) with Groq as automatic backup (also free)

import json
import os
from dotenv import load_dotenv

# This line reads your API keys from the .env file
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
        print("WARNING: No Groq key found in .env")
except ImportError:
    groq_client = None


# ── THE PROMPT TEMPLATE ───────────────────────────────────
# This is the Chain-of-Thought prompt from the LLMAPM paper
# It tells the AI exactly how to think about the problem

def get_system_prompt():
    return """
You are an expert manufacturing process planning engineer 
specialising in Industry 5.0 flexible manufacturing systems.

Your job: convert a user's plain English task description 
into a structured manufacturing workflow JSON.

Follow this thinking process step by step:

STEP 1 - IDENTIFY
Extract the key objects and actions from the task.
What needs to be moved, assembled, inspected, or sorted?
What equipment is mentioned or implied?

STEP 2 - CLASSIFY the task type:
- sequential: steps happen one after another (most common)
- conditional: a decision point exists (if defect found, reject)
- parallel: two things happen at the same time

STEP 3 - DECOMPOSE into individual steps.
Rule: each step uses ONLY ONE piece of equipment.
For each step ask: what INPUT does it need? What OUTPUT does it produce?

STEP 4 - CONNECT the steps.
The OUTPUT of step N must feed into the INPUT of step N+1.
Data types must match across connected steps.

RULES:
- Each step = one component only
- Data types must be: STRING, DOUBLE, INT, BOOL, or ARRAY
- Always end with a reset step for robotic tasks
- Generate between 4 and 10 steps

Return ONLY a JSON object. No explanation. No markdown. 
No ```json blocks. Just the raw JSON like this:

{
    "task_name": "short descriptive name",
    "task_type": "sequential",
    "reasoning": "your step by step thinking here",
    "steps": [
        {
            "step_id": 1,
            "description": "what this step does in plain English",
            "component": "name of equipment used",
            "api": "function_name_called",
            "input_data": {
                "type": "ARRAY",
                "source": "user_input",
                "value": "start_position"
            },
            "output_data": {
                "type": "ARRAY",
                "value": "position_above_target"
            }
        }
    ]
}
"""


def get_user_message(task):
    return f"""
Create a manufacturing workflow for this task:

TASK: {task}

Think through it step by step.
Each step uses one component.
Outputs of each step feed into inputs of the next.
Return ONLY the JSON. Nothing else before or after it.
"""


# ── GEMINI CALL ───────────────────────────────────────────

def call_gemini(task):
    print("Calling Google Gemini...")

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=get_system_prompt(),
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json"
        }
    )

    response = model.generate_content(get_user_message(task))
    raw = response.text.strip()

    # Clean up if model accidentally added markdown blocks
    if raw.startswith("```"):
        lines = raw.split('\n')
        raw = '\n'.join(lines[1:-1])

    workflow = json.loads(raw)
    print("Gemini succeeded")
    return workflow


# ── GROQ CALL ─────────────────────────────────────────────

def call_groq(task):
    print("Calling Groq (Llama 3.3 70B)...")

    if not groq_client:
        raise Exception("Groq not available. Check GROQ_API_KEY in .env")

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        messages=[
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": get_user_message(task)}
        ]
    )

    raw = response.choices[0].message.content.strip()

    # Clean up markdown if present
    if raw.startswith("```"):
        lines = raw.split('\n')
        raw = '\n'.join(lines[1:-1])

    workflow = json.loads(raw)
    print("Groq succeeded")
    return workflow


# ── MAIN FUNCTION ─────────────────────────────────────────
# This is what app.py calls
# Tries Gemini first, automatically uses Groq if Gemini fails

def generate_workflow(task):
    
    # Try Gemini first
    if gemini_key:
        try:
            return call_gemini(task)
        except Exception as e:
            print(f"Gemini failed: {e}")
            print("Switching to Groq...")

    # Try Groq as backup
    if groq_client:
        try:
            return call_groq(task)
        except Exception as e:
            raise Exception(f"Both APIs failed. Last error: {e}")

    raise Exception(
        "No API available. "
        "Check that GEMINI_API_KEY and GROQ_API_KEY are in your .env file."
    )


# ── QUICK TEST ────────────────────────────────────────────
# Run this file directly to test: python planner.py

if __name__ == "__main__":
    print("\n" + "="*50)
    print("TESTING API CONNECTION")
    print("="*50)

    test_task = """
    Use a robotic arm with suction cup to pick a CPU chip 
    from a parts tray and place it onto a motherboard socket. 
    Reset to home position after completion.
    """

    try:
        result = generate_workflow(test_task)
        print("\nSUCCESS! Workflow generated:")
        print(json.dumps(result, indent=2))
        print(f"\nTotal steps generated: {len(result.get('steps', []))}")
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nCheck:")
        print("1. Your .env file has GEMINI_API_KEY=... on one line")
        print("2. You ran: pip install google-generativeai groq python-dotenv")
        print("3. Your key is correct at aistudio.google.com")