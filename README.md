# 🏭 ManufactureGPT

**An industry-grounded LLM process planner with human-in-the-loop oversight — a cognitive-core layer that turns plain-English manufacturing tasks into validated, digital-twin-ready workflows.**

Inspired by LLMAPM (Ni et al., 2025, *International Journal of Production Research*) and the 2025–26 research on LLM + digital twin integration in Industry 5.0.

---

## The Problem It Solves

Manufacturing process planning is slow, expert-dependent, and hard to adapt for custom products. LLMs can help — but on their own they hallucinate, produce generic output, and can't be trusted without oversight. ManufactureGPT addresses all three by **grounding the LLM in real industry knowledge**, **forcing industry-specific depth**, and **placing humans at the decision points that matter most**.

---

## What It Does

Walk through a guided wizard:

1. **Choose an industry** — use a pre-built template (Steel, Electronics, Food) or build your own for *any* sector
2. **Build knowledge** (custom industries) — the AI proposes a starter equipment profile; you review and approve it
3. **Describe your task** in plain English and choose an oversight level
4. **Confirm intent** — the AI reflects back what it understood before planning
5. **Review the steps** — your domain expertise edits what AI can't know
6. **Validate & export** — industry-aware checks, a twin-readiness score, and a signed-off, audit-trailed JSON output

---

## Key Capabilities

**🌍 Multi-industry, for everyone**
Pre-built templates plus an AI-assisted builder that lets a user from *any* industry — cement, textiles, pharma, paper — create their own grounded knowledge profile in minutes.

**🛡️ Grounded against hallucination**
The LLM is constrained to use only the selected industry's real equipment and APIs. Few-shot examples force industry-specific depth instead of generic placeholders. *Specific in, specific out.*

**🧑‍🔧 Human-in-the-loop by design (5 checkpoints)**
Following the Industry 5.0 human-centricity principle, humans are placed at the highest-leverage control points:
- **Checkpoint A** — approve the knowledge base (highest leverage)
- **Checkpoint B** — confirm the AI's interpretation
- **Checkpoint C** — review and edit the step decomposition
- **Checkpoint D** — accept or override validation warnings
- **Checkpoint E** — final sign-off with audit trail

Oversight intensity is configurable: **Express / Standard / Rigorous** — matching the risk profile of the process.

**✅ Industry-aware FSM validation**
A Finite State Machine checks the four LLMAPM error types (deadlock, data mismatch, invalid API, skipped step) against the *selected industry's* rules, plus a **twin-readiness completeness score** measuring how ready the output is to feed a digital twin.

---

## Architecture

┌──────────────────────────────────────────┐
    │  COGNITIVE CORE (planner.py)              │
    │  grounded, industry-aware LLM planning    │
    └──────────────────────────────────────────┘
                      ↕
    ┌──────────────────────────────────────────┐
    │  KNOWLEDGE LAYER (industries.py +         │
    │  knowledge_builder.py)                    │
    │  industry equipment, APIs, rules          │
    └──────────────────────────────────────────┘
                      ↕
    ┌──────────────────────────────────────────┐
    │  VALIDATION LAYER (validator.py)          │
    │  FSM checks + twin-readiness scoring      │
    └──────────────────────────────────────────┘
                      ↕
    ┌──────────────────────────────────────────┐
    │  HUMAN-IN-THE-LOOP (app.py wizard)        │
    │  5 checkpoints, 3 oversight modes         │
    └──────────────────────────────────────────┘

    ---

## File Structure

| File | Role |
|------|------|
| `industries.py` | Knowledge layer — pre-built industry templates (Tier 1) |
| `knowledge_builder.py` | AI-assisted custom industry creation (Tier 2) |
| `planner.py` | Grounded, industry-aware LLM planner + intent confirmation |
| `validator.py` | Industry-aware FSM validation + twin-readiness scoring |
| `app.py` | Wizard interface with human checkpoints |

---

## Tech Stack

- **AI:** Groq (Llama 3.3 70B) primary, Google Gemini backup — both free tier
- **Backend:** Python 3.11
- **Frontend:** Streamlit (wizard flow with session state)
- **Diagram:** Graphviz

---

## Run Locally

git clone https:/Deval-bot/github.com//manufacturegpt.git

cd manufacturegpt

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

Create a `.env` file with your free API keys:
GROQ_API_KEY=your_key_from_console.groq.com

GEMINI_API_KEY=your_key_from_aistudio.google.com

Run:
streamlit run app.py

---

## Honest Scope

ManufactureGPT is the **cognitive-core and process-definition layer** of a digital-twin-enabled system — the AI intelligence that interprets human intent, grounds it in industry knowledge, and produces validated, structured process definitions. It is **not** a full industrial digital twin (no physics engine or live sensor integration). Its output is a high-quality, human-reviewed planning artifact designed to *feed* a digital twin — accelerating and structuring human expertise, not replacing engineering validation.

---

## Roadmap

- **Tier 3 — Document-grounded RAG:** upload real equipment manuals and standards for retrieval-based grounding at scale
- **Flow simulation:** step durations → throughput, cycle time, and bottleneck analysis (the digital twin bridge)
- **Multi-agent architecture:** specialized agents for decomposition, equipment expertise, and validation

---

## Research Foundation

- Ni, M., Wang, T., Leng, J., Chen, C., & Cheng, L. (2025). *A large language model-based manufacturing process planning approach under industry 5.0.* International Journal of Production Research. DOI: 10.1080/00207543.2025.2469285
- Chen et al. (2025). *Integrating large language model and digital twins in the context of industry 5.0.* Robotics and Computer-Integrated Manufacturing.

