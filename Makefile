.PHONY: run infores trapi install clean help

help:
	@echo "Available targets:"
	@echo "  make run DEV=<path> CI=<path>              - Run full diff analysis"
	@echo "  make infores DEV=<path> CI=<path>          - Run infores comparison"
	@echo "  make infores DEV=<path> CI=<path> FILTER=<infores> - Filter to specific infores"
	@echo "  make trapi DEV=<path> CI=<path>            - Export TRAPI responses for CI pass/Dev fail"
	@echo "  make install                               - Install dependencies"
	@echo "  make clean                                 - Clean test_diffs directory"

install:
	uv sync

run:
	@if [ -z "$(DEV)" ] || [ -z "$(CI)" ]; then \
		echo "Error: DEV and CI paths must be specified"; \
		echo "Usage: make run DEV=path/to/dev.csv CI=path/to/ci.csv"; \
		exit 1; \
	fi
	uv run qa-diff "$(DEV)" "$(CI)"

infores:
	@if [ -z "$(DEV)" ] || [ -z "$(CI)" ]; then \
		echo "Error: DEV and CI paths must be specified"; \
		echo "Usage: make infores DEV=path/to/dev.csv CI=path/to/ci.csv [FILTER=infores:source]"; \
		exit 1; \
	fi
	@if [ -n "$(FILTER)" ]; then \
		uv run qa-diff "$(DEV)" "$(CI)" --mode infores --infores-filter "$(FILTER)"; \
	else \
		uv run qa-diff "$(DEV)" "$(CI)" --mode infores; \
	fi

trapi:
	@if [ -z "$(DEV)" ] || [ -z "$(CI)" ]; then \
		echo "Error: DEV and CI paths must be specified"; \
		echo "Usage: make trapi DEV=path/to/dev.csv CI=path/to/ci.csv"; \
		exit 1; \
	fi
	uv run qa-diff "$(DEV)" "$(CI)" --mode trapi-export

clean:
	rm -rf test_diffs
