import argparse
import os
from qa_diff.diff_test_results import get_test_diffs, compare_infores_sources


def main():
    parser = argparse.ArgumentParser(
        description="Analyze the difference between two automated test results."
    )
    parser.add_argument(
        "dev_result_path",
        help="Path to the dev environment test CSV output file"
    )
    parser.add_argument(
        "ci_result_path",
        help="Path to the CI environment test CSV output file"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "infores"],
        default="full",
        help="Analysis mode: 'full' for complete analysis, 'infores' for source comparison only"
    )
    parser.add_argument(
        "--infores-filter",
        help="Filter to specific infores (e.g., 'infores:ctd')"
    )
    
    args = parser.parse_args()
    
    os.makedirs("test_diffs", exist_ok=True)
    
    if args.mode == "full":
        get_test_diffs(args.dev_result_path, args.ci_result_path)
    elif args.mode == "infores":
        compare_infores_sources(args.dev_result_path, args.ci_result_path, args.infores_filter)


if __name__ == "__main__":
    main()
