# SpecEval

Multi-language formal specification inference benchmark for LLMs.

SpecEval evaluates how well language models generate formal specifications (pre/post-conditions, invariants, assertions) for source code across four languages:

| Language | Spec Format | Verifier | Status |
|----------|-------------|----------|--------|
| Java | JML | OpenJML | Supported |
| C | ACSL | Frama-C | Supported |
| Rust | Prusti contracts | Prusti | Supported |
| Solidity | require/assert | SMTChecker | Supported |

## What's novel

SpecEval goes beyond consistency checking (does the spec verify?) with two new metrics:

- **Minimality** — is the spec over-constrained? Systematically removes individual clauses to identify redundant assertions. A high minimality score means every clause in the spec is load-bearing.

- **Strength** — does the spec actually catch bugs? Runs the spec against code mutants and measures how many incorrect implementations are rejected. A spec can verify (consistent) but still be too weak to catch real bugs.

Together with consistency, these three metrics characterize spec quality along orthogonal axes:
- **Consistent but weak** — the spec is correct but trivial (e.g., `ensures true`)
- **Consistent but redundant** — the spec works but has unnecessary clauses
- **Consistent, strong, and minimal** — the gold standard

## Quick start

```bash
pip install -e .

# Generate and evaluate Solidity specs with Claude
python -m speceval.run \
    --dataset datasets/solidity \
    --output output/solidity-claude \
    --language solidity \
    --provider claude \
    --model claude-sonnet-4-6

# Evaluate pre-generated specs for consistency
python -c "
from speceval import eval_consistency
rate, _, _ = eval_consistency('datasets/solidity/specs', 'output/results', language='solidity')
print(f'Consistency: {rate:.1%}')
"

# Evaluate minimality of generated specs
python -c "
from speceval import eval_minimality
score, details = eval_minimality('datasets/solidity/specs', language='solidity')
print(f'Minimality: {score:.1%}')
"
```

## Project structure

```
speceval/
├── speceval/
│   ├── verifiers/       # Language-specific verification backends
│   │   ├── base.py      # Abstract Verifier + VerificationResult
│   │   ├── openjml.py   # Java/JML via OpenJML (Docker)
│   │   ├── framac.py    # C/ACSL via Frama-C (Docker)
│   │   ├── prusti.py    # Rust/Prusti (Docker)
│   │   └── smtchecker.py # Solidity via solc SMTChecker (Docker)
│   ├── metrics/
│   │   ├── consistency.py  # Does the spec verify?
│   │   ├── minimality.py   # Is the spec over-constrained? (novel)
│   │   └── strength.py     # Does the spec catch bugs? (novel)
│   ├── inference/       # LLM providers for spec generation
│   │   ├── claude.py
│   │   └── openai_provider.py
│   ├── dataset/         # Benchmark loader
│   └── run.py           # CLI benchmark runner
├── datasets/            # Benchmark programs per language
│   ├── java/
│   ├── c/
│   ├── rust/
│   └── solidity/        # Smart contract benchmarks
├── docker/              # Verifier Docker images
└── tests/
```

## Docker images

Each verifier runs in a Docker container. Build the images:

```bash
# Solidity SMTChecker
docker build -t speceval/solidity:latest docker/solidity/

# Prusti (Rust) — from FormalBench
docker build --platform linux/amd64 -t formalbench/prusti:latest docker/prusti/

# OpenJML and Frama-C use upstream images:
# thanhlecong/openjml:latest
# framac/frama-c:26.0.debian
```

## Metrics

### Consistency
Does the generated spec verify against the source code? Binary per-file (verified/failed), reported as success rate.

### Minimality
For each verified spec, systematically remove one clause at a time:
- If verification still passes → clause was **redundant**
- If verification fails → clause was **necessary**
- `minimality = necessary_clauses / total_clauses`

### Strength
Given a spec and a set of code mutants (incorrect implementations):
- `strength = mutants_caught / total_killable_mutants`
- A weak spec verifies on correct code but also on buggy code
- A strong spec rejects buggy implementations
