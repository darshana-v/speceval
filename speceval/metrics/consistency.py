"""Consistency metric: does the generated spec verify against the source code?

A spec is *consistent* if the verifier accepts it without errors.
This is the baseline metric shared with FormalBench.
"""

import os
import json
from typing import Dict, List, Optional, Tuple

from ..verifiers import create_verifier
from ..verifiers.base import VerificationResult, VerificationStatus

LANG_EXTENSIONS = {
    "java": ".java",
    "c": ".c",
    "rust": ".rs",
    "solidity": ".sol",
}


def eval_consistency(
    spec_dir: str,
    results_dir: str,
    language: str = "java",
    timeout: int = 1800,
    data_ids: Optional[List[str]] = None,
    **verifier_kwargs,
) -> Tuple[float, float, Dict[str, VerificationResult]]:
    """Evaluate consistency of generated specs.

    Args:
        spec_dir: Directory containing annotated source files (code + specs).
        results_dir: Directory to write per-file verification results.
        language: One of 'java', 'c', 'rust', 'solidity'.
        timeout: Per-file verification timeout in seconds.
        data_ids: Optional subset of benchmark IDs to evaluate.

    Returns:
        (success_rate, failure_rate, per_file_results)
    """
    if language not in LANG_EXTENSIONS:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Choose from {list(LANG_EXTENSIONS.keys())}"
        )

    assert os.path.exists(spec_dir), f"Spec directory not found: {spec_dir}"
    os.makedirs(results_dir, exist_ok=True)

    ext = LANG_EXTENSIONS[language]
    verifier = create_verifier(language, **verifier_kwargs)

    if data_ids is None:
        data_ids = [
            f[: -len(ext)]
            for f in os.listdir(spec_dir)
            if f.endswith(ext)
        ]

    results: Dict[str, VerificationResult] = {}
    n_success = 0
    n_failure = 0
    n_total = 0

    try:
        for data_id in data_ids:
            spec_path = os.path.join(spec_dir, data_id + ext)
            if not os.path.exists(spec_path):
                continue

            result = verifier.verify(spec_path, timeout=timeout, basedir=data_id)
            results[data_id] = result
            n_total += 1

            if result.status == VerificationStatus.VERIFIED:
                n_success += 1
            elif result.status == VerificationStatus.FAILED:
                n_failure += 1

            result_path = os.path.join(results_dir, data_id + ".json")
            with open(result_path, "w") as f:
                json.dump({
                    "data_id": data_id,
                    "status": result.status.value,
                    "error_count": result.error_count,
                    "duration_seconds": result.duration_seconds,
                }, f, indent=2)
    finally:
        verifier.clean_up()

    success_rate = n_success / n_total if n_total > 0 else 0.0
    failure_rate = n_failure / n_total if n_total > 0 else 0.0

    return success_rate, failure_rate, results
