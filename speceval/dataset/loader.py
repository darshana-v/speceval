import os
from dataclasses import dataclass
from typing import List, Optional

LANG_EXTENSIONS = {
    "java": ".java",
    "c": ".c",
    "rust": ".rs",
    "solidity": ".sol",
}


@dataclass
class BenchmarkItem:
    id: str
    language: str
    source_code: str
    gold_spec: Optional[str] = None


def load_benchmark(
    dataset_dir: str,
    language: str,
    ids: Optional[List[str]] = None,
) -> List[BenchmarkItem]:
    """Load benchmark items from a dataset directory.

    Expected structure:
        dataset_dir/
            code/       <- bare source files (no specs)
            specs/      <- gold-standard annotated files (optional)
    """
    if language not in LANG_EXTENSIONS:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Choose from {list(LANG_EXTENSIONS.keys())}"
        )

    ext = LANG_EXTENSIONS[language]
    code_dir = os.path.join(dataset_dir, "code")
    specs_dir = os.path.join(dataset_dir, "specs")

    assert os.path.isdir(code_dir), f"Code directory not found: {code_dir}"

    if ids is None:
        ids = sorted([
            f[: -len(ext)]
            for f in os.listdir(code_dir)
            if f.endswith(ext)
        ])

    items = []
    for item_id in ids:
        code_path = os.path.join(code_dir, item_id + ext)
        if not os.path.exists(code_path):
            continue

        with open(code_path) as f:
            source = f.read()

        gold_spec = None
        gold_path = os.path.join(specs_dir, item_id + ext)
        if os.path.exists(gold_path):
            with open(gold_path) as f:
                gold_spec = f.read()

        items.append(BenchmarkItem(
            id=item_id,
            language=language,
            source_code=source,
            gold_spec=gold_spec,
        ))

    return items
