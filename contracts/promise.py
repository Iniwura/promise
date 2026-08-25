import hashlib
import json
from datetime import datetime, timezone

import genlayer.gl as gl
from genlayer.py.types import bigint


class Promise(gl.Contract):
	MAX_TEXT_LENGTH = 10_000
	MAX_REFERENCE_LENGTH = 256
	MAX_EVIDENCE_LENGTH = 20_000
	MAX_REASONING_LENGTH = 10_000

	commitments: gl.storage.TreeMap[bigint, str]
	criteria: gl.storage.TreeMap[bigint, str]
	creators: gl.storage.TreeMap[bigint, str]
	deadlines: gl.storage.TreeMap[bigint, bigint]
	references: gl.storage.TreeMap[bigint, str]
	fingerprints: gl.storage.TreeMap[bigint, str]
	statuses: gl.storage.TreeMap[bigint, str]
	verdicts: gl.storage.TreeMap[bigint, str]
	reasonings: gl.storage.TreeMap[bigint, str]
	evidences: gl.storage.TreeMap[bigint, str]
	reference_ids: gl.storage.TreeMap[str, bigint]
	next_id: bigint

	def __init__(self):
		self.next_id = 0

	@staticmethod
	def _require_text(value: str, field: str, maximum: int) -> None:
		if not isinstance(value, str) or not value.strip():
			raise ValueError(f"{field} must not be empty")
		if len(value) > maximum:
			raise ValueError(f"{field} is too long")

	@staticmethod
	def _sender() -> str:
		sender = gl.message.sender_address
		if isinstance(sender, bytes):
			return "0x" + sender.hex()
		return str(sender).lower()

	@staticmethod
	def _reference_key(creator: str, reference: str) -> str:
		return creator + "\x00" + reference

	@staticmethod
	def _now() -> int:
		return int(datetime.now(timezone.utc).timestamp())

	@staticmethod
	def _validate_response(response):
		if type(response) is not dict or set(response.keys()) != {"verdict", "reasoning"}:
			raise ValueError("model response must contain only verdict and reasoning")
		verdict = response["verdict"]
		reasoning = response["reasoning"]
		if verdict not in {"FULFILLED", "FAILED", "INCONCLUSIVE"}:
			raise ValueError("model response contains an invalid verdict")
		if type(reasoning) is not str or not reasoning.strip():
			raise ValueError("model reasoning must be a non-empty string")
		if len(reasoning) > Promise.MAX_REASONING_LENGTH:
			raise ValueError("model reasoning is too long")
		return {"verdict": verdict, "reasoning": reasoning}

	def _prompt(self, promise_id: int, evidence: str) -> str:
		return (
			"Evaluate whether the original commitment was fulfilled using the evidence. "
			"Return JSON with exactly two keys: verdict and reasoning. verdict must be "
			"exactly FULFILLED, FAILED, or INCONCLUSIVE.\n"
			f"Commitment: {self.commitments[promise_id]}\n"
			f"Fulfillment criteria: {self.criteria[promise_id]}\n"
			f"Evidence: {evidence}"
		)

	@gl.public.view
	def ping(self) -> str:
		return "promise-v1"

	@gl.public.view
	def get_promise_count(self) -> int:
		return self.next_id

	@gl.public.view
	def is_reference_used(self, reference: str) -> bool:
		self._require_text(reference, "reference", self.MAX_REFERENCE_LENGTH)
		return self._reference_key(self._sender(), reference) in self.reference_ids

	@gl.public.view
	def get_promise(self, promise_id: int) -> dict:
		if not isinstance(promise_id, int) or promise_id < 0 or promise_id >= self.next_id:
			raise ValueError("unknown promise id")
		return {
			"id": promise_id,
			"creator": self.creators[promise_id],
			"commitment": self.commitments[promise_id],
			"fulfillment_criteria": self.criteria[promise_id],
			"deadline": self.deadlines[promise_id],
			"reference": self.references[promise_id],
			"status": self.statuses[promise_id],
			"verdict": self.verdicts[promise_id],
			"reasoning": self.reasonings[promise_id],
			"evidence": self.evidences[promise_id],
			"fingerprint": self.fingerprints[promise_id],
		}

	@gl.public.write
	def create_promise(
		self, commitment: str, fulfillment_criteria: str, deadline: int, reference: str
	) -> int:
		self._require_text(commitment, "commitment", self.MAX_TEXT_LENGTH)
		self._require_text(fulfillment_criteria, "fulfillment criteria", self.MAX_TEXT_LENGTH)
		self._require_text(reference, "reference", self.MAX_REFERENCE_LENGTH)
		if type(deadline) is not int or deadline < 0:
			raise ValueError("deadline must be a non-negative Unix timestamp")

		creator = self._sender()
		key = self._reference_key(creator, reference)
		if key in self.reference_ids:
			raise ValueError("reference already used by creator")

		promise_id = self.next_id
		fingerprint = hashlib.sha256(
			json.dumps(
				{
					"commitment": commitment,
					"criteria": fulfillment_criteria,
					"creator": creator,
					"deadline": deadline,
					"reference": reference,
				},
				sort_keys=True,
				separators=(",", ":"),
			).encode("utf-8")
		).hexdigest()
		self.commitments[promise_id] = commitment
		self.criteria[promise_id] = fulfillment_criteria
		self.creators[promise_id] = creator
		self.deadlines[promise_id] = deadline
		self.references[promise_id] = reference
		self.fingerprints[promise_id] = fingerprint
		self.statuses[promise_id] = "PENDING"
		self.verdicts[promise_id] = ""
		self.reasonings[promise_id] = ""
		self.evidences[promise_id] = ""
		self.reference_ids[key] = promise_id
		self.next_id += 1
		return promise_id

	@gl.public.write
	def resolve_promise(self, promise_id: int, evidence: str) -> dict:
		self._require_text(evidence, "evidence", self.MAX_EVIDENCE_LENGTH)
		if not isinstance(promise_id, int) or promise_id < 0 or promise_id >= self.next_id:
			raise ValueError("unknown promise id")
		if self.statuses[promise_id] != "PENDING":
			raise ValueError("promise has already been resolved")
		if self._now() <= self.deadlines[promise_id]:
			raise ValueError("promise deadline has not passed")

		prompt = self._prompt(promise_id, evidence)

		def leader():
			return gl.nondet.exec_prompt(prompt, response_format="json")

		def validator(result):
			if not isinstance(result, gl.vm.Return):
				return False
			try:
				candidate = self._validate_response(result.calldata)
				observed = gl.nondet.exec_prompt(prompt, response_format="json")
				return candidate == self._validate_response(observed)
			except Exception:
				return False

		response = gl.vm.run_nondet(leader, validator)
		validated = self._validate_response(response)
		self.statuses[promise_id] = "RESOLVED"
		self.verdicts[promise_id] = validated["verdict"]
		self.reasonings[promise_id] = validated["reasoning"]
		self.evidences[promise_id] = evidence
		return validated
