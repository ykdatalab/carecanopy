from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
import json

import boto3
import streamlit as st

from app.actions import execute_actions
from app.agent import route_case
from app.dynamo_state import DynamoWorkflowStateStore


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="CareCanopy",
    page_icon="🌿",
    layout="wide",
)


# =========================================================
# DESIGN SYSTEM
# =========================================================

st.markdown(
    dedent("""
    <style>
        :root {
            --cc-ink: #172321;
            --cc-muted: #66746F;
            --cc-line: #DDE5E1;
            --cc-surface: #FFFFFF;
            --cc-canvas: #F5F8F6;
            --cc-sidebar: #EEF3F0;
            --cc-green: #176B4D;
            --cc-green-dark: #12543D;
            --cc-green-soft: #EAF5EF;
            --cc-amber: #8A5A00;
            --cc-amber-soft: #FFF4D8;
            --cc-red: #B42318;
            --cc-red-soft: #FDECEC;
            --cc-slate-soft: #EEF2F3;
        }

        .stApp {
            background:
                linear-gradient(180deg, #F9FBFA 0px, #F5F8F6 260px, #F5F8F6 100%);
            color: var(--cc-ink);
        }

        .block-container {
            max-width: 1220px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }

        /* Reduce default Streamlit chrome without changing app logic. */
        #MainMenu,
        footer,
        [data-testid="stAppDeployButton"] {
            display: none !important;
        }

        header[data-testid="stHeader"] {
            background: transparent;
            box-shadow: none;
        }

        section[data-testid="stSidebar"] {
            background: var(--cc-sidebar);
            border-right: 1px solid var(--cc-line);
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 1.2rem;
        }

        .product-shell {
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid var(--cc-line);
            border-radius: 20px;
            padding: 1.35rem 1.55rem 1.2rem 1.55rem;
            margin-bottom: 1rem;
            box-shadow: 0 8px 28px rgba(23, 107, 77, 0.06);
        }

        .product-eyebrow {
            color: var(--cc-green);
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .product-title-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
        }

        .care-title {
            color: var(--cc-ink);
            font-size: 2.35rem;
            font-weight: 820;
            letter-spacing: -0.045em;
            line-height: 1.05;
            margin: 0;
        }

        .care-subtitle {
            color: var(--cc-muted);
            font-size: 0.98rem;
            line-height: 1.55;
            margin-top: 0.3rem;
        }

        .tagline {
            color: #34433E;
            font-weight: 720;
        }

        .principle-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.95rem;
        }

        .principle-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            background: #F7FAF8;
            color: #40514B;
            border: 1px solid var(--cc-line);
            border-radius: 999px;
            padding: 0.34rem 0.62rem;
            font-size: 0.78rem;
            font-weight: 650;
        }

        .workflow-strip {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.55rem;
            margin-top: 0.85rem;
        }

        .workflow-step {
            background: #FAFCFB;
            border: 1px solid var(--cc-line);
            border-radius: 11px;
            padding: 0.58rem 0.7rem;
            color: #5A6863;
            font-size: 0.76rem;
            line-height: 1.25;
        }

        .workflow-step b {
            color: var(--cc-ink);
            display: block;
            font-size: 0.79rem;
            margin-bottom: 0.12rem;
        }

        .section-kicker {
            color: #5E6D67;
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            margin-bottom: 0.38rem;
        }

        .sidebar-brand {
            color: var(--cc-ink);
            font-size: 1.04rem;
            font-weight: 800;
            margin-bottom: 0.15rem;
        }

        .sidebar-copy {
            color: var(--cc-muted);
            font-size: 0.78rem;
            line-height: 1.45;
            margin-bottom: 0.7rem;
        }

        .demo-badge {
            display: inline-block;
            color: #596762;
            background: rgba(255,255,255,0.7);
            border: 1px solid var(--cc-line);
            border-radius: 999px;
            padding: 0.26rem 0.5rem;
            font-size: 0.7rem;
            font-weight: 700;
            margin: 0.45rem 0 0.75rem 0;
        }

        .background-task {
            background: var(--cc-green-soft);
            border: 1px solid #B7D9C7;
            border-radius: 14px;
            padding: 0.85rem 1rem;
            margin: 0.55rem 0 1.15rem 0;
            box-shadow: 0 4px 16px rgba(23, 107, 77, 0.035);
        }

        .background-task-title {
            color: var(--cc-green);
            font-size: 0.95rem;
            font-weight: 800;
            margin-bottom: 0.22rem;
        }

        .background-task-main {
            color: var(--cc-ink);
            font-size: 0.98rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }

        .background-task-meta {
            color: #5F6E68;
            font-size: 0.82rem;
            line-height: 1.45;
        }

        .route-badge {
            display: inline-block;
            padding: 0.46rem 0.78rem;
            border-radius: 999px;
            font-weight: 800;
            font-size: 0.84rem;
            letter-spacing: 0.02em;
        }

        .routine {
            background: #E4F3EA;
            color: #176B4D;
        }

        .clarify {
            background: var(--cc-amber-soft);
            color: var(--cc-amber);
        }

        .escalate {
            background: var(--cc-red-soft);
            color: var(--cc-red);
        }

        .safety-on {
            background: #FFF0E8;
            color: #B54708;
        }

        .safety-off {
            background: var(--cc-slate-soft);
            color: #4E5D58;
        }

        .decision-shell {
            background: var(--cc-surface);
            border: 1px solid var(--cc-line);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            margin: 0.35rem 0 0.9rem 0;
            box-shadow: 0 6px 22px rgba(20, 43, 35, 0.045);
        }

        .decision-title {
            font-size: 1.04rem;
            font-weight: 800;
            color: var(--cc-ink);
            margin-bottom: 0.25rem;
        }

        .decision-copy {
            color: var(--cc-muted);
            font-size: 0.82rem;
            line-height: 1.45;
        }

        .hero-urgent {
            background: #FFF8F6;
            border: 1px solid #F0B7B1;
            border-left: 4px solid var(--cc-red);
            border-radius: 14px;
            padding: 0.95rem 1.05rem;
            margin: 0.9rem 0;
        }

        .hero-title {
            font-size: 0.98rem;
            font-weight: 800;
            color: var(--cc-red);
            margin-bottom: 0.3rem;
        }

        .hero-text {
            color: #56645F;
            line-height: 1.48;
            font-size: 0.86rem;
        }

        /* Make default Streamlit controls feel closer to a service workspace. */
        div[data-baseweb="select"] > div {
            background: white;
            border-color: #CFDAD5;
            border-radius: 11px;
            min-height: 2.7rem;
        }

        .stTextArea textarea {
            background: white !important;
            border: 1px solid #CFDAD5 !important;
            border-radius: 13px !important;
            box-shadow: none !important;
            line-height: 1.5;
        }

        .stTextArea textarea:focus {
            border-color: #6EAA8E !important;
            box-shadow: 0 0 0 2px rgba(23, 107, 77, 0.08) !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--cc-line);
            border-radius: 14px;
            background: rgba(255,255,255,0.82);
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid var(--cc-line);
            padding: 0.75rem 0.9rem;
            border-radius: 12px;
            box-shadow: none;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.16rem;
        }

        div.stButton > button {
            border-radius: 11px;
            min-height: 2.9rem;
            font-weight: 750;
            background-color: var(--cc-green);
            border-color: var(--cc-green);
            color: white;
            box-shadow: 0 4px 14px rgba(23, 107, 77, 0.12);
        }

        div.stButton > button:hover {
            background-color: var(--cc-green-dark);
            border-color: var(--cc-green-dark);
            color: white;
        }

        hr {
            border-color: var(--cc-line) !important;
        }

        @media (max-width: 900px) {
            .workflow-strip {
                grid-template-columns: repeat(2, 1fr);
            }

            .product-title-row {
                display: block;
            }
        }
    </style>
    """),
    unsafe_allow_html=True,
)


# =========================================================
# CONSTANTS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DEV_CASES_PATH = BASE_DIR / "data" / "dev_cases.json"

AWS_REGION = "ap-northeast-2"
DYNAMO_TABLE = "CareCanopyWorkflowStates"


ACTION_LABELS = {
    "COMPLETE_ROUTINE_FOLLOWUP":
        "Complete routine follow-up",

    "REQUEST_CLARIFICATION":
        "Request clarification",

    "ISSUE_IMMEDIATE_MEDICAL_GUIDANCE":
        "Immediate medical pathway",

    "NOTIFY_CLINICAL_TEAM":
        "Record clinical-team notification action",

    "CREATE_REVIEW_PACKET":
        "Create human review packet",
}


ESCALATION_LABELS = {
    "URGENT_MEDICAL":
        "Urgent medical",

    "NON_URGENT_PROFESSIONAL":
        "Professional review",

    "SCOPE_BOUNDARY":
        "Scope boundary",
}


STATUS_LABELS = {
    "ROUTINE_COMPLETED":
        "Completed",

    "AWAITING_CLARIFICATION":
        "Awaiting clarification",

    "ESCALATED":
        "Escalated",
}


CONTEXT_LABELS = {
    "age":
        "Age",

    "weeks_post_stroke":
        "Time since stroke",

    "baseline":
        "Baseline",

    "approved_plan":
        "Specialist-approved plan",
}


# =========================================================
# DATA HELPERS
# =========================================================

@st.cache_data
def load_dev_cases() -> list[dict]:
    with open(
        DEV_CASES_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


@st.cache_data(ttl=15)
def load_proactive_tasks() -> list[dict]:
    """
    Read proactive follow-up tasks created by
    Amazon EventBridge Scheduler.
    """

    dynamodb = boto3.resource(
        "dynamodb",
        region_name=AWS_REGION,
    )

    table = dynamodb.Table(
        DYNAMO_TABLE
    )

    response = table.scan(
        FilterExpression=(
            "begins_with(case_id, :prefix)"
        ),
        ExpressionAttributeValues={
            ":prefix": "PROACTIVE_DEMO_"
        },
    )

    tasks = response.get(
        "Items",
        [],
    )

    tasks.sort(
        key=lambda item: item.get(
            "updated_at",
            "",
        ),
        reverse=True,
    )

    return tasks


def reset_demo_state():
    keys_to_clear = [
        "carecanopy_result",
        "workflow_case_id",
        "clarification_round",
        "base_report",
        "last_clarification",
    ]

    for key in keys_to_clear:
        st.session_state.pop(
            key,
            None,
        )


def escalation_label(decision) -> str:
    if decision.escalation_type is None:
        return "—"

    value = decision.escalation_type.value

    return ESCALATION_LABELS.get(
        value,
        value,
    )


def run_pipeline(
    case: dict,
) -> dict:

    decision = route_case(case)

    action_result = execute_actions(
        case,
        decision,
    )

    store = DynamoWorkflowStateStore()

    state = store.apply_actions(
        case,
        action_result,
    )

    return {
        "decision": decision,
        "actions": action_result,
        "state": state,
    }


# =========================================================
# HEADER
# =========================================================

st.html(
    dedent("""
    <div class="product-shell">
        <div class="product-eyebrow">
            Community rehabilitation workspace
        </div>

        <div class="product-title-row">
            <div>
                <div class="care-title">CareCanopy</div>
                <div class="care-subtitle">
                    AI Agent for Safe Delegation in Community Rehabilitation
                    <br>
                    <span class="tagline">
                        Handle the routine. Clarify the uncertain.
                        Escalate the clinical.
                    </span>
                </div>
            </div>
        </div>

        <div class="principle-row">
            <span class="principle-chip">LLM reasoning for ambiguity</span>
            <span class="principle-chip">Selected deterministic boundaries</span>
            <span class="principle-chip">Qualified human clinical authority</span>
        </div>

        <div class="workflow-strip">
            <div class="workflow-step">
                <b>1 · Observe</b>
                Frontline follow-up report
            </div>
            <div class="workflow-step">
                <b>2 · Reason</b>
                Context-aware routing proposal
            </div>
            <div class="workflow-step">
                <b>3 · Enforce</b>
                Selected hard-boundary check
            </div>
            <div class="workflow-step">
                <b>4 · Act / Review</b>
                Workflow action or human hand-off
            </div>
        </div>
    </div>
    """)
)


# =========================================================
# PROACTIVE BACKGROUND TASK
# =========================================================

try:
    proactive_tasks = (
        load_proactive_tasks()
    )
except Exception:
    proactive_tasks = []


if proactive_tasks:

    latest_task = proactive_tasks[0]

    reason = latest_task.get(
        "reason",
        "Scheduled follow-up is overdue.",
    )

    source = latest_task.get(
        "task_source",
        "Amazon EventBridge Scheduler",
    )

    task_count = len(proactive_tasks)
    task_word = "task" if task_count == 1 else "tasks"

    background_html = (
        '<div class="background-task">'
        '<div class="background-task-title">'
        '⚡ Background task detected'
        '</div>'
        '<div class="background-task-main">'
        f'{task_count} overdue rehabilitation follow-up '
        f'{task_word} detected'
        '</div>'
        '<div class="background-task-meta">'
        f'Latest task: {reason}'
        '<br>'
        f'Created automatically by {source}. '
        'The overdue follow-up is surfaced before the worker '
        'has to create the task manually.'
        '</div>'
        '</div>'
    )

    st.markdown(
        background_html,
        unsafe_allow_html=True,
    )

else:

    background_html = (
        '<div class="background-task">'
        '<div class="background-task-title">'
        'Proactive follow-up workflow active'
        '</div>'
        '<div class="background-task-meta">'
        'Amazon EventBridge Scheduler checks scheduled follow-ups '
        'and can create overdue tasks.'
        '</div>'
        '</div>'
    )

    st.markdown(
        background_html,
        unsafe_allow_html=True,
    )


# =========================================================
# SIDEBAR
# =========================================================

cases = load_dev_cases()

with st.sidebar:

    st.markdown(
        '<div class="sidebar-brand">Follow-up Queue</div>'
        '<div class="sidebar-copy">Select a synthetic follow-up scenario for the demo workspace.</div>',
        unsafe_allow_html=True,
    )

    case_index = st.selectbox(
        "Select follow-up",
        options=range(
            len(cases)
        ),
        format_func=lambda index: (
            f"{cases[index]['id']} — "
            f"{cases[index]['title']}"
        ),
        key="case_selector",
        on_change=reset_demo_state,
    )

    selected_case = (
        cases[case_index]
    )

    st.markdown(
        '<span class="demo-badge">Demo data · Synthetic</span>',
        unsafe_allow_html=True,
    )

    st.caption(
        "The frozen evaluation benchmark remains sealed."
    )

    st.divider()

    st.caption(
        "Technical stack\n\n"
        "Strands Agents SDK · Amazon Bedrock · "
        "Amazon DynamoDB · Amazon EventBridge Scheduler"
    )


# =========================================================
# CASE OVERVIEW
# =========================================================

left, right = st.columns(
    [1, 1.25]
)


with left:

    st.markdown(
        '<div class="section-kicker">'
        'Patient snapshot'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.container(
        border=True,
    ):

        for key, value in (
            selected_case[
                "patient_context"
            ].items()
        ):

            label = CONTEXT_LABELS.get(
                key,
                key.replace(
                    "_",
                    " ",
                ).title(),
            )

            if key == "weeks_post_stroke":
                value = (
                    f"{value} weeks"
                )

            st.markdown(
                f"**{label}:** {value}"
            )


with right:

    st.markdown(
        '<div class="section-kicker">'
        'Frontline observation'
        '</div>',
        unsafe_allow_html=True,
    )

    current_report = (
        st.text_area(
            "Current follow-up report",
            value=selected_case[
                "current_report"
            ],
            height=180,
            label_visibility="collapsed",
            key=(
                f"report_"
                f"{selected_case['id']}"
            ),
        )
    )


run_button = st.button(
    "Analyse & route follow-up",
    type="primary",
    use_container_width=True,
)


# =========================================================
# INITIAL RUN
# =========================================================

if run_button:

    reset_demo_state()

    workflow_case_id = (
        f"{selected_case['id']}_UI_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"
    )

    demo_case = dict(
        selected_case
    )

    demo_case["id"] = (
        workflow_case_id
    )

    demo_case["current_report"] = (
        current_report
    )

    with st.spinner(
        "CareCanopy is reviewing "
        "the follow-up report..."
    ):

        result = run_pipeline(
            demo_case
        )

    st.session_state[
        "carecanopy_result"
    ] = result

    st.session_state[
        "workflow_case_id"
    ] = workflow_case_id

    st.session_state[
        "clarification_round"
    ] = 0

    st.session_state[
        "base_report"
    ] = current_report

    st.session_state[
        "last_clarification"
    ] = None


# =========================================================
# RESULT
# =========================================================

if (
    "carecanopy_result"
    in st.session_state
):

    result = st.session_state[
        "carecanopy_result"
    ]

    decision = result[
        "decision"
    ]

    action_result = result[
        "actions"
    ]

    state = result[
        "state"
    ]

    route = (
        decision.route.value
    )

    clarification_round = (
        st.session_state.get(
            "clarification_round",
            0,
        )
    )


    # -----------------------------------------------------
    # ROUTING HEADER
    # -----------------------------------------------------

    st.divider()

    st.markdown(
        "## Decision & Workflow"
    )

    if clarification_round == 1:

        st.info(
            "Re-routed after one clarification round. "
            "The MVP permits only one clarification round "
            "before unresolved uncertainty is handed to a human."
        )

        clarification_used = (
            st.session_state.get(
                "last_clarification"
            )
        )

        if clarification_used:

            with st.expander(
                "Clarification used for re-routing"
            ):

                st.write(
                    clarification_used
                )


    route_class = {
        "ROUTINE":
            "routine",

        "CLARIFY":
            "clarify",

        "ESCALATE":
            "escalate",
    }[route]

    decision_title = {
        "ROUTINE": "Routine workflow can proceed",
        "CLARIFY": "More information is needed",
        "ESCALATE": "Qualified human review is required",
    }[route]

    gate_summary = (
        "A selected hard-boundary override was applied."
        if decision.safety_gate_triggered
        else "No selected hard-boundary override was required."
    )

    st.html(
        dedent(f"""
        <div class="decision-shell">
            <div class="decision-title">{decision_title}</div>
            <div class="decision-copy">
                CareCanopy produced a structured routing proposal,
                then applied the deterministic boundary check.
                {gate_summary}
            </div>
        </div>
        """)
    )


    c1, c2, c3 = (
        st.columns(3)
    )


    with c1:

        st.markdown(
            '<div class="section-kicker">'
            'Route'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<span class="route-badge {route_class}">'
            f'{route}'
            f'</span>',
            unsafe_allow_html=True,
        )


    with c2:

        st.markdown(
            '<div class="section-kicker">'
            'Escalation type'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f"**{escalation_label(decision)}**"
        )


    with c3:

        st.markdown(
            '<div class="section-kicker">'
            'Deterministic safety gate'
            '</div>',
            unsafe_allow_html=True,
        )

        if (
            decision
            .safety_gate_triggered
        ):

            st.markdown(
                '<span class="route-badge safety-on">'
                'TRIGGERED'
                '</span>',
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                '<span class="route-badge safety-off">'
                'Not triggered'
                '</span>',
                unsafe_allow_html=True,
            )


    # -----------------------------------------------------
    # ROUTE MESSAGE
    # -----------------------------------------------------

    if (
        decision.escalation_type
        and
        decision.escalation_type.value
        == "URGENT_MEDICAL"
    ):

        st.html(
            dedent("""
            <div class="hero-urgent">

                <div class="hero-title">
                    Urgent dual-path escalation
                </div>

                <div class="hero-text">
                    CareCanopy directs the case to the
                    appropriate urgent medical pathway
                    while also recording a clinical-team
                    notification action in workflow state.
                    Qualified humans retain clinical authority.
                </div>

            </div>
            """)
        )

        urgent_left, urgent_right = (
            st.columns(2)
        )

        with urgent_left:
            st.error(
                "🚨 Immediate medical pathway"
            )

        with urgent_right:
            st.info(
                "👥 Clinical team notification action"
            )


    elif route == "ROUTINE":

        st.success(
            "✅ Routine follow-up can be completed "
            "within the existing specialist-approved plan."
        )


    elif route == "CLARIFY":

        st.warning(
            "❓ Additional information is required "
            "before safe routing can be completed."
        )


    elif (
        decision.escalation_type
        and
        decision.escalation_type.value
        == "SCOPE_BOUNDARY"
    ):

        st.warning(
            "The requested action exceeds the delegated "
            "scope. Human clinical judgement is required."
        )


    # -----------------------------------------------------
    # WHY
    # -----------------------------------------------------

    st.markdown(
        "### Decision rationale"
    )

    st.write(
        decision.rationale
    )


    if decision.evidence:

        with st.container(
            border=True,
        ):

            st.markdown(
                "**Evidence from report**"
            )

            for evidence in (
                decision.evidence
            ):

                st.markdown(
                    f"- {evidence}"
                )


    if (
        decision
        .safety_gate_reason
    ):

        st.warning(
            "🛡️ "
            + decision
            .safety_gate_reason
        )


    # -----------------------------------------------------
    # CLARIFICATION WORKFLOW
    # -----------------------------------------------------

    if (
        route == "CLARIFY"
        and
        clarification_round == 0
    ):

        st.markdown(
            "### Clarification required"
        )

        with st.container(
            border=True,
        ):

            for question in (
                decision
                .missing_information
            ):

                st.markdown(
                    f"- {question}"
                )


        clarification_text = (
            st.text_area(
                "Additional observation from the frontline worker",
                placeholder=(
                    "Enter only the additional information "
                    "obtained from the follow-up."
                ),
                height=120,
                key=(
                    "clarification_input_"
                    + str(
                        state[
                            "case_id"
                        ]
                    )
                ),
            )
        )


        reroute_button = (
            st.button(
                "Re-route with clarification",
                type="primary",
                use_container_width=True,
            )
        )


        if reroute_button:

            if not (
                clarification_text
                .strip()
            ):

                st.warning(
                    "Please enter the clarification "
                    "before re-routing."
                )

            else:

                workflow_case_id = (
                    st.session_state.get(
                        "workflow_case_id"
                    )
                    or
                    state["case_id"]
                )

                base_report = (
                    st.session_state.get(
                        "base_report",
                        current_report,
                    )
                )

                reroute_case = dict(
                    selected_case
                )

                reroute_case["id"] = (
                    workflow_case_id
                )

                reroute_case[
                    "current_report"
                ] = (
                    base_report
                    + "\n\n"
                    + "Additional clarification "
                    + "provided by the frontline worker: "
                    + clarification_text.strip()
                )


                with st.spinner(
                    "CareCanopy is re-routing "
                    "with the new information..."
                ):

                    reroute_result = (
                        run_pipeline(
                            reroute_case
                        )
                    )


                st.session_state[
                    "carecanopy_result"
                ] = reroute_result

                st.session_state[
                    "clarification_round"
                ] = 1

                st.session_state[
                    "last_clarification"
                ] = (
                    clarification_text
                    .strip()
                )

                st.rerun()


    # -----------------------------------------------------
    # AGENT ACTIONS
    # -----------------------------------------------------

    st.markdown(
        "### Workflow Actions"
    )

    st.caption(
        "Permitted workflow actions executed after "
        "deterministic boundary checks."
    )

    actions = (
        action_result[
            "actions"
        ]
    )

    action_columns = (
        st.columns(
            min(
                max(
                    len(actions),
                    1,
                ),
                3,
            )
        )
    )


    for index, action in enumerate(
        actions
    ):

        target_column = (
            action_columns[
                index
                % len(
                    action_columns
                )
            ]
        )

        with target_column:

            with st.container(
                border=True,
            ):

                action_name = (
                    action["action"]
                )

                st.markdown(
                    "**"
                    + ACTION_LABELS.get(
                        action_name,
                        action_name,
                    )
                    + "**"
                )


                if (
                    action_name
                    == "REQUEST_CLARIFICATION"
                ):

                    st.caption(
                        "Clarification request created "
                        "for the frontline follow-up."
                    )

                elif (
                    action.get(
                        "description"
                    )
                ):

                    if action_name == "NOTIFY_CLINICAL_TEAM":
                        st.caption(
                            "Clinical-team notification action recorded "
                            "in workflow state."
                        )
                    else:
                        st.caption(
                            action[
                                "description"
                            ]
                        )

    # -----------------------------------------------------
    # HUMAN REVIEW PACKET
    # -----------------------------------------------------

    if action_result.get(
        "review_packet"
    ):

        packet = (
            action_result[
                "review_packet"
            ]
        )

        st.markdown(
            "### Human Review Packet"
        )

        with st.container(
            border=True,
        ):

            p1, p2, p3 = (
                st.columns(3)
            )


            with p1:

                st.markdown(
                    '<div class="section-kicker">'
                    'Escalation'
                    '</div>',
                    unsafe_allow_html=True,
                )

                packet_escalation = (
                    packet.get(
                        "escalation_type"
                    )
                )

                st.markdown(
                    "**"
                    + ESCALATION_LABELS.get(
                        packet_escalation,
                        packet_escalation
                        or "—",
                    )
                    + "**"
                )


            with p2:

                st.markdown(
                    '<div class="section-kicker">'
                    'Protocol trigger'
                    '</div>',
                    unsafe_allow_html=True,
                )

                triggers = (
                    packet.get(
                        "protocol_triggers",
                        [],
                    )
                )

                st.markdown(
                    "**"
                    + (
                        ", ".join(
                            triggers
                        )
                        if triggers
                        else "—"
                    )
                    + "**"
                )


            with p3:

                st.markdown(
                    '<div class="section-kicker">'
                    'Safety gate'
                    '</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "**Applied**"
                    if packet.get(
                        "safety_gate_triggered"
                    )
                    else
                    "**Not applied**"
                )


            st.markdown(
                "**Reason for human review**"
            )

            st.write(
                packet.get(
                    "rationale",
                    "—",
                )
            )


            evidence = packet.get(
                "evidence",
                [],
            )

            if evidence:

                st.markdown(
                    "**Evidence sent to reviewer**"
                )

                for item in evidence:

                    st.markdown(
                        f"- {item}"
                    )


            if packet.get(
                "safety_gate_triggered"
            ):

                st.warning(
                    "🛡️ "
                    + packet.get(
                        "safety_gate_reason",
                        "Deterministic safety "
                        "boundary applied.",
                    )
                )


        with st.expander(
            "Technical details"
        ):

            st.json(
                packet
            )


    # -----------------------------------------------------
    # WORKFLOW STATE
    # -----------------------------------------------------

    st.markdown(
        "### Workflow State"
    )

    s1, s2, s3 = (
        st.columns(3)
    )


    with s1:

        st.metric(
            "Status",
            STATUS_LABELS.get(
                state["status"],
                state["status"],
            ),
        )


    with s2:

        st.metric(
            "Human review",
            "Required"
            if state[
                "review_required"
            ]
            else
            "Not required",
        )


    with s3:

        st.metric(
            "Clinical notification action",
            "Recorded"
            if state[
                "clinical_team_notified"
            ]
            else
            "Not required",
        )


    # -----------------------------------------------------
    # AUDIT TRAIL
    # -----------------------------------------------------

    if state[
        "audit_log"
    ]:

        with st.expander(
            "Audit trail"
        ):

            audit_rows = []

            for item in (
                state[
                    "audit_log"
                ]
            ):

                audit_rows.append(
                    {
                        "Action":
                            ACTION_LABELS.get(
                                item[
                                    "action"
                                ],
                                item[
                                    "action"
                                ],
                            ),

                        "Source":
                            item[
                                "source"
                            ],

                        "Timestamp":
                            item[
                                "timestamp"
                            ],
                    }
                )


            st.dataframe(
                audit_rows,
                use_container_width=True,
                hide_index=True,
            )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Built with Strands Agents SDK on AWS · "
    "Amazon Bedrock · Amazon DynamoDB · "
    "Amazon EventBridge Scheduler · "
    "Qualified humans retain clinical authority."
)