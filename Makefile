# Weekly FPL brief.
#
#   make brief      fetch → gate → digest → print brief.md   (local use)
#   make ci-brief   fetch → gate → digest, prints nothing   (what Actions runs)
#
# The pipeline is defined once, in ci-brief. `brief` adds the print, which is
# fine on your own terminal and never allowed in CI (public logs).
#
# ci-brief writes the gate's JSON to data/gate.json (gitignored). When the
# gate is closed it stops there, exit 0, and brief.md is left untouched;
# callers check `"proceed": true` in data/gate.json to know whether a fresh
# brief.md was written.

PY ?= python3
GATE_JSON = data/gate.json

.PHONY: brief ci-brief fetch fetch-force gate digest routine check-routine test clean

brief: ci-brief
	@if grep -q '"proceed": true' $(GATE_JSON); then cat brief.md; fi

ci-brief: fetch
	@mkdir -p data
	@if $(PY) -m scripts.gate > $(GATE_JSON); then \
		$(PY) -m scripts.digest; \
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
