from __future__ import annotations

import argparse

from cico_pipeline.config import load_config
from cico_pipeline.io import write_json
from cico_pipeline.stages import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the staged CICO reproduction pipeline.")
    parser.add_argument("--config", default="configs/cico_pipeline.yaml")
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--language", choices=["py", "java", "go"], default=None)
    parser.add_argument("--stage", choices=["index", "plan", "retrieve", "generate"], default="generate")
    parser.add_argument("--force-rebuild", action="store_true")
    parser.add_argument("--output", default=None, help="Optional path to save the final pipeline result JSON.")
    args = parser.parse_args()

    config = load_config(args.config)
    language = args.language or config["pipeline"].get("language", "py")
    result = run_pipeline(args.repo_path, args.query, language, config, args.force_rebuild, args.stage)

    if args.output:
        from pathlib import Path

        write_json(Path(args.output), result)

    if result["answer"]:
        print(result["answer"])
    else:
        print(f"Completed stage: {args.stage}")
    print(f"\nCache: {result['query_cache_dir']}")


if __name__ == "__main__":
    main()
