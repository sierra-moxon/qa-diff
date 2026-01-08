# qa-diff

Analyze differences between automated test results from different environments (CI vs Dev).

## Installation

Install dependencies using uv:

```bash
make install
```

Or directly:

```bash
uv sync
```

## Usage

### Full Analysis (default)

Using Make:
```bash
make run DEV=path/to/dev.csv CI=path/to/ci.csv
```

Using the CLI directly:
```bash
uv run qa-diff path/to/dev.csv path/to/ci.csv
```

After installation:
```bash
qa-diff path/to/dev.csv path/to/ci.csv
```

### Infores Source Comparison

Compare which data sources (infores) appear in CI but not in Dev:

Using Make:
```bash
make infores DEV=path/to/dev.csv CI=path/to/ci.csv
```

Filter to a specific infores (e.g., CTD):
```bash
make infores DEV=path/to/dev.csv CI=path/to/ci.csv FILTER=infores:ctd
```

Using the CLI directly:
```bash
uv run qa-diff path/to/dev.csv path/to/ci.csv --mode infores
```

With filter:
```bash
uv run qa-diff path/to/dev.csv path/to/ci.csv --mode infores --infores-filter infores:ctd
```

## What it does

This tool:
- Compares test results between two environments (typically Dev and CI)
- Identifies tests that pass in CI but fail in Dev
- Analyzes data source disparities
- Generates detailed JSON reports in the `test_diffs/` directory

## Output

### Full Analysis Mode

Results are written to `test_diffs/`:
- `diff_test_results.json` - Summary of differing tests
- `missing_sources.json` - List of missing data sources
- `missing_source_counts.json` - Count of each missing source
- Individual test result files for detailed analysis

### Infores Comparison Mode

Results are written to `test_diffs/`:
- `infores_comparison.json` - Detailed comparison showing which sources appear in CI, Dev, or both for each test asset
- `infores_only_in_ci_summary.json` - Summary of sources that appear in CI but not Dev, with counts and affected test assets
- Cached ARS responses for each test asset

## Clean up

Remove generated test results:

```bash
make clean
```

## Examples

Compare infores sources between CI and Dev:
```bash
make infores DEV="dev_refactor_tests_ 2026_01_07_05_00.csv" CI="sprint_6_tests_ 2026_01_04_05_00.csv"
```

Filter to specific infores like CTD:
```bash
make infores DEV="dev_refactor_tests_ 2026_01_07_05_00.csv" CI="sprint_6_tests_ 2026_01_04_05_00.csv" FILTER=infores:ctd
```

Run full analysis:
```bash
make run DEV="dev_refactor_tests_ 2026_01_07_05_00.csv" CI="sprint_6_tests_ 2026_01_04_05_00.csv"
```
