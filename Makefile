.PHONY: all test stats health audit seed clean init-cache pdf-check

all:
	./scripts/run_harness.sh

init-cache:
	python3 harness/cache.py --ensure-init

pdf-check:
	python3 harness/document.py --check-env

test:
	python3 -m unittest discover -s tests -p "test_*.py" -v

stats:
	python3 harness/cache.py --stats

health:
	python3 harness/cache.py --health

seed:
	python3 harness/evaluator.py --seed-cache

audit: seed
	python3 harness/evaluator.py --audit-outputs

clean:
	python3 harness/cache.py --prune
