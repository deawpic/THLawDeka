#!/usr/bin/env bash
set -e

# ==============================================================================
# THLawDeka AI Agent Harness v3.0 - Unified Runner
# ==============================================================================

# Robust project root discovery regardless of where this script is called from
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================================================"
echo "⚡ THLawDeka Agent Harness v3.0: Full Verification Pipeline"
echo "======================================================================"

echo ""
echo "▶ 1. Running Unit & Integration Test Suite (45 Tests)..."
python3 -m unittest discover -s tests -p "test_*.py" -v

echo ""
echo "▶ 2. Checking Legal MCP Cache Health & FinOps Telemetry..."
python3 harness/cache.py --health
python3 harness/cache.py --stats

echo ""
echo "▶ 3. Seeding Verified Research Dekas into Cache..."
python3 harness/evaluator.py --seed-cache

echo ""
echo "▶ 4. Auditing Output Artifacts against Legal Benchmarks..."
python3 harness/evaluator.py --audit-outputs

echo ""
echo "======================================================================"
echo "✅ All Harness v3.0 Quality Gates & Verification Passed Successfully!"
echo "======================================================================"
