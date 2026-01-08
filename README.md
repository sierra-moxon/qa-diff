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

### Using Make

```bash
make run DEV=path/to/dev.csv CI=path/to/ci.csv
```

### Using the CLI directly

```bash
uv run qa-diff path/to/dev.csv path/to/ci.csv
```

### After installation

```bash
qa-diff path/to/dev.csv path/to/ci.csv
```

## What it does

This tool:
- Compares test results between two environments (typically Dev and CI)
- Identifies tests that pass in CI but fail in Dev
- Analyzes data source disparities
- Generates detailed JSON reports in the `test_diffs/` directory

## Output

Results are written to `test_diffs/`:
- `diff_test_results.json` - Summary of differing tests
- `missing_sources.json` - List of missing data sources
- `missing_source_counts.json` - Count of each missing source
- Individual test result files for detailed analysis

## Clean up

Remove generated test results:

```bash
make clean
```
