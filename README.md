# Promise

Promise is a GenLayer Intelligent Contract for resolving natural-language commitments after a deadline using independently acquired web evidence and validator consensus.

A creator records a commitment, explicit fulfillment criteria, a Unix deadline, and a creator-scoped reference. After the deadline, a resolver submits supporting context plus one or more HTTPS source URLs. GenLayer validators independently fetch those sources and independently judge whether the original commitment was fulfilled.

The contract resolves to one of three verdicts:

- `FULFILLED`
- `FAILED`
- `INCONCLUSIVE`

The final verdict, reasoning, caller-supplied evidence, and source URLs are persisted onchain.

## Why GenLayer

A deterministic smart contract can enforce timestamps, ownership, replay protection, and exact numeric rules. It cannot reliably interpret whether an arbitrary real-world commitment written in natural language was actually fulfilled.

Promise keeps deterministic lifecycle rules onchain while using GenLayer nondeterministic execution for two things that ordinary deterministic contracts cannot safely perform alone:

1. retrieving current external web content;
2. semantically evaluating that content against natural-language fulfillment criteria.

The core flow is:

```text
Create commitment
      ↓
Wait until deadline
      ↓
Submit supporting context + HTTPS source URLs
      ↓
Each validator independently fetches the sources
      ↓
Each validator independently evaluates the evidence
      ↓
FULFILLED / FAILED / INCONCLUSIVE
      ↓
Persist the consensus-bound resolution onchain
```

## Evidence trust model

Promise v2 does not treat caller-supplied evidence text as authoritative proof of real-world events.

The caller provides:

- supporting evidence text;
- up to five HTTPS source URLs.

The evidence text is explicitly treated as unauthenticated context and may be false, incomplete, or adversarial. For externally verifiable real-world claims, validators are instructed not to return `FULFILLED` solely because the caller asserts that something happened.

Instead, each validator independently retrieves the submitted URLs with GenLayer web access inside the nondeterministic consensus path and evaluates the fetched material together with the immutable commitment and fulfillment criteria.

This removes the previous v1 trust model in which a caller could describe an external event without the contract independently acquiring any external evidence.

### What this trust model does and does not prove

Independent acquisition verifies what the submitted URLs served to validators at resolution time. It does not by itself prove that a publisher is authoritative, that every web claim is objectively true, or that a caller selected the best possible sources.

The source URLs are caller-selected. Their contents are independently acquired by validators rather than copied from caller-supplied text.

If every submitted source is unavailable, Promise resolves the nondeterministic evaluation to `INCONCLUSIVE` rather than treating unauthenticated caller text as sufficient proof.

## Consensus and nondeterministic boundary

Promise deliberately separates deterministic state handling from nondeterministic work.

Before entering nondeterministic execution, the contract validates and captures the immutable promise data and submitted URLs. Inside the consensus closures, validators may perform web retrieval and LLM evaluation, but they do not mutate contract storage. State is written only after `gl.vm.run_nondet` returns a valid consensus result.

Each validator independently:

1. fetches the same submitted HTTPS source URLs;
2. constructs the adjudication prompt from the stored promise, caller context, and fetched sources;
3. evaluates the promise;
4. validates the model response schema.

Consensus binds the state-changing field, `verdict`, rather than requiring free-form reasoning text to be byte-for-byte identical. This allows validators to agree on the semantic decision while expressing different explanations.

Raw web page text is not compared with strict equality because independently fetched web content can vary between validators. The consensus target is the derived verdict.

## Prompt isolation

Commitment text, fulfillment criteria, caller evidence, and fetched web content are all treated as untrusted data.

The adjudication prompt explicitly instructs validators to ignore embedded commands, fake system messages, role changes, output-format overrides, and other instruction-like content inside those fields.

The test suite includes prompt-injection cases in:

- caller-supplied evidence;
- commitment text;
- fulfillment criteria;
- independently fetched source content;
- adversarial JSON-like payloads.

This is prompt-injection hardening, not a claim that prompt injection is mathematically impossible.

## Contract behavior

Each promise stores:

- creator;
- natural-language commitment;
- fulfillment criteria;
- deadline;
- creator-scoped reference;
- deterministic SHA-256 fingerprint of the original promise inputs;
- status;
- final verdict;
- reasoning;
- caller-supplied evidence;
- submitted source URLs.

Important safeguards:

- references are unique per creator;
- original commitment and fulfillment criteria cannot be changed after creation;
- resolution is only allowed after the deadline;
- a promise can only be resolved once;
- contract inputs are bounded and validated;
- source lists must be non-empty for resolution;
- a resolution accepts at most five sources;
- source URLs must use `https://`;
- duplicate source URLs are rejected;
- each source URL is limited to 2,048 characters;
- fetched source text is bounded to 8,000 characters per source before prompting;
- model responses must use the exact expected schema;
- verdicts are restricted to `FULFILLED`, `FAILED`, or `INCONCLUSIVE`;
- all-source retrieval failure yields `INCONCLUSIVE`;
- storage mutation occurs only after a valid consensus result;
- source URLs are persisted for auditability;
- contract errors use GenVM-compatible `gl.vm.UserError`;
- helper signatures pass the current GenVM linter.

## Public methods

### Views

- `ping()`
- `get_promise_count()`
- `get_promise(promise_id)`
- `is_reference_used(reference)`

### Writes

- `create_promise(commitment, fulfillment_criteria, deadline, reference)`
- `resolve_promise(promise_id, evidence, sources)`

`ping()` returns:

```text
promise-v2
```

## Tests

Run:

```bash
gltest test/test_promise.py -q
```

Current result:

```text
27 passed in 0.73s
```

The direct-mode suite covers:

- deployment and initial state;
- promise creation and persistence;
- deterministic fingerprints;
- creator-scoped reference protection;
- creation input validation;
- oversized inputs;
- deadline enforcement;
- all three verdicts;
- source URL persistence;
- malformed model output without state mutation;
- one-time resolution;
- empty source rejection;
- non-HTTPS source rejection;
- duplicate source rejection;
- maximum source-count enforcement;
- unavailable-source fallback to `INCONCLUSIVE`;
- prompt injection in caller evidence;
- fake `SYSTEM` instructions;
- prompt injection in criteria;
- prompt injection in commitment text;
- adversarial JSON-like payloads;
- prompt injection inside independently fetched source content;
- validator agreement;
- validator re-fetch behavior;
- validator disagreement;
- same verdict with different reasoning.

## GenVM lint

Promise v2 passes the current GenVM linter used for resubmission:

```bash
genvm-lint check contracts/promise.py
```

Result:

```text
✓ Lint passed (3 checks)
✓ Validation passed
  Contract: Promise
  Methods: 6 (4 view, 2 write)
```

This specifically addresses the previous lint rejection involving unsupported helper signatures and bare `ValueError` paths.

## Bradbury deployment

Promise v2 contract:

```text
0x8b44023c995Ed001A83A122f23a4a6B147bcbdE5
```

Deployment transaction:

```text
0xaea4ca9dcb32d2176c97c99d0fd936f554957f3d2ee99f260c536937db3e80c2
```

Deployment completed with:

```text
ACCEPTED
AGREE
FINISHED_WITH_RETURN
```

Live `ping()` returned:

```text
promise-v2
```

## Live Bradbury evidence-acquisition proof

A live promise was created with:

```text
commitment:
Publish the GenLayer documentation

fulfillment criteria:
The GenLayer documentation is publicly accessible online

reference:
promise-v2-live-001

promise id:
0
```

Creation transaction:

```text
0xf45759daa1f4bc5fdb306155570acbb710af6279dac81f47cb0590774ff45890
```

The resolution supplied the official GenLayer developer documentation URL:

```text
https://docs.genlayer.com/developers
```

Resolution transaction:

```text
0xc6252e1b20fa15e8295c951aed8570c157acab49b7094b3f8e233629f59b745e
```

After finalization, `get_promise(0)` returned:

```text
status: RESOLVED
verdict: FULFILLED
sources: ["https://docs.genlayer.com/developers"]
```

The persisted reasoning states that the independently fetched GenLayer developer source was available and contained documentation covering developer guides, protocol concepts, tooling, deployment, testing, and API references, establishing that the GenLayer documentation was publicly accessible online.

This live run demonstrates the v2 evidence path that was missing from the rejected version: the material external source is fetched by the contract's nondeterministic validator execution rather than accepted only as caller-supplied prose.

## Run locally

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the tests:

```bash
gltest test/test_promise.py -q
```

Run GenVM lint:

```bash
genvm-lint check contracts/promise.py
```

## Deploy

```bash
genlayer deploy \
  --contract contracts/promise.py \
  --rpc https://rpc-bradbury.genlayer.com
```

For nondeterministic resolution writes on Bradbury, the tested CLI invocation used an explicit fee distribution:

```bash
genlayer write \
  <CONTRACT_ADDRESS> \
  resolve_promise \
  --rpc https://rpc-bradbury.genlayer.com \
  --fees '{"distribution":{"leaderTimeunitsAllocation":"100","validatorTimeunitsAllocation":"200","rotations":["0"]}}' \
  --args \
  <PROMISE_ID> \
  '<SUPPORTING_EVIDENCE>' \
  '["https://example.com/source"]'
```

## Reviewer checklist

- Contract source passes current `genvm-lint` with zero diagnostics.
- Direct-mode suite passes: 27 tests.
- Real-world evidence is no longer judged only from caller-supplied prose.
- Validators independently acquire submitted HTTPS sources inside nondeterministic execution.
- Caller evidence remains explicitly unauthenticated supporting context.
- All-source retrieval failure resolves to `INCONCLUSIVE`.
- Nondeterministic execution does not mutate contract storage directly.
- Only a validated consensus result is persisted.
- Source URLs remain onchain for auditability.
- Deployed Bradbury contract returns `promise-v2`.
- Live Bradbury resolution persisted `RESOLVED / FULFILLED` with the independently fetched source URL.

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

## Status

Promise v2 is implemented, lint-clean, covered by 27 direct-mode tests, deployed to GenLayer Bradbury, and proven live with independent web evidence acquisition and a finalized `FULFILLED` resolution.

## License

MIT
