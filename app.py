# app.py
# The complete web interface using Streamlit
# Run with: streamlit run app.py

import streamlit as st
import json
import graphviz
from planner import generate_workflow
from validator import validate_workflow

# ── PAGE SETUP ────────────────────────────────────────────

st.set_page_config(
    page_title="ManufactureGPT",
    page_icon="🏭",
    layout="wide"
)

# ── HEADER ────────────────────────────────────────────────

st.title("🏭 ManufactureGPT")
st.markdown(
    "**LLM-Powered Manufacturing Process Planner** · Industry 5.0 · "
    "Based on LLMAPM (Ni et al., IJPR 2025)"
)
st.divider()

# ── SIDEBAR ───────────────────────────────────────────────

with st.sidebar:
    st.header("📋 Try an Example")
    st.caption("Click any example to load it into the input box")

    examples = {
        "CPU Assembly": (
            "Use a robotic arm with suction cup to pick a CPU chip "
            "from a parts tray and place it onto a motherboard socket. "
            "Reset to home position after completion."
        ),
        "Block Sorting": (
            "Use a depth camera and robotic arm to detect circular, "
            "square, and hexagonal blocks on a conveyor, then sort "
            "them into designated bins based on shape."
        ),
        "Cap Inspection": (
            "Inspect bottle caps for defects using a vision camera "
            "and YOLO AI detection. Route defective caps to a "
            "rejection bin using a PLC-controlled conveyor."
        )
    }

    for name, task in examples.items():
        if st.button(f"▶ {name}", use_container_width=True):
            st.session_state.task_input = task

    st.divider()

    st.header("ℹ️ How It Works")
    st.markdown("""
**Phase 1 — Task Split**
LLM reads your description and breaks it into subtasks

**Phase 2 — Step Generation**  
LLM defines inputs, outputs and APIs for each step

**Phase 3 — FSM Validation**  
Finite State Machine checks 4 error types:
- 🔴 Type 1: Deadlock
- 🔴 Type 2: Data Mismatch  
- 🔴 Type 3: Invalid API
- 🔴 Type 4: Skipped Step

**Paper:** Ni et al. (2025), *Int. Journal of Production Research*
    """)

    st.divider()
    st.header("🤖 AI Engine")
    st.markdown("""
**Primary:** Google Gemini 2.0 Flash (Free)  
**Backup:** Groq Llama 3.3 70B (Free)  
Auto-switches if primary hits rate limit.
    """)

# ── MAIN INPUT AREA ───────────────────────────────────────

col_input, col_options = st.columns([3, 1])

with col_input:
    task_text = st.text_area(
        "📝 Describe your manufacturing task in plain English:",
        value=st.session_state.get("task_input", ""),
        height=130,
        placeholder=(
            "Example: Use a robotic arm and suction cup to pick a "
            "CPU from a parts tray and place it on a motherboard, "
            "then reset to home position..."
        )
    )

with col_options:
    st.markdown("**Task Type Hint:**")
    task_type_hint = st.radio(
        "Task type",
        ["Sequential", "Conditional", "Parallel"],
        captions=["Steps in order", "Has a decision", "Two things at once"],
        label_visibility="collapsed"
    )

generate_clicked = st.button(
    "🚀 Generate & Validate Workflow",
    type="primary",
    use_container_width=True
)

# ── GENERATION AND RESULTS ────────────────────────────────

if generate_clicked:

    if not task_text.strip():
        st.error("Please type a task description or click an example above.")
        st.stop()

    # Add the task type hint to help the AI
    full_task = f"{task_text}\n\nHint: This is likely a {task_type_hint} task."

    # Phase 1 + 2: Generate workflow
    with st.spinner(
        "🤖 AI is analysing your task and generating workflow... "
        "(takes 5-15 seconds)"
    ):
        try:
            workflow = generate_workflow(full_task)
        except Exception as e:
            st.error(f"Generation failed: {str(e)}")
            st.info(
                "Check that your API keys are correct in the .env file "
                "and that you have internet connection."
            )
            st.stop()

    # Phase 3: Validate
    with st.spinner("🔍 Running FSM validation checks..."):
        validation = validate_workflow(workflow)

    st.success("✅ Done! See results below.")
    st.divider()

    # ── RESULTS IN TABS ───────────────────────────────────

    tab_diagram, tab_validation, tab_steps, tab_json = st.tabs([
        "📊 Workflow Diagram",
        "✅ Validation Report",
        "📋 Step Details",
        "🔧 Raw JSON"
    ])

    # ── TAB 1: VISUAL DIAGRAM ─────────────────────────────

    with tab_diagram:

        task_name = workflow.get("task_name", "Manufacturing Workflow")
        task_type = workflow.get("task_type", "sequential").upper()
        steps = workflow.get("steps", [])

        st.subheader(task_name)
        st.caption(f"Task Type: **{task_type}** · {len(steps)} Steps")

        # Show AI reasoning if available
        if workflow.get("reasoning"):
            with st.expander("💭 View AI Chain-of-Thought Reasoning"):
                st.write(workflow["reasoning"])

        # Build the diagram
        try:
            dot = graphviz.Digraph()
            dot.attr(rankdir="LR")  # Left to right
            dot.attr("graph", bgcolor="transparent")
            dot.attr("node", fontname="Arial", fontsize="10")
            dot.attr("edge", fontname="Arial", fontsize="8",
                     color="#888888")

            # START node
            dot.node(
                "START", "START",
                shape="oval",
                style="filled",
                fillcolor="#27ae60",
                fontcolor="white",
                fontsize="11"
            )

            for i, step in enumerate(steps):
                sid = str(step["step_id"])
                desc = step.get("description", "")
                component = step.get("component", "unknown")

                # Truncate long descriptions for the box
                short_desc = (desc[:35] + "...") if len(desc) > 35 else desc
                label = f"Step {step['step_id']}\n{short_desc}\n[{component}]"

                # Color by equipment type
                comp_lower = component.lower()
                if any(x in comp_lower for x in ["arm", "robot", "ur5"]):
                    color = "#2980b9"    # Blue = robotic arm
                elif any(x in comp_lower for x in
                         ["camera", "vision", "depth", "hikvision"]):
                    color = "#8e44ad"    # Purple = vision/camera
                elif any(x in comp_lower for x in
                         ["suction", "gripper", "effector"]):
                    color = "#e67e22"    # Orange = end effector
                elif any(x in comp_lower for x in
                         ["plc", "conveyor", "pump"]):
                    color = "#c0392b"    # Red = PLC/conveyor
                elif any(x in comp_lower for x in
                         ["reset", "home", "init"]):
                    color = "#7f8c8d"    # Grey = reset
                else:
                    color = "#16a085"    # Teal = other

                dot.node(
                    sid, label,
                    shape="box",
                    style="filled,rounded",
                    fillcolor=color,
                    fontcolor="white"
                )

                # Connect START to first step
                if i == 0:
                    dot.edge("START", sid)

                # Connect steps to each other
                if i < len(steps) - 1:
                    next_sid = str(steps[i + 1]["step_id"])
                    out_val = step.get("output_data", {}).get("value", "")
                    edge_label = out_val[:18] if out_val else ""
                    dot.edge(sid, next_sid, label=edge_label)

            # END node
            dot.node(
                "END", "END",
                shape="oval",
                style="filled",
                fillcolor="#c0392b",
                fontcolor="white",
                fontsize="11"
            )

            if steps:
                dot.edge(str(steps[-1]["step_id"]), "END")

            st.graphviz_chart(dot)

            st.caption(
                "🔵 Robotic Arm · 🟣 Camera/Vision · "
                "🟠 End Effector · 🔴 PLC/Conveyor · "
                "⬜ Reset · 🟢 Start · 🔴 End"
            )

        except Exception as diagram_error:
            st.warning(f"Diagram could not render: {diagram_error}")
            st.info("Showing text list instead:")
            for step in steps:
                st.write(
                    f"**Step {step['step_id']}:** "
                    f"{step.get('description', '')} "
                    f"[{step.get('component', '')}]"
                )

    # ── TAB 2: VALIDATION REPORT ──────────────────────────

    with tab_validation:
        st.subheader("FSM Validation Report")
        st.caption(
            "Implements Algorithm 1 from the LLMAPM paper — "
            "checks 4 error types before deployment"
        )

        # Big pass/fail indicator
        if validation["is_valid"]:
            st.success(
                "✅ VALIDATION PASSED — "
                "Workflow is logically correct and safe to deploy"
            )
        else:
            st.error(
                "❌ VALIDATION FAILED — "
                "Issues must be resolved before deployment"
            )

        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Steps", validation["total_steps"])
        m2.metric("Steps Simulated", validation["executed_steps"])
        m3.metric("Errors", len(validation["errors"]))
        m4.metric("Warnings", len(validation["warnings"]))

        st.divider()

        # Four check boxes — one per error type
        st.markdown("**Check Results:**")

        error_types_found = [e["error_type"] for e in validation["errors"]]

        checks = [
            (1, "Deadlock Check",
             "No infinite loops detected",
             "Infinite loop detected in sequence"),
            (2, "Data Type Check",
             "All data types valid and consistent",
             "Data type errors found between steps"),
            (3, "API Validation",
             "All API calls are from valid equipment functions",
             "Invalid API calls detected"),
            (4, "Step Completeness",
             "All defined steps are executed",
             "Some steps are skipped or unreachable")
        ]

        for error_num, check_name, pass_msg, fail_msg in checks:
            if error_num in error_types_found:
                st.error(f"❌ **{check_name}** — {fail_msg}")
            else:
                st.success(f"✅ **{check_name}** — {pass_msg}")

        # Error details
        if validation["errors"]:
            st.divider()
            st.markdown("**Error Details:**")

            explanations = {
                1: ("What it means: A step keeps executing and "
                    "never finishes — like a machine stuck in a loop. "
                    "Fix: Add a proper exit condition."),
                2: ("What it means: Data flowing between steps has "
                    "incompatible formats — like sending an image "
                    "to a component expecting coordinates. "
                    "Fix: Match output type of step N to input type "
                    "of step N+1."),
                3: ("What it means: The workflow calls a function "
                    "that does not exist on that equipment. "
                    "Fix: Use a valid API from the equipment's list."),
                4: ("What it means: A step was defined but the "
                    "workflow never reaches it — broken sequence. "
                    "Fix: Check that all steps are properly connected.")
            }

            for error in validation["errors"]:
                with st.expander(
                    f"[Error Type {error['error_type']}] "
                    f"Step {error['step_id']}: {error['error_name']}"
                ):
                    st.write(error["message"])
                    st.info(explanations.get(error["error_type"], ""))

        # Warnings
        if validation["warnings"]:
            st.divider()
            st.markdown("**Warnings (non-critical):**")
            for w in validation["warnings"]:
                with st.expander(
                    f"[Warning] Step {w['step_id']}: {w['warning_name']}"
                ):
                    st.write(w["message"])

    # ── TAB 3: STEP DETAILS ───────────────────────────────

    with tab_steps:
        st.subheader("Step-by-Step Breakdown")
        st.caption(
            "Each step corresponds to one manufacturing function block "
            "in the LLMAPM architecture"
        )

        for step in workflow.get("steps", []):
            with st.expander(
                f"Step {step['step_id']}: {step.get('description', '')}"
            ):
                col_a, col_b = st.columns(2)

                with col_a:
                    st.markdown("**Equipment & Function**")
                    st.write(f"Component: `{step.get('component', 'N/A')}`")
                    st.write(f"API Call: `{step.get('api', 'N/A')}`")

                with col_b:
                    st.markdown("**Data Flow**")
                    inp = step.get("input_data", {})
                    out = step.get("output_data", {})
                    st.write(
                        f"Input: `{inp.get('value', 'N/A')}` "
                        f"({inp.get('type', 'N/A')}) "
                        f"← from {inp.get('source', 'N/A')}"
                    )
                    st.write(
                        f"Output: `{out.get('value', 'N/A')}` "
                        f"({out.get('type', 'N/A')})"
                    )

    # ── TAB 4: RAW JSON ───────────────────────────────────

    with tab_json:
        st.subheader("Raw JSON Output")
        st.caption(
            "This is the structured workflow the AI generates — "
            "ready to be imported into an industrial software platform"
        )
        st.json(workflow)

        # Create filename safely
        task_name_clean = workflow.get('task_name', 'workflow').replace(' ', '_')
        
        st.download_button(
            label="⬇️ Download Workflow as JSON",
            data=json.dumps(workflow, indent=2),
            file_name=f"{task_name_clean}.json",
            mime="application/json"
        )