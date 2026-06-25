# app.py
# ════════════════════════════════════════════════════════════════
# ManufactureGPT — Wizard Interface
# Industry-grounded LLM process planner with human-in-the-loop
# checkpoints, multi-industry support, and twin-readiness scoring.
# Run with: streamlit run app.py
# ════════════════════════════════════════════════════════════════

import streamlit as st
import json
import graphviz

from industries import (
    get_industry_list, get_industry, get_example_tasks, get_safety_rules
)
from planner import interpret_task, generate_workflow
from validator import validate_workflow
from knowledge_builder import (
    propose_industry_profile, validate_industry_profile, finalize_profile
)
from simulator import (
    propose_durations, build_duration_table, simulate, provenance_summary
)
# We need to register custom industries so planner/validator can use them
import industries as industries_module


# ── PAGE SETUP ────────────────────────────────────────────
st.set_page_config(page_title="ManufactureGPT", page_icon="🏭", layout="wide")


# ── SESSION STATE INITIALISATION ──────────────────────────
# This is the wizard's "memory" — it remembers data across clicks
def init_state():
    defaults = {
        "stage": 1,
        "industry_key": None,
        "industry_is_custom": False,
        "custom_profile": None,
        "task_text": "",
        "review_mode": "Standard",
        "interpretation": None,
        "workflow": None,
        "validation": None,
        "approved": False,
        "duration_table": None,
        "sim_result": None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()


def go_to(stage):
    st.session_state.stage = stage


def reset_wizard():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


# ── HEADER ────────────────────────────────────────────────
st.title("🏭 ManufactureGPT")
st.caption(
    "Industry-grounded LLM process planner with human-in-the-loop oversight · "
    "Based on LLMAPM (Ni et al., IJPR 2025)"
)

# Progress indicator
stages = ["1. Industry", "2. Knowledge", "3. Task", "4. Confirm",
          "5. Steps", "6. Validate", "7. Simulate", "8. Export"]
current = st.session_state.stage
progress_cols = st.columns(len(stages))
for i, (col, label) in enumerate(zip(progress_cols, stages), start=1):
    if i < current:
        col.markdown(f"✅ {label}")
    elif i == current:
        col.markdown(f"**▶ {label}**")
    else:
        col.markdown(f"○ {label}")

st.divider()


# ════════════════════════════════════════════════════════════
# STAGE 1 — CHOOSE INDUSTRY
# ════════════════════════════════════════════════════════════
if st.session_state.stage == 1:
    st.header("Step 1 — Choose Your Industry")
    st.write("Pick a ready-made industry template, or build your own for any industry.")

    choice = st.radio(
        "How would you like to start?",
        ["Use a pre-built template", "Build my own industry (any sector)"]
    )

    if choice == "Use a pre-built template":
        industry_list = get_industry_list()
        selected_name = st.selectbox(
            "Select industry:",
            options=list(industry_list.keys()),
            format_func=lambda k: industry_list[k]
        )
        st.info(get_industry(selected_name)["description"])

        if st.button("Continue →", type="primary"):
            st.session_state.industry_key = selected_name
            st.session_state.industry_is_custom = False
            go_to(3)   # skip knowledge-building stage for templates
            st.rerun()

    else:
        st.write("Describe your industry in one line and the AI will propose a "
                 "starter equipment profile for you to review and approve.")
        if st.button("Continue to build →", type="primary"):
            st.session_state.industry_is_custom = True
            go_to(2)
            st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE 2 — BUILD CUSTOM INDUSTRY (Tier 2 + Checkpoint A)
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == 2:
    st.header("Step 2 — Build Your Industry Knowledge")
    st.caption("🧑‍🔧 Checkpoint A: You review and approve the knowledge — "
               "this is the highest-leverage human input, since knowledge "
               "quality determines output quality.")

    industry_desc = st.text_input(
        "Describe your industry in one line:",
        placeholder="e.g. A textile dyeing and finishing unit"
    )

    if st.button("🤖 Propose Equipment Profile"):
        if industry_desc.strip():
            with st.spinner("AI is proposing a starter profile for your review..."):
                try:
                    profile = propose_industry_profile(industry_desc)
                    st.session_state.custom_profile = profile
                except Exception as e:
                    st.error(f"Could not generate profile: {e}")
        else:
            st.warning("Please describe your industry first.")

    # Show the proposed profile for review/editing
    if st.session_state.custom_profile:
        profile = st.session_state.custom_profile
        st.success("AI proposed this profile. Review and edit it below before approving.")

        # Editable JSON — the human can correct anything
        edited = st.text_area(
            "Review & edit the profile (this is your knowledge — make it accurate):",
            value=json.dumps(profile, indent=2),
            height=400
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve & Use This Knowledge", type="primary"):
                try:
                    final_profile = json.loads(edited)
                    issues = validate_industry_profile(final_profile)
                    if issues:
                        st.error("Profile has issues — please fix before approving:")
                        for issue in issues:
                            st.write(f"- {issue}")
                    else:
                        # Register the custom industry into the live library
                        final_profile = finalize_profile(final_profile)
                        custom_key = "custom_" + final_profile["display_name"].lower().replace(" ", "_")[:20]
                        industries_module.INDUSTRIES[custom_key] = final_profile
                        st.session_state.industry_key = custom_key
                        st.session_state.approved = True
                        st.success(f"Knowledge approved! Industry '{final_profile['display_name']}' is ready.")
                        go_to(3)
                        st.rerun()
                except json.JSONDecodeError:
                    st.error("The edited text is not valid JSON. Check your brackets and commas.")
        with col2:
            if st.button("← Back"):
                go_to(1)
                st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE 3 — DESCRIBE TASK + REVIEW MODE
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == 3:
    industry = get_industry(st.session_state.industry_key)
    st.header("Step 3 — Describe Your Manufacturing Task")
    st.info(f"Industry: **{industry['display_name']}**")

    # Example tasks for this industry
    examples = get_example_tasks(st.session_state.industry_key)
    if examples:
        st.write("**Example tasks** (click to use):")
        for i, ex in enumerate(examples):
            if st.button(f"▶ {ex[:70]}...", key=f"ex_{i}"):
                st.session_state.task_text = ex

    task = st.text_area(
        "Describe your task in plain English:",
        value=st.session_state.task_text,
        height=120,
        placeholder="Describe the manufacturing process you want to plan..."
    )

    st.write("**Review Mode** — how much human oversight do you want?")
    review_mode = st.radio(
        "Review mode",
        ["Express (fast — fewer checkpoints)",
         "Standard (recommended — key checkpoints)",
         "Rigorous (regulated/safety-critical — all checkpoints)"],
        index=1,
        label_visibility="collapsed"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Continue →", type="primary"):
            if task.strip():
                st.session_state.task_text = task
                st.session_state.review_mode = review_mode
                # Express mode skips intent confirmation
                if review_mode.startswith("Express"):
                    go_to(5)
                else:
                    go_to(4)
                st.rerun()
            else:
                st.warning("Please describe a task first.")
    with col2:
        if st.button("← Change Industry"):
            go_to(1)
            st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE 4 — CONFIRM INTENT (Checkpoint B)
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == 4:
    st.header("Step 4 — Confirm What the AI Understood")
    st.caption("🧑‍🔧 Checkpoint B: Confirm the AI understood your task correctly "
               "before it plans — catching misunderstandings early is cheap.")

    if st.session_state.interpretation is None:
        with st.spinner("AI is interpreting your task..."):
            try:
                st.session_state.interpretation = interpret_task(
                    st.session_state.task_text, st.session_state.industry_key
                )
            except Exception as e:
                st.error(f"Interpretation failed: {e}")
                st.stop()

    interp = st.session_state.interpretation
    st.write("**The AI understood your task as:**")
    st.success(f"🎯 Goal: {interp.get('understood_goal', 'N/A')}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Equipment it will use:**")
        for eq in interp.get("equipment_needed", []):
            st.write(f"- {eq}")
    with col_b:
        st.write(f"**Task type:** {interp.get('task_type', 'N/A')}")
        st.write(f"**Estimated steps:** {interp.get('estimated_steps', 'N/A')}")

    missing = interp.get("missing_or_unclear", "nothing")
    if missing and missing.lower() != "nothing":
        st.warning(f"⚠️ Unclear or missing: {missing}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Looks correct — Generate", type="primary"):
            go_to(5)
            st.rerun()
    with col2:
        if st.button("✏️ Let me revise my task"):
            st.session_state.interpretation = None
            go_to(3)
            st.rerun()
    with col3:
        if st.button("← Back"):
            st.session_state.interpretation = None
            go_to(3)
            st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE 5 — GENERATE + REVIEW STEPS (Checkpoint C)
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == 5:
    st.header("Step 5 — Review the Generated Workflow")
    st.caption("🧑‍🔧 Checkpoint C: Review the step breakdown. Your domain expertise "
               "catches what AI can't — edit the JSON below if needed.")

    if st.session_state.workflow is None:
        with st.spinner("AI is generating your grounded workflow..."):
            try:
                st.session_state.workflow = generate_workflow(
                    st.session_state.task_text, st.session_state.industry_key
                )
            except Exception as e:
                st.error(f"Generation failed: {e}")
                st.stop()

    wf = st.session_state.workflow
    st.success(f"Generated: **{wf.get('task_name', 'Workflow')}** "
               f"({len(wf.get('steps', []))} steps)")

    if wf.get("warnings") and wf["warnings"].lower() != "none":
        st.warning(f"⚠️ AI flagged: {wf['warnings']}")

    # Show steps in a readable way
    for step in wf.get("steps", []):
        st.write(f"**Step {step['step_id']}:** {step['description']} "
                 f"`[{step.get('component', '')}]`")

    # Editable workflow (Checkpoint C)
    with st.expander("✏️ Edit the workflow (advanced — edit JSON directly)"):
        edited_wf = st.text_area(
            "Workflow JSON:",
            value=json.dumps(wf, indent=2),
            height=300
        )
        if st.button("Apply Edits"):
            try:
                st.session_state.workflow = json.loads(edited_wf)
                st.success("Edits applied.")
                st.rerun()
            except json.JSONDecodeError:
                st.error("Invalid JSON — check brackets and commas.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Validate Workflow", type="primary"):
            go_to(6)
            st.rerun()
    with col2:
        if st.button("🔄 Regenerate"):
            st.session_state.workflow = None
            st.rerun()
    with col3:
        if st.button("← Back"):
            st.session_state.workflow = None
            go_to(3)
            st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE 6 — VALIDATE (Checkpoint D)
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == 6:
    st.header("Step 6 — Validation")

    if st.session_state.validation is None:
        with st.spinner("Running industry-aware FSM validation..."):
            st.session_state.validation = validate_workflow(
                st.session_state.workflow, st.session_state.industry_key
            )

    wf = st.session_state.workflow
    val = st.session_state.validation

    tab1, tab2, tab3 = st.tabs(["📊 Diagram", "✅ Validation", "📋 Steps"])

    # ── TAB 1: DIAGRAM ──
    with tab1:
        st.subheader(wf.get("task_name", "Workflow"))
        steps = wf.get("steps", [])
        try:
            dot = graphviz.Digraph()
            dot.attr(rankdir="LR")
            dot.attr("node", fontname="Arial", fontsize="10")
            dot.node("START", "START", shape="oval", style="filled",
                     fillcolor="#27ae60", fontcolor="white")
            for i, step in enumerate(steps):
                sid = str(step["step_id"])
                desc = step.get("description", "")[:30]
                comp = step.get("component", "")
                label = f"Step {step['step_id']}\n{desc}\n[{comp}]"
                dot.node(sid, label, shape="box", style="filled,rounded",
                         fillcolor="#2980b9", fontcolor="white")
                if i == 0:
                    dot.edge("START", sid)
                if i < len(steps) - 1:
                    dot.edge(sid, str(steps[i+1]["step_id"]))
            dot.node("END", "END", shape="oval", style="filled",
                     fillcolor="#c0392b", fontcolor="white")
            if steps:
                dot.edge(str(steps[-1]["step_id"]), "END")
            st.graphviz_chart(dot)
        except Exception as e:
            st.warning(f"Diagram error: {e}")

    # ── TAB 2: VALIDATION ──
    with tab2:
        st.caption("🧑‍🔧 Checkpoint D: Review warnings — accept those fine for your context.")
        if val["is_valid"]:
            st.success("✅ VALIDATION PASSED")
        else:
            st.error("❌ VALIDATION FAILED — see errors below")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Steps", val["total_steps"])
        c2.metric("Twin-Readiness", f"{val['completeness_score']}%")
        c3.metric("Errors", len(val["errors"]))
        c4.metric("Safety Rules", val["safety_rules_count"])

        if val["errors"]:
            st.subheader("🔴 Errors")
            for e in val["errors"]:
                st.error(f"[Type {e['error_type']}] Step {e['step_id']}: {e['message']}")
        if val["warnings"]:
            st.subheader("🟡 Warnings")
            for w in val["warnings"]:
                st.warning(f"[Type {w['warning_type']}] Step {w['step_id']}: {w['message']}")

        st.subheader("🛡️ Safety Rules Checked")
        for rule in val.get("safety_rules", []):
            st.write(f"- {rule}")

    # ── TAB 3: STEPS ──
    with tab3:
        for step in wf.get("steps", []):
            with st.expander(f"Step {step['step_id']}: {step.get('description','')}"):
                st.write(f"Component: `{step.get('component','N/A')}`")
                st.write(f"API: `{step.get('api','N/A')}`")
                inp = step.get("input_data", {})
                out = step.get("output_data", {})
                st.write(f"Input: `{inp.get('value','N/A')}` ({inp.get('type','N/A')})")
                st.write(f"Output: `{out.get('value','N/A')}` ({out.get('type','N/A')})")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Continue to Flow Simulation", type="primary"):
            go_to(7)
            st.rerun()
    with col2:
        if st.button("← Back to Steps"):
            go_to(5)
            st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE 7 — FLOW SIMULATION (the digital twin bridge)
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == 7:
    st.header("Step 7 — Flow Simulation")
    st.caption("🧑‍🔧 AI proposes durations with reasoning → you review and enter "
               "real data → every number's source stays transparent.")

    wf = st.session_state.workflow

    # Get AI-proposed durations once
    if st.session_state.duration_table is None:
        with st.spinner("AI is estimating step durations (with reasoning)..."):
            try:
                ai_durations = propose_durations(wf, st.session_state.industry_key)
                st.session_state.duration_table = build_duration_table(wf, ai_durations)
            except Exception as e:
                st.error(f"Could not estimate durations: {e}")
                st.stop()

    table = st.session_state.duration_table

    # Provenance summary at the top — the transparency metric
    prov = provenance_summary(table)
    st.progress(prov["grounded_pct"] / 100)
    st.caption(f"**{prov['grounded_pct']}% grounded in real data** "
               f"({prov['ai_estimated']} 🤖 AI-estimated, "
               f"{prov['user_entered']} ✏️ user-entered). "
               f"Replace estimates with real values to increase confidence.")

    st.subheader("Step Durations — review and edit")
    st.write("Edit any duration with your real data. The 🤖 tag flips to ✏️ when you do.")

    # Editable duration table
    for i, row in enumerate(table):
        col1, col2, col3 = st.columns([3, 1.5, 1])
        with col1:
            tag = "🤖" if row["provenance"] == "ai_estimated" else "✏️"
            st.write(f"{tag} **Step {row['step_id']}**: {row['description'][:45]}")
            st.caption(f"Basis: {row['basis']}")
        with col2:
            new_val = st.number_input(
                f"Seconds (step {row['step_id']})",
                min_value=1,
                value=int(row["duration_seconds"]),
                key=f"dur_{row['step_id']}",
                label_visibility="collapsed"
            )
            # If the user changed it, update provenance
            if new_val != row["duration_seconds"]:
                table[i]["duration_seconds"] = new_val
                table[i]["provenance"] = "user_entered"
        with col3:
            st.write(f"`{row['component'][:12]}`")

    # Run simulation on current table
    sim = simulate(table)
    st.session_state.sim_result = sim

    st.divider()
    st.subheader("📈 Simulation Results")

    m1, m2, m3 = st.columns(3)
    m1.metric("Cycle Time", f"{sim['cycle_time_minutes']} min")
    m2.metric("Throughput", f"{sim['throughput_per_hour']}/hr")
    m3.metric("Per 8h Shift", f"{sim['throughput_per_8h_shift']} units")

    # Bottleneck callout — the operations insight
    st.error(f"🔴 **Bottleneck: Step {sim['bottleneck_step_id']}** — "
             f"{sim['bottleneck_description']} "
             f"({sim['bottleneck_duration']}s, {sim['bottleneck_share_pct']}% of cycle time). "
             f"This step limits your throughput — prioritize getting its real duration accurate.")

    # ── TIMELINE / GANTT VIEW ──
    st.subheader("⏱️ Process Timeline")
    try:
        timeline = graphviz.Digraph()
        timeline.attr(rankdir="LR")
        timeline.attr("node", shape="box", style="filled", fontname="Arial", fontsize="9")
        cumulative = 0
        for row in table:
            sid = str(row["step_id"])
            is_bottleneck = (row["step_id"] == sim["bottleneck_step_id"])
            color = "#c0392b" if is_bottleneck else "#2980b9"
            label = (f"Step {row['step_id']}\n{row['duration_seconds']}s\n"
                     f"{row['utilization_pct']}% util")
            timeline.node(sid, label, fillcolor=color, fontcolor="white")
            cumulative += row["duration_seconds"]
        # connect in order
        for i in range(len(table) - 1):
            timeline.edge(str(table[i]["step_id"]), str(table[i+1]["step_id"]))
        st.graphviz_chart(timeline)
        st.caption("🔴 Red = bottleneck step. Utilization % shows how busy each "
                   "step is relative to the bottleneck.")
    except Exception as e:
        st.warning(f"Timeline error: {e}")

    # ── WHAT-IF SLIDER ──
    st.subheader("🎚️ What-If Analysis")
    st.write(f"Drag to see: if you reduce the bottleneck (Step "
             f"{sim['bottleneck_step_id']}) duration, how does throughput change?")

    current_bottleneck = sim["bottleneck_duration"]
    new_bottleneck = st.slider(
        "Bottleneck duration (seconds)",
        min_value=1,
        max_value=int(current_bottleneck),
        value=int(current_bottleneck)
    )
    new_throughput = round(3600 / new_bottleneck, 1) if new_bottleneck > 0 else 0
    improvement = round(((new_throughput - sim["throughput_per_hour"])
                         / sim["throughput_per_hour"]) * 100) if sim["throughput_per_hour"] > 0 else 0

    wc1, wc2 = st.columns(2)
    wc1.metric("New Throughput", f"{new_throughput}/hr",
               delta=f"{improvement}%")
    wc2.metric("New Per 8h Shift", f"{round(new_throughput * 8)} units")
    st.caption("Note: this what-if assumes the bottleneck improves; if another step "
               "becomes the new slowest step, real throughput would be capped by that.")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Continue to Export", type="primary"):
            go_to(8)
            st.rerun()
    with col2:
        if st.button("← Back to Validation"):
            go_to(6)
            st.rerun()


# ════════════════════════════════════════════════════════════
# STAGE 8 — FINAL EXPORT (Checkpoint E)
# ════════════════════════════════════════════════════════════
elif st.session_state.stage == 8:
    st.header("Step 8 — Final Sign-Off & Export")
    st.caption("🧑‍🔧 Checkpoint E: Final human sign-off — creates accountability "
               "and an audit trail before the output feeds a digital twin.")

    wf = st.session_state.workflow
    val = st.session_state.validation
    sim = st.session_state.sim_result
    table = st.session_state.duration_table
    prov = provenance_summary(table) if table else {}

    # Summary card
    st.subheader("📋 Workflow Summary")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Steps", val["total_steps"])
    s2.metric("Twin-Readiness", f"{val['completeness_score']}%")
    s3.metric("Cycle Time", f"{sim['cycle_time_minutes']} min" if sim else "N/A")
    s4.metric("Data Grounded", f"{prov.get('grounded_pct', 0)}%")

    st.json(wf)

    approver = st.text_input("Your name/role (for audit trail):")
    if st.button("✅ Approve & Export", type="primary"):
        if approver.strip():
            export = dict(wf)
            export["approved_by"] = approver
            export["industry"] = st.session_state.industry_key
            export["validation_summary"] = {
                "passed": val["is_valid"],
                "twin_readiness": val["completeness_score"]
            }
            if sim:
                export["simulation_summary"] = {
                    "cycle_time_minutes": sim["cycle_time_minutes"],
                    "throughput_per_hour": sim["throughput_per_hour"],
                    "bottleneck_step_id": sim["bottleneck_step_id"],
                    "data_grounded_pct": prov.get("grounded_pct", 0)
                }
                export["step_durations"] = table
            st.download_button(
                "⬇️ Download Approved Workflow JSON",
                data=json.dumps(export, indent=2),
                file_name=f"{wf.get('task_name','workflow').replace(' ','_')}_approved.json",
                mime="application/json"
            )
            st.success(f"Approved by {approver}. Ready for digital twin import.")
        else:
            st.warning("Please enter your name/role to approve.")

    st.divider()
    if st.button("🔄 Start New Workflow"):
        reset_wizard()
        st.rerun()