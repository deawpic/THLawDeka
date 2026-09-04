.PHONY: all test stats health audit seed clean

all: test stats audit

test:
	python3 -m unittest discover -s tests -p "test_*.py" -v

stats:
	python3 legal_mcp_cache.py --stats

health:
	python3 legal_mcp_cache.py --health

seed:
	python3 tests/eval_benchmark_runner.py --seed-cache

audit: seed
	python3 tests/eval_benchmark_runner.py --audit-outputs

clean:
	python3 legal_mcp_cache.py --prune
