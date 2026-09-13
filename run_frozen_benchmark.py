import argparse
import copy
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.agent import route_case
from app.schemas import Route


INPUT_PATH = Path("data/cases_blind_v0.json")
OUTPUT_DIR = Path("evaluation")
OUTPUT_PATH = OUTPUT_DIR / "frozen_agent_outputs_v1.json"

FREEZE_TAG = "carecanopy-agent-v1-freeze"
EXPECTED_CASE_COUNT = 18


def assert_agent_is_frozen() -> None:
    """
    Confirm that tracked files under app/ have not changed
    relative to the frozen evaluation tag.
    """
    result = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            FREEZE_TAG,
            "--",
            "app",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return

    if result.returncode == 1:
        raise RuntimeError(
            "Files under app/ differ from the frozen agent tag. "
            "Do not run the benchmark until the difference is resolved."
        )

    raise RuntimeError(
        "Could not verify the frozen agent state with git."
    )


def load_benchmark() -> dict:
    with INPUT_PATH.open("r", encoding="utf-8") as file:
        benchmark = json.load(file)

    cases = benchmark.get("cases", [])

    if len(cases) != EXPECTED_CASE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_CASE_COUNT} benchmark cases, "
            f"found {len(cases)}."
        )

    return benchmark


def build_first_pass_case(raw_case: dict) -> dict:
    """
    Convert the blind benchmark schema into the frozen agent's
    expected input schema.

    additional_info is deliberately excluded from the first pass.
    """
    report = raw_case.get("report", {})

    patient_context = {
        "patient": raw_case.get("patient", {}),
        "plan": raw_case.get("plan", {}),
        "recent_records": raw_case.get(
            "recent_records",
            [],
        ),
        "visit_type": report.get("visit_type"),
        "overdue": report.get("overdue"),
    }

    case_id = raw_case.get("id")

    return {
        "id": case_id,
        "case_id": case_id,
        "patient_context": patient_context,
        "current_report": report.get("text", ""),
        "clarification_round": 0,
    }


def build_second_pass_case(
    first_pass_case: dict,
    additional_info: str,
) -> dict:
    """
    Supply additional_info only after the frozen agent itself
    selected CLARIFY on the first pass.
    """
    case = copy.deepcopy(first_pass_case)

    original_report = case.get(
        "current_report",
        "",
    )

    case["current_report"] = (
        f"{original_report}\n\n"
        "Additional observation from the frontline worker:\n"
        f"{additional_info}"
    )

    case["clarification_round"] = 1

    return case


def decision_to_dict(decision) -> dict:
    return decision.model_dump(mode="json")


def run_smoke_test(benchmark: dict) -> None:
    """
    Run only the first benchmark case to verify that the adapter
    can successfully call the frozen agent.

    No case content or routing result is printed.
    """
    raw_case = benchmark["cases"][0]

    first_pass_case = build_first_pass_case(
        raw_case
    )

    route_case(first_pass_case)

    print()
    print("Frozen benchmark adapter smoke test: OK")
    print("No case content or routing result was displayed.")
    print()


def save_results(results: list[dict]) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "evaluation_name": (
            "CareCanopy Frozen Synthetic Benchmark"
        ),
        "freeze_tag": FREEZE_TAG,
        "benchmark_file": INPUT_PATH.name,
        "evaluated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "method": {
            "cases": EXPECTED_CASE_COUNT,
            "agent_frozen_before_evaluation": True,
            "first_pass_excludes_additional_info": True,
            "additional_info_only_after_clarify": True,
            "maximum_clarification_rounds": 1,
            "clinician_labels_revealed_before_run": False,
            "generator_answer_key_used": False,
            "case_text_printed_to_console": False,
        },
        "results": results,
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )


def run_full_benchmark(
    benchmark: dict,
) -> None:
    cases = benchmark["cases"]
    results = []

    print("=" * 72)
    print("CARECANOPY FROZEN BENCHMARK")
    print(f"Frozen agent: {FREEZE_TAG}")
    print(f"Cases: {len(cases)}")
    print("=" * 72)
    print()
    print(
        "Case contents and routing results "
        "will not be printed."
    )
    print()

    for index, raw_case in enumerate(
        cases,
        start=1,
    ):
        case_id = raw_case.get(
            "id",
            f"CASE_{index:02d}",
        )

        print(
            f"[{index:02d}/{len(cases)}] "
            f"{case_id} — running..."
        )

        try:
            first_pass_case = (
                build_first_pass_case(
                    raw_case
                )
            )

            first_decision = route_case(
                first_pass_case
            )

            result = {
                "case_id": case_id,
                "first_pass": (
                    decision_to_dict(
                        first_decision
                    )
                ),
                "clarification_used": False,
                "second_pass": None,
                "error": None,
            }

            if (
                first_decision.route
                == Route.CLARIFY
            ):
                additional_info = (
                    raw_case.get(
                        "additional_info",
                        "",
                    )
                )

                second_pass_case = (
                    build_second_pass_case(
                        first_pass_case,
                        additional_info,
                    )
                )

                second_decision = route_case(
                    second_pass_case
                )

                result[
                    "clarification_used"
                ] = True

                result[
                    "second_pass"
                ] = decision_to_dict(
                    second_decision
                )

            results.append(result)

            print(
                f"          {case_id} — OK"
            )

        except Exception as exc:
            results.append(
                {
                    "case_id": case_id,
                    "first_pass": None,
                    "clarification_used": False,
                    "second_pass": None,
                    "error": str(exc),
                }
            )

            print(
                f"          {case_id} — ERROR"
            )

        # Save after every case so completed work
        # survives a later interruption.
        save_results(results)

    success_count = sum(
        1
        for result in results
        if result["error"] is None
    )

    error_count = sum(
        1
        for result in results
        if result["error"] is not None
    )

    print()
    print("=" * 72)
    print("FROZEN BENCHMARK COMPLETE")
    print("=" * 72)
    print(
        f"Successful cases: "
        f"{success_count}/{len(cases)}"
    )
    print(f"Errors: {error_count}")
    print(
        f"Results saved to: "
        f"{OUTPUT_PATH}"
    )
    print()
    print(
        "Do not open the result file yet."
    )
    print(
        "Clinician labels and generator answer key "
        "remain sealed."
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Run one case only to verify "
            "the benchmark adapter."
        ),
    )

    args = parser.parse_args()

    assert_agent_is_frozen()

    benchmark = load_benchmark()

    if args.smoke:
        run_smoke_test(benchmark)
        return

    run_full_benchmark(benchmark)


if __name__ == "__main__":
    main()