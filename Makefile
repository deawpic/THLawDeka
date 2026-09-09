.PHONY: all test stats health audit seed clean init-cache ping-mcp synthetic-test

all:
	./scripts/run_harness.sh

init-cache:
	python3 harness/cache.py --ensure-init

test:
	python3 -m unittest discover -s tests -p "test_*.py" -v

stats:
	python3 harness/cache.py --stats

health:
	python3 harness/cache.py --health

ping-mcp:
	python3 scripts/ping_mcp.py

synthetic-test:
	python3 harness/mock_llm.py

seed:
	python3 harness/evaluator.py --seed-cache

audit: seed
	python3 harness/evaluator.py --audit-outputs

clean:
	python3 harness/cache.py --prune

