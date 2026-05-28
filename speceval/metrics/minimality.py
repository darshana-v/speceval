"""Minimality metric: is the generated spec over-constrained?

A spec is *minimal* if removing any single clause causes the verifier to
either still pass (clause was redundant) or fail (clause was necessary).
The minimality score is the fraction of clauses that are necessary.

High minimality = tight spec with no redundant assertions.
Low minimality = over-constrained spec that restates things the verifier
already knows, or adds vacuously true conditions.

This is a novel metric not present in FormalBench.
"""

import os
import re
import tempfile
import shutil
from typing import Dict, List, Tuple

from ..verifiers import create_verifier
from ..verifiers.base import VerificationResult, VerificationStatus

CLAUSE_PATTERNS = {
    "java": re.compile(
        r"(//@\s*(requires|ensures|invariant|assignable|assert)\s+[^;]+;)",
        re.MULTILINE,
    ),
    "c": re.compile(
        r"(/\*@\s*(requires|ensures|loop invariant|assigns|assert)\s+[^;]+;\s*\*/)",
        re.MULTILINE,
    ),
    "rust": re.compile(
        r"(#\[(requires|ensures|invariant)\([^\]]+\)\])",
        re.MULTILINE,
    ),
    "solidity": re.compile(
        r"((?:require|assert)\s*\([^)]+\)\s*;)",
        re.MULTILINE,
    ),
}


def extract_clauses(source: str, language: str) -> List[Tuple[str, int]]:
    """Extract spec clauses and their positions from annotated source."""
    pattern = CLAUSE_PATTERNS.get(language)
    if pattern is None:
        raise ValueError(f"Unsupported language for minimality: {language}")
    return [(m.group(1), m.start()) for m in pattern.finditer(source)]


def eval_minimality(
    spec_dir: str,
    language: str = "java",
    timeout: int = 1800,
    data_ids: List[str] = None,
    **verifier_kwargs,
) -> Tuple[float, Dict[str, dict]]:
    """Evaluate minimality of generated specs.

    For each file, systematically removes one clause at a time and re-verifies.
    A clause is *necessary* if removing it causes verification to fail.

    Args:
        spec_dir: Directory of annotated source files.
        language: Target language.
        timeout: Per-verification timeout.
        data_ids: Optional subset of benchmark IDs.

    Returns:
        (avg_minimality_score, per_file_results)
        where per_file_results[id] = {
            "total_clauses": int,
            "necessary_clauses": int,
            "redundant_clauses": list[str],
            "minimality_score": float,
        }
    """
    ext = {"java": ".java", "c": ".c", "rust": ".rs", "solidity": ".sol"}[language]
    verifier = create_verifier(language, **verifier_kwargs)

    if data_ids is None:
        data_ids = [
            f[: -len(ext)]
            for f in os.listdir(spec_dir)
            if f.endswith(ext)
        ]

    per_file: Dict[str, dict] = {}
    scores: List[float] = []

    try:
        for data_id in data_ids:
            spec_path = os.path.join(spec_dir, data_id + ext)
            if not os.path.exists(spec_path):
                continue

            with open(spec_path) as f:
                source = f.read()

            clauses = extract_clauses(source, language)
            if not clauses:
                per_file[data_id] = {
                    "total_clauses": 0,
                    "necessary_clauses": 0,
                    "redundant_clauses": [],
                    "minimality_score": 1.0,
                }
                scores.append(1.0)
                continue

            necessary = 0
            redundant_clauses = []

            for clause_text, clause_pos in clauses:
                reduced_source = source.replace(clause_text, "", 1)

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=ext, delete=False
                ) as tmp:
                    tmp.write(reduced_source)
                    tmp_path = tmp.name

                try:
                    result = verifier.verify(tmp_path, timeout=timeout, basedir=data_id)
                    if result.status != VerificationStatus.VERIFIED:
                        necessary += 1
                    else:
                        redundant_clauses.append(clause_text)
                finally:
                    os.unlink(tmp_path)

            total = len(clauses)
            score = necessary / total if total > 0 else 1.0
            per_file[data_id] = {
                "total_clauses": total,
                "necessary_clauses": necessary,
                "redundant_clauses": redundant_clauses,
                "minimality_score": score,
            }
            scores.append(score)
    finally:
        verifier.clean_up()

    avg_score = sum(scores) / len(scores) if scores else 0.0
    return avg_score, per_file
