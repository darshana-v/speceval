"""Strength metric: how much does the spec actually constrain the implementation?

A spec is *strong* if it rejects many incorrect implementations (mutants).
We measure this by generating mutants of the original code and checking
whether the generated spec catches them (verification fails on mutants).

strength = (mutants caught by spec) / (total killable mutants)

This extends FormalBench's completeness metric with a clearer framing:
- Completeness asks "does the spec cover the code?"
- Strength asks "does the spec reject wrong code?"

A spec can be consistent (verifies on correct code) but weak (doesn't catch bugs).
The gold standard is a spec that is consistent, minimal, AND strong.
"""

import os
import json
from typing import Dict, List, Optional, Tuple

from ..verifiers import create_verifier
from ..verifiers.base import VerificationStatus

LANG_EXTENSIONS = {
    "java": ".java",
    "c": ".c",
    "rust": ".rs",
    "solidity": ".sol",
}


def eval_strength(
    spec_dir: str,
    mutant_dir: str,
    results_dir: str,
    language: str = "java",
    timeout: int = 1800,
    data_ids: Optional[List[str]] = None,
    **verifier_kwargs,
) -> Tuple[float, Dict[str, dict]]:
    """Evaluate strength of generated specs against code mutants.

    For each benchmark:
    1. Load the annotated spec from spec_dir/<id>.<ext>
    2. Load mutants from mutant_dir/<id>/mutant_*.<ext>
       (each mutant has the same spec but a modified implementation)
    3. Verify each mutant — if verification fails, the spec caught the bug.

    Args:
        spec_dir: Directory of annotated source files (code + spec).
        mutant_dir: Directory of mutants, organized as mutant_dir/<id>/mutant_*.<ext>.
        results_dir: Where to write per-file strength results.
        language: Target language.
        timeout: Per-verification timeout.
        data_ids: Optional subset of IDs.

    Returns:
        (avg_strength, per_file_results)
    """
    if language not in LANG_EXTENSIONS:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Choose from {list(LANG_EXTENSIONS.keys())}"
        )

    assert os.path.exists(spec_dir), f"Spec directory not found: {spec_dir}"
    assert os.path.exists(mutant_dir), f"Mutant directory not found: {mutant_dir}"
    os.makedirs(results_dir, exist_ok=True)

    ext = LANG_EXTENSIONS[language]
    verifier = create_verifier(language, **verifier_kwargs)

    if data_ids is None:
        data_ids = [
            d for d in os.listdir(mutant_dir)
            if os.path.isdir(os.path.join(mutant_dir, d))
        ]

    per_file: Dict[str, dict] = {}
    strengths: List[float] = []

    try:
        for data_id in data_ids:
            mutant_subdir = os.path.join(mutant_dir, data_id)
            if not os.path.isdir(mutant_subdir):
                continue

            mutant_files = sorted([
                f for f in os.listdir(mutant_subdir)
                if f.endswith(ext) and f.startswith("mutant_")
            ])

            if not mutant_files:
                continue

            caught = 0
            survived = 0
            mutant_results = []

            for mf in mutant_files:
                mutant_path = os.path.join(mutant_subdir, mf)
                result = verifier.verify(
                    mutant_path, timeout=timeout, basedir=f"{data_id}/{mf}"
                )

                killed = result.status in (
                    VerificationStatus.FAILED,
                    VerificationStatus.COMPILE_ERROR,
                )
                if killed:
                    caught += 1
                else:
                    survived += 1

                mutant_results.append({
                    "mutant": mf,
                    "killed": killed,
                    "status": result.status.value,
                    "error_count": result.error_count,
                })

            total = caught + survived
            strength = caught / total if total > 0 else 0.0

            per_file[data_id] = {
                "total_mutants": total,
                "caught": caught,
                "survived": survived,
                "strength": strength,
                "mutants": mutant_results,
            }
            strengths.append(strength)

            result_path = os.path.join(results_dir, data_id + ".json")
            with open(result_path, "w") as f:
                json.dump(per_file[data_id], f, indent=2)
    finally:
        verifier.clean_up()

    avg_strength = sum(strengths) / len(strengths) if strengths else 0.0
    return avg_strength, per_file
