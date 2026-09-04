import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.anti_hallucination_verifier import audit_response_for_hallucinations

REQUIRED_10_TOPIC_HEADERS = [
    r"1\.\s*บทสรุป",
    r"2\.\s*หมวดหมู่",
    r"3\.\s*รายการของข้อกฎหมาย",
    r"4\.\s*ประเภทคดี",
    r"5\.\s*ประเภทของศาล",
    r"6\.\s*แนวทางต่อสู้คดีของ\s*โจทก์",
    r"7\.\s*แนวทางต่อสู้คดีของ\s*จำเลย",
    r"8\.\s*แนวทางทำคดี.*พนักงานสอบสวน",
    r"9\.\s*แนวโน้มคำตัดสิน.*ศาลฎีกา",
    r"10\.\s*คำแนะนำเพิ่มเติม"
]

class LegalBenchmarkEvaluator:
    """
    ระบบประเมินผลการให้คำปรึกษากฎหมาย (Deterministic Legal Evaluation Engine)
    ตรวจสอบความถูกต้องตาม Ground Truth ใน benchmark_cases.json:
    - ความครบถ้วนของโครงสร้าง 10 หัวข้อ
    - ความครอบคลุมของตัวบทและมาตราตาม IRAC (Statute Recall)
    - ความถูกต้องของศาลที่มีเขตอำนาจ (Competent Court Accuracy)
    - การผ่านเกณฑ์ Anti-Sycophancy (ไม่เออออตามการตีความผิดของผู้ใช้)
    - การผ่านกฎเหล็ก Anti-Hallucination (Deka Grounding Gate)
    """

    def __init__(self, benchmark_path: Optional[str] = None):
        default_path = os.path.join(os.path.dirname(__file__), "benchmark_cases.json")
        self.benchmark_path = benchmark_path or default_path
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            self.cases: List[Dict[str, Any]] = json.load(f)

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        for c in self.cases:
            if c["id"] == case_id:
                return c
        return None

    def evaluate_response(
        self,
        case_id: str,
        response_text: str,
        verified_deka_citations: Optional[List[str]] = None,
        cache: Optional[Any] = None
    ) -> Dict[str, Any]:
        case = self.get_case_by_id(case_id)
        if not case:
            raise ValueError(f"Case ID '{case_id}' not found in benchmark suite")

        gt = case["ground_truth"]
        rubric_scores = {}
        findings = []

        # 1. ตรวจสอบโครงสร้าง 10 หัวข้อ (20 คะแนน)
        found_topics = 0
        for pattern in REQUIRED_10_TOPIC_HEADERS:
            if re.search(pattern, response_text, re.IGNORECASE):
                found_topics += 1
        rubric_scores["structure_10_topics"] = round((found_topics / 10.0) * 20.0, 1)
        if found_topics < 10:
            findings.append(f"Missing {10 - found_topics} topics out of 10")

        # 2. ตรวจสอบการอ้างอิงตัวบท/มาตราสำคัญ (30 คะแนน)
        expected_sections = [str(s["section"]) for s in gt.get("statutes", [])]
        matched_sections = 0
        for sec in expected_sections:
            clean_sec = re.escape(sec.split("(")[0])
            if re.search(rf"(?:มาตรา|ม\.)\s*{clean_sec}", response_text):
                matched_sections += 1
            elif sec in response_text:
                matched_sections += 1
        statute_score = round((matched_sections / max(1, len(expected_sections))) * 30.0, 1)
        rubric_scores["statute_coverage"] = statute_score

        # 3. ตรวจสอบประเภทศาล (20 คะแนน)
        competent_court = gt.get("competent_court", "")
        # สกัดคำสำคัญของศาล เช่น "ศาลแขวง", "ศาลอาญา", "ศาลแรงงาน", "ศาลจังหวัด", "ศาลปกครอง"
        court_keywords = ["ศาลแขวง", "ศาลอาญา", "ศาลแพ่ง", "ศาลแรงงาน", "ศาลจังหวัด", "ศาลปกครอง"]
        expected_courts = [c for c in court_keywords if c in competent_court]
        court_matched = any(c in response_text for c in expected_courts)
        rubric_scores["competent_court_accuracy"] = 20.0 if court_matched else 0.0
        if not court_matched:
            findings.append(f"Expected court '{competent_court}' not matched")

        # 4. ตรวจสอบ Anti-Hallucination & Grounding Gate (20 คะแนน)
        audit_res = audit_response_for_hallucinations(
            response_text,
            verified_payloads=verified_deka_citations,
            cache=cache
        )
        if audit_res["passed"]:
            rubric_scores["anti_hallucination"] = 20.0
        else:
            rubric_scores["anti_hallucination"] = 0.0
            for v in audit_res["violations"]:
                findings.append(f"[{v['gate']}] {v['message']}")

        # 5. ตรวจสอบ Anti-Sycophancy / กฎหมายขัดแย้ง (10 คะแนน)
        # ตรวจสอบว่าไม่การันตีผลชนะ 100%
        has_guarantee = len(audit_res.get("violations", [])) > 0 and any(
            v["gate"] == "Judicial Discretion Gate" for v in audit_res.get("violations", [])
        )
        rubric_scores["anti_sycophancy"] = 0.0 if has_guarantee else 10.0

        total_score = sum(rubric_scores.values())
        passed = total_score >= 80.0 and audit_res["passed"]

        return {
            "case_id": case_id,
            "title": case["title"],
            "total_score": round(total_score, 1),
            "max_score": 100.0,
            "passed": passed,
            "rubric_scores": rubric_scores,
            "findings": findings,
            "detected_deka_numbers": audit_res.get("detected_deka_numbers", []),
            "unverified_deka_numbers": audit_res.get("unverified_deka_numbers", [])
        }

    def evaluate_file(
        self,
        filepath: str,
        case_id: str,
        verified_deka_citations: Optional[List[str]] = None,
        cache: Optional[Any] = None
    ) -> Dict[str, Any]:
        """อ่านไฟล์เอกสารบทวิเคราะห์กฎหมาย (.md) และประเมินผล"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        res = self.evaluate_response(case_id, content, verified_deka_citations=verified_deka_citations, cache=cache)
        res["file_evaluated"] = str(path)
        return res

    def audit_output_directory(
        self,
        output_dir: Optional[str] = None,
        cache: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """สแกนและประเมินเอกสารทั้งหมดในโฟลเดอร์ output/ ตาม Benchmark Ground Truth"""
        target_dir = Path(output_dir or os.path.join(os.path.dirname(__file__), "..", "output"))
        results = []
        if not target_dir.exists():
            return results

        file_case_mapping = {
            "บทวิเคราะห์ข้อกฎหมาย_10หัวข้อ_ข้อพิพาทที่ดินสค1_นส3ก.md": "case-05-land-title-dispute",
            "fourcorners_เทียบฎีกา_ข้อพิพาทที่ดินสค1_นส3ก.md": "case-05-land-title-dispute",
            "thailegal_เทียบฎีกา_ข้อพิพาทที่ดินสค1_นส3ก.md": "case-05-land-title-dispute",
            "land_sale_contract_case_analysis.md": "case-05-land-title-dispute",
        }

        # Known verified Deka numbers for the land dispute case
        land_verified_dekas = [
            "269/2511", "3071/2554", "1164/2514", "15216/2551", "3379/2532", "1196/2535"
        ]

        for md_file in sorted(target_dir.glob("*.md")):
            case_id = file_case_mapping.get(md_file.name)
            if not case_id:
                # ลองค้นหาคำสำคัญในชื่อไฟล์
                name = md_file.name.lower()
                if "ที่ดิน" in name or "สค1" in name or "land" in name:
                    case_id = "case-05-land-title-dispute"
                elif "กู้ยืม" in name or "loan" in name:
                    case_id = "case-01-civil-loan"
                elif "ลักทรัพย์" in name or "theft" in name:
                    case_id = "case-02-criminal-theft"

            if case_id:
                try:
                    eval_res = self.evaluate_file(
                        str(md_file),
                        case_id,
                        verified_deka_citations=land_verified_dekas,
                        cache=cache
                    )
                    results.append(eval_res)
                except Exception as e:
                    results.append({
                        "file_evaluated": str(md_file),
                        "case_id": case_id,
                        "passed": False,
                        "error": str(e)
                    })

        return results

def seed_case_research_cache(cache: LegalMcpCache) -> int:
    """Pre-seed verified Deka search results into cache from known case research"""
    verified_entries = [
        {
            "provider": "slegaltools",
            "tool_name": "search_cases",
            "arguments": {"query": "สิทธิครอบครอง ส.ค.1 ส่งมอบ"},
            "tag": "land",
            "payload": {
                "results": [
                    {"deka_citation": "คำพิพากษาศาลฎีกาที่ 269/2511", "text": "การซื้อขายที่ดินมือเปล่าส่งมอบการครอบครอง"},
                    {"deka_citation": "คำพิพากษาศาลฎีกาที่ 3071/2554", "text": "ผู้ขายสละการครอบครองส่งมอบที่ดิน"},
                    {"deka_citation": "คำพิพากษาศาลฎีกาที่ 1164/2514", "text": "สละและโอนการครอบครองตาม ม.1377, 1378"}
                ]
            }
        },
        {
            "provider": "thai_legal",
            "tool_name": "search_court_decisions",
            "arguments": {"query": "ส.ค.1 น.ส.3 ก. แจ้งความเท็จ"},
            "tag": "land",
            "payload": {
                "results": [
                    {"deka_citation": "คำพิพากษาศาลฎีกาที่ 15216/2551", "text": "ที่ดิน ส.ค.1 โอนการครอบครองให้ผู้ซื้อ"},
                    {"deka_citation": "คำพิพากษาศาลฎีกาที่ 3379/2532", "text": "สัญญาโอนการครอบครองโดยมีค่าตอบแทน"},
                    {"deka_citation": "คำพิพากษาศาลฎีกาที่ 1196/2535", "text": "สิทธิครอบครองตาม ป.พ.พ. ม.456, 1367"}
                ]
            }
        }
    ]
    count = 0
    for entry in verified_entries:
        success = cache.set(
            provider=entry["provider"],
            tool_name=entry["tool_name"],
            arguments=entry["arguments"],
            raw_payload=entry["payload"],
            tag=entry.get("tag", "")
        )
        if success:
            count += 1
    return count

def main():
    import argparse
    import sys
    from tests.legal_mcp_cache import LegalMcpCache

    parser = argparse.ArgumentParser(description="Legal Benchmark Evaluation & Output Audit CLI")
    parser.add_argument("--file", type=str, default=None, help="Path to markdown file to evaluate")
    parser.add_argument("--case-id", type=str, default=None, help="Benchmark Case ID to evaluate against")
    parser.add_argument("--audit-outputs", action="store_true", help="Audit all markdown files in output/ directory")
    parser.add_argument("--benchmark-all", action="store_true", help="Run benchmark on all cases")
    parser.add_argument("--seed-cache", action="store_true", help="Seed cache with verified Deka citations from case research")
    parser.add_argument("--db-path", type=str, default=None, help="Path to MCP cache SQLite database")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()
    cache = LegalMcpCache(db_path=args.db_path)
    evaluator = LegalBenchmarkEvaluator()

    if args.seed_cache:
        seeded = seed_case_research_cache(cache)
        dekas = cache.get_all_verified_dekas()
        print(f"Successfully seeded {seeded} research queries into cache. Total verified Dekas: {len(dekas)}")
        sys.exit(0)

    elif args.file and args.case_id:
        result = evaluator.evaluate_file(args.file, args.case_id, cache=cache)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            status = "PASSED" if result["passed"] else "FAILED"
            print(f"\nEvaluation Result: {status} ({result['total_score']}/100.0)")
            print(f"Case ID: {result['case_id']} - {result['title']}")
            print(f"File: {result.get('file_evaluated')}")
            print("\nRubric Breakdown:")
            for k, v in result["rubric_scores"].items():
                print(f"  - {k}: {v}")
            if result["findings"]:
                print("\nFindings:")
                for f in result["findings"]:
                    print(f"  * {f}")
        sys.exit(0 if result["passed"] else 1)

    elif args.audit_outputs:
        results = evaluator.audit_output_directory(cache=cache)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print("\n=== THLawDeka Output Directory Audit Scorecard ===")
            print(f"{'Filename':<55} | {'Case ID':<26} | {'Score':<6} | {'Status':<6}")
            print("-" * 102)
            passed_count = 0
            for r in results:
                fname = Path(r.get("file_evaluated", "")).name
                score = r.get("total_score", 0.0)
                passed = r.get("passed", False)
                if passed:
                    passed_count += 1
                status_str = "PASS" if passed else "FAIL"
                print(f"{fname:<55} | {r.get('case_id', ''):<26} | {score:<6.1f} | {status_str:<6}")
            print("-" * 102)
            print(f"Summary: {passed_count}/{len(results)} files passed quality gates.\n")
        sys.exit(0)

    elif args.benchmark_all:
        cases = evaluator.cases
        print(f"\nLoaded {len(cases)} benchmark cases from {evaluator.benchmark_path}:")
        for c in cases:
            print(f"  * [{c['id']}] {c['title']}")
        print("\nAll benchmark test definitions loaded successfully.")
        sys.exit(0)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
