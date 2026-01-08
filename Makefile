.PHONY: run install clean help

help:
	@echo "Available targets:"
	@echo "  make run DEV=<path> CI=<path>  - Run the diff test results script"
	@echo "  make install                   - Install dependencies"
	@echo "  make clean                     - Clean test_diffs directory"

install:
	uv sync

run:
	@if [ -z "$(DEV)" ] || [ -z "$(CI)" ]; then \
		echo "Error: DEV and CI paths must be specified"; \
		echo "Usage: make run DEV=path/to/dev.csv CI=path/to/ci.csv"; \
		exit 1; \
	fi
	uv run qa-diff "$(DEV)" "$(CI)"

clean:
	rm -rf test_diffs
