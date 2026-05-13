from sentinel_pr_review.benchmarking.runner import run_benchmark


def main() -> int:
    run_benchmark(manifest_path="benchmarks/manifest.json", output_path="benchmarks/results/latest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
