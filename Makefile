# Weekly FPL brief. `make brief` fetches, gates, writes and prints brief.md.
# Printing is for local use only: the CI job never prints the digest.

PY ?= python3

.PHONY: brief fetch fetch-force gate digest routine test check-routine clean

brief: fetch
	@if $(PY) -m scripts.gate; then \
		$(PY) -m scripts.digest && cat brief.md; \
	else \
		echo "brief: gate closed, nothing to do." >&2; \
	fi

fetch:
	$(PY) -m scripts.fetch

fetch-force:
	$(PY) -m scripts.fetch --force

gate:
	$(PY) -m scripts.gate

digest:
	$(PY) -m scripts.digest

routine:
	$(PY) -m scripts.build_routine

check-routine:
	$(PY) -m scripts.build_routine --check

test:
	$(PY) -m pytest -q

clean:
	rm -f data/*.json brief.md
