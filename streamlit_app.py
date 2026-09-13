from datetime import datetime, timezone
from pathlib import Path
import json

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
    """
    <style>
        .stApp {
            background: #F7F9F8;
        }

        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .care-title {
            font-size: 2.55rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 0.2rem;
        }

        .care-subtitle {
            color: #667085;
            font-size: 1.02rem;
            line-height: 1.55;
            margin-bottom: 1.6rem;
        }

        .tagline {
            color: #344054;
            font-weight: 650;
        }

        .section-kicker {
            color: #667085;
            font-size: 0.76rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.35rem;
        }

        .route-badge {
            display: inline-block;
            padding: 0.48rem 0.9rem;
            border-radius: 999px;
            font-weight: 750;
            font-size: 0.92rem;
        }

        .routine {
            background: #E8F5EE;
            color: #176B4D;
        }

        .clarify {
            background: #FFF4D8;
            color: #8A5A00;
        }

        .escalate {
            background: #FDECEC;
            color: #B42318;
        }

        .safety-on {
            background: #FFF0E8;
            color: #B54708;
        }

        .safety-off {
            background: #EEF2F6;
            color: #475467;
        }

        .hero-urgent {
            background: #FFF7F5;
            border: 1px solid #FDA29B;
            border-radius: 16px;
            padding: 1.1rem 1.2rem;
            margin: 1rem 0;
        }

        .hero-title {
            font-size: 1.05rem;
            font-weight: 750;
            color: #B42318;
            margin-bottom: 0.35rem;
        }

        .hero-text {
            color: #475467;
            line-height: 1.5;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #E4E7EC;
            padding: 0.75rem 0.9rem;
            border-radius: 12px;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.22rem;
        }

        div.stButton > button {
            border-radius: 10px;
            min-height: 3rem;
            font-weight: 700;
            background-color: #176B4D;
            border-color: #176B4D;
            color: white;
        }

        div.stButton > button:hover {
            background-color: #12543D;
            border-color: #12543D;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# CONSTANTS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DEV_CASES_PATH = BASE_DIR / "data" / "dev_cases.json"


ACTION_LABELS = {
    "COMPLETE_ROUTINE_FOLLOWUP":
        "Complete routine follow-up",

    "REQUEST_CLARIFICATION":
        "Request clarification",

    "ISSUE_IMMEDIATE_MEDICAL_GUIDANCE":
        "Immediate medical pathway",

    "NOTIFY_CLINICAL_TEAM":
        "Notify clinical team",

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
# HELPERS
# =========================================================

@st.cache_data
def load_dev_cases() -> list[dict]:
    with open(
        DEV_CASES_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


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

st.markdown(
    '<div class="care-title">CareCanopy</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="care-subtitle">
        AI Agent for Safe Delegation in Community Rehabilitation
        <br>
        <span class="tagline">
            Handle the routine. Clarify the uncertain.
            Escalate the clinical.
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SIDEBAR
# =========================================================

cases = load_dev_cases()

with st.sidebar:

    st.markdown("### Demo Cases")

    case_index = st.selectbox(
        "Synthetic development case",
        options=range(len(cases)),
        format_func=lambda index: (
            f"{cases[index]['id']} — "
            f"{cases[index]['title']}"
        ),
        key="case_selector",
        on_change=reset_demo_state,
    )

    selected_case = cases[case_index]

    st.caption(
        "Development cases only. "
        "The frozen evaluation benchmark remains sealed."
    )

    st.divider()

    st.caption(
        "AWS stack\n\n"
        "Strands Agents SDK · Amazon Bedrock · "
        "Amazon DynamoDB"
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
        'Patient context'
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
                value = f"{value} weeks"

            st.markdown(
                f"**{label}:** {value}"
            )


with right:

    st.markdown(
        '<div class="section-kicker">'
        'Current follow-up report'
        '</div>',
        unsafe_allow_html=True,
    )

    current_report = st.text_area(
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


run_button = st.button(
    "Run CareCanopy",
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

    route = decision.route.value

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
        "## Routing Result"
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


    c1, c2, c3 = st.columns(3)


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
    # ROUTE-SPECIFIC MESSAGE
    # -----------------------------------------------------

    if (
        decision.escalation_type
        and
        decision.escalation_type.value
        == "URGENT_MEDICAL"
    ):

        st.markdown(
            """
            <div class="hero-urgent">
                <div class="hero-title">
                    Urgent dual-path escalation
                </div>

                <div class="hero-text">
                    CareCanopy directs the case to the
                    appropriate urgent medical pathway
                    while also recording an action to
                    notify the responsible rehabilitation
                    or clinical team.
                    Qualified humans retain clinical authority.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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
        "### Why this route?"
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
            "### Clarification Needed"
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
        "### Agent Actions"
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
    # AUDIT
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
    "Qualified humans retain clinical authority."
)