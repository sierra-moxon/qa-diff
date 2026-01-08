import argparse
import os
from qa_diff.diff_test_results import get_test_diffs


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
    
    args = parser.parse_args()
    
    os.makedirs("test_diffs", exist_ok=True)
    get_test_diffs(args.dev_result_path, args.ci_result_path)


if __name__ == "__main__":
    main()
