import json
from datetime import datetime, timedelta, timezone

import pytest


CONTRACT = "contracts/promise.py"


def future_timestamp(seconds=3600):
	return int((datetime.now(timezone.utc) + timedelta(seconds=seconds)).timestamp())


def deploy(direct_deploy):
	return direct_deploy(CONTRACT)


def test_ping_and_initial_state(direct_deploy):
	promise = deploy(direct_deploy)
	assert promise.ping() == "promise-v1"
	assert promise.get_promise_count() == 0


def test_create_persists_data_and_deterministic_fingerprint(direct_deploy, direct_alice, direct_vm):
	promise = deploy(direct_deploy)
	direct_vm.sender = direct_alice
	deadline = future_timestamp()
	promise_id = promise.create_promise("Deliver a report", "Report is published", deadline, "report-1")
	first = promise.get_promise(promise_id)

	assert first == {
		"id": 0,
		"creator": "0x" + direct_alice.hex(),
		"commitment": "Deliver a report",
		"fulfillment_criteria": "Report is published",
		"deadline": deadline,
		"reference": "report-1",
		"status": "PENDING",
		"verdict": "",
		"reasoning": "",
		"evidence": "",
		"fingerprint": first["fingerprint"],
	}
	assert len(first["fingerprint"]) == 64
	assert promise.get_promise(promise_id)["fingerprint"] == first["fingerprint"]
	assert promise.is_reference_used("report-1") is True


def test_references_are_creator_scoped(direct_deploy, direct_alice, direct_bob, direct_vm):
	promise = deploy(direct_deploy)
	deadline = future_timestamp()
	direct_vm.sender = direct_alice
	assert promise.create_promise("A", "A happens", deadline, "same") == 0
	with direct_vm.expect_revert("reference already used"):
		promise.create_promise("B", "B happens", deadline, "same")
	direct_vm.sender = direct_bob
	assert promise.create_promise("B", "B happens", deadline, "same") == 1
	assert promise.get_promise_count() == 2


@pytest.mark.parametrize("field_args", [
	("", "criteria", 1, "ref"),
	("commitment", "", 1, "ref"),
	("commitment", "criteria", 1, ""),
	("commitment", "criteria", -1, "ref"),
])
def test_creation_validation(direct_deploy, direct_vm, field_args):
	promise = deploy(direct_deploy)
	with direct_vm.expect_revert():
		promise.create_promise(*field_args)
	assert promise.get_promise_count() == 0


def test_oversized_inputs_are_rejected(direct_deploy, direct_vm):
	promise = deploy(direct_deploy)
	with direct_vm.expect_revert("too long"):
		promise.create_promise("x" * 10_001, "criteria", 1, "ref")
	with direct_vm.expect_revert("too long"):
		promise.create_promise("commitment", "criteria", 1, "x" * 257)


def test_deadline_is_enforced(direct_deploy, direct_vm):
	promise = deploy(direct_deploy)
	deadline = future_timestamp(60)
	promise.create_promise("Do it", "It is done", deadline, "deadline")
	direct_vm.mock_llm(r"Commitment:", json.dumps({"verdict": "FULFILLED", "reasoning": "done"}))
	with direct_vm.expect_revert("deadline has not passed"):
		promise.resolve_promise(0, "evidence")
	direct_vm.warp(datetime.fromtimestamp(deadline + 1, timezone.utc).isoformat())
	assert promise.resolve_promise(0, "evidence")["verdict"] == "FULFILLED"


@pytest.mark.parametrize("verdict", ["FULFILLED", "FAILED", "INCONCLUSIVE"])
def test_all_verdicts_are_stored(direct_deploy, direct_vm, verdict):
	promise = deploy(direct_deploy)
	promise.create_promise("Do it", "It is done", 1, "verdict-" + verdict)
	direct_vm.warp(datetime.fromtimestamp(2, timezone.utc).isoformat())
	direct_vm.mock_llm(r"Commitment:", json.dumps({"verdict": verdict, "reasoning": "reviewed"}))
	promise.resolve_promise(0, "evidence")
	stored = promise.get_promise(0)
	assert stored["status"] == "RESOLVED"
	assert stored["verdict"] == verdict
	assert stored["reasoning"] == "reviewed"
	assert stored["evidence"] == "evidence"


@pytest.mark.parametrize("response", [
	"not json",
	{"verdict": "FULFILLED"},
	{"verdict": "MAYBE", "reasoning": "unknown"},
	{"verdict": "FAILED", "reasoning": 42},
	{"verdict": "FAILED", "reasoning": "ok", "extra": True},
])
def test_malformed_model_output_is_rejected_without_mutation(direct_deploy, direct_vm, response):
	promise = deploy(direct_deploy)
	promise.create_promise("Do it", "It is done", 1, "malformed")
	direct_vm.warp(datetime.fromtimestamp(2, timezone.utc).isoformat())
	direct_vm.mock_llm(r"Commitment:", json.dumps(response) if isinstance(response, dict) else response)
	with direct_vm.expect_revert():
		promise.resolve_promise(0, "evidence")
	stored = promise.get_promise(0)
	assert stored["status"] == "PENDING"
	assert stored["verdict"] == ""
	assert stored["reasoning"] == ""
	assert stored["evidence"] == ""


def test_resolution_is_only_once(direct_deploy, direct_vm):
	promise = deploy(direct_deploy)
	promise.create_promise("Do it", "It is done", 1, "once")
	direct_vm.warp(datetime.fromtimestamp(2, timezone.utc).isoformat())
	direct_vm.mock_llm(r"Commitment:", json.dumps({"verdict": "FAILED", "reasoning": "not done"}))
	promise.resolve_promise(0, "first")
	with direct_vm.expect_revert("already been resolved"):
		promise.resolve_promise(0, "second")
	assert promise.get_promise(0)["evidence"] == "first"
