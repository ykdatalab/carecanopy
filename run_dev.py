import json

from app.agent import route_case


DEV_CASES_PATH = "data/dev_cases.json"


def load_dev_cases() -> list[dict]:
    with open(DEV_CASES_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    cases = load_dev_cases()

    results = []

    for case in cases:
        print("\n" + "=" * 70)
        print(f"Case: {case['id']} - {case['title']}")
        print(f"Expected route: {case['expected_route']}")

        if "expected_escalation_type" in case:
            print(
                f"Expected escalation type: "
                f"{case['expected_escalation_type']}"
            )

        print("=" * 70)

        decision = route_case(case)

        actual_route = decision.route.value
        actual_escalation_type = (
            decision.escalation_type.value
            if decision.escalation_type
            else None
        )

        route_match = actual_route == case["expected_route"]

        escalation_match = True
        if "expected_escalation_type" in case:
            escalation_match = (
                actual_escalation_type
                == case["expected_escalation_type"]
            )

        passed = route_match and escalation_match

        print(
            json.dumps(
                decision.model_dump(mode="json"),
                indent=2,
                ensure_ascii=False,
            )
        )

        print(f"\nPASS: {passed}")

        results.append(
            {
                "id": case["id"],
                "expected_route": case["expected_route"],
                "actual_route": actual_route,
                "expected_escalation_type": case.get(
                    "expected_escalation_type"
                ),
                "actual_escalation_type": actual_escalation_type,
                "safety_gate_triggered": (
                    decision.safety_gate_triggered
                ),
                "passed": passed,
            }
        )

    print("\n\n" + "=" * 70)
    print("CARECANOPY DEVELOPMENT TEST SUMMARY")
    print("=" * 70)

    passed_count = sum(
        1 for result in results if result["passed"]
    )

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"

        print(
            f"{result['id']}: {status} | "
            f"{result['actual_route']} | "
            f"{result['actual_escalation_type']} | "
            f"Safety gate: "
            f"{result['safety_gate_triggered']}"
        )

    print(
        f"\nResult: {passed_count}/{len(results)} "
        f"development cases passed."
    )


if __name__ == "__main__":
    main()