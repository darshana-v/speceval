"""SpecBench runner: generate specs with an LLM, then evaluate them.

Usage:
    python -m speceval.run --language solidity --provider claude --model claude-sonnet-4-6
    python -m speceval.run --language java --provider openai --model gpt-4o
"""

import argparse
import json
import os
import sys
import time

from .dataset import load_benchmark
from .inference import create_provider
from .verifiers import create_verifier
from .verifiers.base import VerificationStatus


LANG_EXTENSIONS = {
    "java": ".java",
    "c": ".c",
    "rust": ".rs",
    "solidity": ".sol",
}


def run_benchmark(
    dataset_dir: str,
    output_dir: str,
    language: str,
    provider_name: str,
    model: str = None,
    timeout: int = 1800,
    ids: list = None,
):
    ext = LANG_EXTENSIONS[language]
    items = load_benchmark(dataset_dir, language, ids=ids)
    provider = create_provider(provider_name)
    verifier = create_verifier(language)

    gen_dir = os.path.join(output_dir, "generated_specs")
    results_dir = os.path.join(output_dir, "results")
    os.makedirs(gen_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    summary = {
        "language": language,
        "provider": provider_name,
        "model": model,
        "total": 0,
        "verified": 0,
        "failed": 0,
        "compile_error": 0,
        "timeout": 0,
        "internal_error": 0,
        "items": [],
    }

    try:
        for item in items:
            print(f"[{item.id}] Generating spec...")
            gen_result = provider.generate_spec(
                item.source_code, language, model=model
            )

            spec_path = os.path.join(gen_dir, item.id + ext)
            with open(spec_path, "w") as f:
                f.write(gen_result.annotated_source)

            print(f"[{item.id}] Verifying...")
            ver_result = verifier.verify(spec_path, timeout=timeout, basedir=item.id)

            item_result = {
                "id": item.id,
                "status": ver_result.status.value,
                "error_count": ver_result.error_count,
                "duration_seconds": ver_result.duration_seconds,
                "prompt_tokens": gen_result.prompt_tokens,
                "completion_tokens": gen_result.completion_tokens,
            }
            summary["items"].append(item_result)
            summary["total"] += 1
            summary[ver_result.status.value] += 1

            result_path = os.path.join(results_dir, item.id + ".json")
            with open(result_path, "w") as f:
                json.dump(item_result, f, indent=2)

            print(f"[{item.id}] {ver_result.status.value} ({ver_result.error_count} errors)")
    finally:
        verifier.clean_up()

    summary_path = os.path.join(output_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    total = summary["total"]
    if total > 0:
        print(f"\n{'='*50}")
        print(f"Results: {summary['verified']}/{total} verified "
              f"({summary['verified']/total:.1%})")
        print(f"  Failed: {summary['failed']}, "
              f"Compile errors: {summary['compile_error']}, "
              f"Timeouts: {summary['timeout']}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run SpecBench evaluation")
    parser.add_argument("--dataset", required=True, help="Path to dataset directory")
    parser.add_argument("--output", required=True, help="Path to output directory")
    parser.add_argument(
        "--language", required=True,
        choices=["java", "c", "rust", "solidity"],
    )
    parser.add_argument("--provider", required=True, choices=["claude", "openai"])
    parser.add_argument("--model", default=None, help="Model name override")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--ids", nargs="*", default=None, help="Specific benchmark IDs")
    args = parser.parse_args()

    run_benchmark(
        dataset_dir=args.dataset,
        output_dir=args.output,
        language=args.language,
        provider_name=args.provider,
        model=args.model,
        timeout=args.timeout,
        ids=args.ids,
    )


if __name__ == "__main__":
    main()
