# Promise v3

Promise is a GenLayer Intelligent Contract for resolving natural-language commitments after a deadline using independently acquired web evidence and validator consensus.

Promise v3 binds both resolver authority and acceptable evidence sources before the deadline. At creation time, the creator commits:

- the commitment;
- the fulfillment criteria;
- the deadline;
- a creator-scoped reference; and
- an approved HTTPS source list.

The approved source list is validated at creation, persisted onchain, included in the deterministic promise fingerprint, and immutable for that promise. It is the only source set used during resolution.

## Trust model

The creator is also the resolver. That authority is fixed when the promise is created, and only the creator address may call `resolve_promise`. An arbitrary third party cannot race to resolve a pending promise.

Caller-supplied evidence is unauthenticated supporting context. It may be false, incomplete, or adversarial and cannot replace source proof. Validators independently retrieve the stored precommitted HTTPS URLs inside the nondeterministic consensus path and independently evaluate the retrieved material against the stored commitment and criteria.

If every precommitted source is unavailable, the result is `INCONCLUSIVE` rather than being decided from caller text alone. Source contents are not treated as mathematically authoritative: the contract proves which URLs were committed and which material validators independently retrieved, not that a publisher is truthful or that the creator selected the best possible source.

## Lifecycle

```text
Create commitment, criteria, deadline, reference, and HTTPS sources
      ↓
Persist the source list and fingerprint before the deadline
      ↓
Wait until the deadline
      ↓
Creator submits promise_id + supporting evidence
      ↓
Leader and validators independently fetch the stored source list
      ↓
Validators independently evaluate the same precommitted evidence set
      ↓
Persist FULFILLED / FAILED / INCONCLUSIVE once
```

Resolution accepts only `promise_id` and supporting `evidence`. It does not accept new source URLs. A caller therefore cannot substitute a new source set at or after the deadline.

## Contract API

### Views

- `ping()`
- `get_promise_count()`
- `get_promise(promise_id)`
- `is_reference_used(reference)`

### Writes

```python
create_promise(
    commitment,
    fulfillment_criteria,
    deadline,
    reference,
    sources,
)

resolve_promise(
    promise_id,
    evidence,
)
```

`get_promise(promise_id)` exposes the creator, resolver, commitment, fulfillment criteria, deadline, reference, precommitted sources, fingerprint, status, verdict, reasoning, and caller evidence.

The possible verdicts are:

- `FULFILLED`
- `FAILED`
- `INCONCLUSIVE`

## Consensus boundary

Deterministic lifecycle rules are handled onchain. Before entering nondeterministic execution, the contract validates and captures the immutable promise data, the creator authority, and the stored source list. The consensus closures do not mutate contract storage.

The leader fetches every stored URL and evaluates the result. Each validator independently fetches those same stored URLs again and independently evaluates the result. Consensus binds the verdict, not free-form reasoning, so validators may use different explanations while agreeing on the semantic decision.

The prompt treats commitment text, fulfillment criteria, caller evidence, and fetched page text as untrusted data. Embedded commands, fake system messages, role changes, and output-format instructions in those fields are ignored.

## Contract safeguards

- creator and resolver are bound at creation;
- only the creator may resolve;
- resolution is blocked until after the stored deadline;
- a promise can be resolved only once;
- source URLs are validated before storage and must use `https://`;
- source lists are non-empty, duplicate-free, and limited to five URLs;
- each source URL is limited to 2,048 characters;
- fetched source text is limited to 8,000 characters per source before prompting;
- source URLs have no public post-creation mutator;
- the source list participates in the SHA-256 promise fingerprint;
- malformed model responses do not mutate promise state;
- all-source retrieval failure yields `INCONCLUSIVE`;
- caller evidence remains unauthenticated context;
- GenVM-compatible `gl.vm.UserError` paths are used.

## Tests and validation

Run the direct-mode suite with the installed GenVM runner:

```bash
gltest test/test_promise.py -q
```

The suite covers 31 tests, including:

- creation-time source validation and persistence;
- creator-only resolution and pending state after an unauthorized attempt;
- the absence of a resolution-time source argument;
- source-list fingerprint participation;
- the absence of a public source mutator;
- deadline enforcement;
- all three verdicts;
- unavailable-source fallback to `INCONCLUSIVE`;
- malformed model output without state mutation;
- one-time resolution;
- unauthenticated caller evidence and prompt-injection handling;
- leader and validator retrieval of every precommitted URL;
- validator disagreement and same-verdict/different-reasoning behavior.

Compile and validate the contract with:

```bash
python3 -m py_compile contracts/promise.py
genvm-lint check contracts/promise.py
```

The current validation result is:

```text
Lint passed (3 checks)
Validation passed
Contract: Promise
Methods: 6 (4 view, 2 write)
```

## Bradbury deployment

The verified v3 source is `contracts/promise.py`. The contract is deployed to Bradbury at the address and transaction recorded below after the source, lint, SDK validation, and Direct Mode checks passed.

Promise v3 contract:

```text
0x05A332eeE29A00543976e8328F6B10729a48A84e
```

Deployment transaction:

```text
0x344e37c2e8a2139ab1f74f82b51af6e5a931db32079117c48fa38fb042a495c5
```

The deployment was observed as `ACCEPTED` with consensus `AGREE` and execution `FINISHED_WITH_RETURN`. The SDK wait for finalization timed out, so this README does not claim that the deployment reached `FINALIZED`.

Bradbury RPC:

```text
https://rpc-bradbury.genlayer.com
```

The previous Promise v2 deployment `0x8b44023c995Ed001A83A122f23a4a6B147bcbdE5` is superseded and must not be used for the resubmission.

Live proof transaction IDs:

```text
create: 0x0aa021eae51a11c10ff1fc54ae7887cc91cb1db2380bec4318ec876572a5470d
resolve: 0xffd53b0df07fe1681aeed738d622c4b35e593e201a11b5c85b195e8c7d156b00
unauthorized attempt: not run; Direct Mode covers creator-only authorization and no second signer was used
```

The live proof created one future-deadline promise with a unique reference and precommitted HTTPS source list. A post-creation read verified the creator, resolver, sources, and fingerprint before the deadline. The authorized creator then submitted `resolve_promise` after the deadline using only `promise_id` and supporting evidence; the transaction reached `VALIDATORS_TIMEOUT` with `TIMEOUT` consensus and `FINISHED_WITH_RETURN`, so the promise correctly remained `PENDING` and no false resolution is claimed. The leader output recorded that the precommitted source was independently fetched and available. A higher-rotation retry was rejected by the consensus contract, and a normal-settings retry was also rejected after the timeout.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gltest test/test_promise.py -q
genvm-lint check contracts/promise.py
```

## Repository structure

```text
contracts/
  promise.py

test/
  test_promise.py

requirements.txt
README.md
LICENSE
```

## License

MIT
