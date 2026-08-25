# Promise

Promise is a GenLayer Intelligent Contract for resolving natural-language commitments after a deadline.

A creator records a commitment, explicit fulfillment criteria, a Unix deadline, and a creator-scoped reference. After the deadline, evidence can be submitted and GenLayer validators independently evaluate whether the commitment was fulfilled.

The contract resolves to one of three verdicts:

- `FULFILLED`
- `FAILED`
- `INCONCLUSIVE`

The final verdict, reasoning, and submitted evidence are persisted onchain.

## Why GenLayer

A deterministic smart contract can enforce a timestamp, ownership rule, or exact numeric threshold. It cannot reliably determine whether an arbitrary real-world commitment written in natural language was actually fulfilled.

Promise uses GenLayer's nondeterministic execution and validator consensus for that interpretation step while keeping the lifecycle and state transitions onchain.

The core flow is:

```text
Create commitment
      ↓
Wait until deadline
      ↓
Submit evidence
      ↓
GenLayer validator evaluation
      ↓
FULFILLED / FAILED / INCONCLUSIVE
      ↓
Persist final resolution onchain
```

## Contract behavior

Each promise stores:

- creator
- natural-language commitment
- fulfillment criteria
- deadline
- creator-scoped reference
- deterministic SHA-256 fingerprint of the original promise inputs
- status
- final verdict
- reasoning
- submitted evidence

Important safeguards:

- references are unique per creator
- the original commitment and fulfillment criteria cannot be changed after creation
- resolution is only allowed after the deadline
- a promise can only be resolved once
- empty and oversized inputs are rejected
- model responses must use the exact expected schema
- verdicts are restricted to `FULFILLED`, `FAILED`, or `INCONCLUSIVE`
- resolution state is written only after a valid consensus result is obtained

## GenLayer consensus design

The leader returns strict JSON containing:

```json
{
  "verdict": "FULFILLED",
  "reasoning": "..."
}
```

Validators independently evaluate the same commitment, criteria, and evidence.

Consensus compares the state-changing field, `verdict`, rather than requiring free-form reasoning text to be byte-for-byte identical. Each response still has to pass strict schema and reasoning validation.

This matters because independent validators can reach the same conclusion while wording their explanations differently.

## Public methods

### Views

- `ping()`
- `get_promise_count()`
- `get_promise(promise_id)`
- `is_reference_used(reference)`

### Writes

- `create_promise(commitment, fulfillment_criteria, deadline, reference)`
- `resolve_promise(promise_id, evidence)`

## Tests

The direct-mode test suite covers:

- promise creation
- input validation
- creator-scoped references
- persistence of original terms
- deadline enforcement
- `FULFILLED`
- `FAILED`
- `INCONCLUSIVE`
- malformed model output
- deterministic fingerprints
- duplicate resolution prevention
- failure-state safety

Final local result:

```text
18 passed
```

## Bradbury deployment

Final deployed contract:

```text
0x703AC5Aa250257AbA44034cC7AbeBd44e3C69362
```

Deployment transaction:

```text
0x1babc5f99422412cdacc897258e94c3027298fb48e9c241ee8d571ebd0bd2a23
```

The deployment finalized with:

```text
ACCEPTED
AGREE
FINISHED_WITH_RETURN
```

## Live Bradbury proof

A live promise was created with the commitment:

> Release the public beta of Project Atlas with wallet login and transaction history.

Fulfillment criteria required a publicly accessible beta containing both wallet login and transaction history.

After the deadline, evidence was submitted stating that the public beta was live and included both required features.

Resolution transaction:

```text
0x32891c2886b5d1c23a5171ac75054349b7a0030ba45daef73a28b1d3df8b100b
```

Bradbury consensus returned:

```text
status_name: ACCEPTED
resultName: AGREE
txExecutionResultName: FINISHED_WITH_RETURN
```

The stored promise state was then read back as:

```text
status: RESOLVED
verdict: FULFILLED
```

The reasoning and submitted evidence were also persisted onchain.

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
  '<EVIDENCE>'
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

## Status

Promise V1 is implemented, locally tested, deployed to GenLayer Bradbury, and proven with a live `FULFILLED` resolution.

## License

MIT
