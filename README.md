# 🏭 ManufactureGPT

**LLM-Powered Manufacturing Process Planner | Industry 5.0**

Converts plain English manufacturing task descriptions into 
validated, executable workflows — inspired by LLMAPM 
(Ni et al., 2025, International Journal of Production Research).

---

## What It Does

Type a manufacturing task in plain English and get back:
- Structured step-by-step workflow with equipment assignments
- Data flow connections between each step  
- FSM validation report checking 4 error types
- Visual workflow diagram
- Downloadable JSON for industrial platform import

**Example input:**
> "Use a robotic arm with suction cup to pick a CPU from a 
> parts tray and place it onto a motherboard socket"

---

## Three-Phase Pipeline

**Phase 1 — Task Split**
Gemini AI decomposes the task using Chain-of-Thought prompting

**Phase 2 — Step Generation**
AI defines inputs, outputs and API calls for each step

**Phase 3 — FSM Validation**
Finite State Machine checks 4 error types:
- Type 1: Deadlock
- Type 2: Data Type Mismatch
- Type 3: Invalid API Call
- Type 4: Skipped Step

---

## Tech Stack

- AI: Google Gemini 2.0 Flash (free) + Groq Llama 3.3 70B (backup)
- Backend: Python 3.11
- Frontend: Streamlit
- Diagram: Graphviz

---

## Run Locally
git clone https://github.com/Deval-bot/manufacturegpt.git

cd manufacturegpt

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

Create a `.env` file:
GEMINI_API_KEY=your_key_from_aistudio.google.com

GROQ_API_KEY=your_key_from_console.groq.com

Then run:
streamlit run app.py

---

## Research Reference

Ni, M., Wang, T., Leng, J., Chen, C., & Cheng, L. (2025).
*A large language model-based manufacturing process planning 
approach under industry 5.0.*
International Journal of Production Research.
DOI: 10.1080/00207543.2025.2469285
