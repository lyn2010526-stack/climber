"""Task completion must expose independent acceptance evidence."""

from app.core.task_worker import _normalise_result


def test_handler_result_without_acceptance_is_explicitly_unverified() -> None:
    result = _normalise_result({"output": "patch created"})

    assert result["output"] == "patch created"
    assert result["verification"] == {
        "status": "unverified",
        "reason": "handler returned no acceptance evidence",
    }


def test_handler_acceptance_evidence_is_preserved_and_marked_verified() -> None:
    result = _normalise_result(
        {
            "output": "tests passed",
            "acceptance": {"passed": True, "tests": ["pytest tests/test_task.py"]},
        }
    )

    assert result["acceptance"]["tests"] == ["pytest tests/test_task.py"]
    assert result["verification"]["status"] == "verified"


def test_rejected_acceptance_does_not_become_a_success_claim() -> None:
    result = _normalise_result(
        {"acceptance": {"passed": False, "reason": "required test failed"}}
    )

    assert result["verification"] == {
        "status": "rejected",
        "reason": "required test failed",
    }
