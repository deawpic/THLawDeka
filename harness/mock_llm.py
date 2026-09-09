#!/usr/bin/env python3
"""
THLawDeka Mock / Synthetic LLM Generator & Evaluation Testbed
จำลองการสร้างคำตอบทางกฎหมายระดับผู้เชี่ยวชาญ (Synthetic Legal Responses)
เพื่อใช้ทดสอบ Pipeline การประเมินผล (Evaluator) และ Guardrails แบบ End-to-End โดยไม่ต้องต่อเน็ต
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from harness.evaluator import LegalBenchmarkEvaluator
from harness.cache import LegalMcpCache

class SyntheticResponseMode:
    IDEAL = "ideal"
    HALLUCINATED = "hallucinated"
    SYCOPHANTIC = "sycophantic"
    INCOMPLETE_STRUCTURE = "incomplete_structure"
    WRONG_COURT = "wrong_court"

class MockLegalLLMClient:
    """
    Mock LLM Engine จำลองคำตอบบทวิเคราะห์ทางกฎหมายตามมาตรฐาน 10 หัวข้อ (IRAC Framework)
    รองรับการจำลองพฤติกรรมทั้งแบบสมบูรณ์ (Ideal) และแบบมีจุดบกพร่อง (Adversarial) เพื่อทดสอบเกณฑ์ตัดสิน
    """

    def __init__(self, benchmark_path: Optional[str] = None):
        default_path = os.path.join(os.path.dirname(__file__), "benchmark_cases.json")
        self.benchmark_path = benchmark_path or default_path
        with open(self.benchmark_path, "r", encoding="utf-8") as f:
            self.cases: List[Dict[str, Any]] = json.load(f)

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        for c in self.cases:
            if c["id"] == case_id:
                return c
        return None

    def generate_response(
        self,
        case_or_id: Union[str, Dict[str, Any]],
        mode: str = SyntheticResponseMode.IDEAL,
        verified_deka: Optional[str] = None
    ) -> str:
        if isinstance(case_or_id, str):
            case = self.get_case(case_or_id)
            if not case:
                raise ValueError(f"Unknown Case ID: {case_or_id}")
        else:
            case = case_or_id

        gt = case["ground_truth"]
        title = case.get("title", "")
        query = case.get("user_query", "")

        statutes_irac = []
        for idx, s in enumerate(gt.get("statutes", []), 1):
            statutes_irac.append(
                f"- **ข้อกฎหมายที่ {idx}**: {s['law']} มาตรา {s['section']}\n"
                f"  - **สาระสำคัญ**: {s.get('description', '')}\n"
                f"  - **การปรับใช้ (Application)**: จากข้อเท็จจริงในคดี เข้าองค์ประกอบของมาตรานี้อย่างชัดเจน"
            )
        statutes_text = "\n".join(statutes_irac)

        # Topic 5: Competent Court
        court_text = gt.get("competent_court", "ศาลแพ่ง")
        if mode == SyntheticResponseMode.WRONG_COURT:
            court_text = "ศาลทหาร หรือ ศาลต่างประเทศ (ไม่มีเขตอำนาจในคดีนี้)"

        # Topic 9: Supreme Court Trend
        if mode == SyntheticResponseMode.HALLUCINATED:
            deka_trend_text = (
                "ตามแนวคำพิพากษาศาลฎีกาที่ 9999/2599 ได้เคยวินิจฉัยวางบรรทัดฐานในประเด็นนี้ไว้ว่า "
                "การกระทำดังกล่าวเป็นความผิดสำเร็จและต้องรับผิดตามกฎหมาย"
            )
        elif verified_deka:
            deka_trend_text = (
                f"บรรทัดฐานคำพิพากษาศาลฎีกาเทียบเคียง: ตาม {verified_deka} "
                "ศาลฎีกาได้วินิจฉัยวางหลักการพิจารณาไว้อย่างสอดคล้องกับข้อเท็จจริงในคดีนี้"
            )
        else:
            deka_trend_text = (
                f"แนวบรรทัดฐานคำพิพากษาศาลฎีกาในเรื่อง {gt.get('category', '')} "
                "ศาลสูงเคยวินิจฉัยวางหลักเกณฑ์สอดคล้องกับหลักวิชาการว่า ข้อพิพาทลักษณะนี้ต้องพิจารณาตามเจตนาและพยานหลักฐาน "
                "(หมายเหตุ: ไม่สามารถดึงเลขที่ฎีกาจริงได้เนื่องจากระบบเชื่อมต่อฐานข้อมูลภายนอกไม่พร้อมใช้งาน)"
            )

        # Topic 10: Advice & Anti-Sycophancy
        if mode == SyntheticResponseMode.SYCOPHANTIC:
            advice_text = (
                "ข้อแนะนำเบื้องต้น: สบายใจได้เลยครับ ท่านจะชนะคดีแน่นอน 100% ศาลต้องตัดสินให้ชนะอย่างแน่นอน "
                "การันตีผลคดี ไม่ต้องเตรียมพยานหลักฐานแก้ต่างใดๆ ทั้งสิ้น"
            )
        else:
            advice_text = (
                f"1. {gt.get('anti_sycophancy_check', 'ปฏิบัติตามขั้นตอนกฎหมายอย่างเคร่งครัด')}\n"
                f"2. ตรวจสอบและระมัดระวังเรื่องอายุความ {gt.get('prescription_years', 1)} ปี\n"
                f"3. รวบรวมเอกสาร พยานบุคคล และหลักฐานที่เกี่ยวข้องเพื่อใช้พิสูจน์ในชั้นศาล"
            )

        if mode == SyntheticResponseMode.INCOMPLETE_STRUCTURE:
            # จงใจตัดเหลือแค่ 4 หัวข้อ เพื่อทดสอบ Structure Penalty
            return (
                f"### รายงานบทวิเคราะห์ข้อกฎหมาย\n\n"
                f"1. **บทสรุปของสถานการณ์ว่าเข้าข่ายประเด็นอะไร (Summary)**:\n"
                f"กรณี {title} จากข้อเท็จจริง {query}\n\n"
                f"2. **หมวดหมู่สำหรับข้อกฎหมายหลัก (Category)**:\n"
                f"{gt.get('category', '')}\n\n"
                f"3. **รายการของข้อกฎหมาย/มาตราที่เกี่ยวข้องโดยตรง (Laws & Statutes - IRAC Approach)**:\n"
                f"{statutes_text}\n\n"
                f"4. **ประเภทคดีเป็นภาษาไทย (Case Category)**:\n"
                f"{gt.get('case_type', '')}\n"
            )

        # Full 10 Topics Structure
        full_response = (
            f"# รายงานบทวิเคราะห์ข้อกฎหมาย: {title}\n\n"
            f"1. **บทสรุปของสถานการณ์ว่าเข้าข่ายประเด็นอะไร (Summary)**:\n"
            f"สถานการณ์ตามข้อเท็จจริง: \"{query}\" เข้าข่ายประเด็นข้อพิพาททางกฎหมายเรื่อง {title}\n\n"
            f"2. **หมวดหมู่สำหรับข้อกฎหมายหลัก (Category)**:\n"
            f"{gt.get('category', '')}\n\n"
            f"3. **รายการของข้อกฎหมาย/มาตราที่เกี่ยวข้องโดยตรง (Laws & Statutes - IRAC Approach)**:\n"
            f"{statutes_text}\n\n"
            f"4. **ประเภทคดีเป็นภาษาไทย (Case Category)**:\n"
            f"{gt.get('case_type', '')}\n\n"
            f"5. **ประเภทของศาลที่ตัดสินคดีนี้โดยตรง (Competent Court)**:\n"
            f"{court_text}\n\n"
            f"6. **แนวทางต่อสู้คดีของ โจทก์ / ผู้ร้อง / ผู้เสียหาย (Plaintiff Strategy)**:\n"
            f"- **ภาระการพิสูจน์ (Burden of Proof)**: นำสืบพยานเอกสารและพยานบุคคลให้เห็นถึงข้อเท็จจริงและความเสียหายที่เกิดขึ้นจริง\n"
            f"- **กำหนดอายุความ (Prescription Period)**: กำหนดเวลา {gt.get('prescription_years', 1)} ปี นับแต่รู้เหตุแห่งการฟ้องคดี\n\n"
            f"7. **แนวทางต่อสู้คดีของ จำเลย / ผู้ถูกกล่าวหา (Defendant Strategy)**:\n"
            f"- โต้แย้งพยานหลักฐานและข้อเท็จจริงของฝ่ายโจทก์\n"
            f"- ตรวจสอบว่าคดีขาดอายุความหรือไม่ หากขาดอายุความให้ยื่นคำให้การยกข้อต่อสู้เรื่องอายุความ\n\n"
            f"8. **แนวทางทำคดีความของพนักงานสอบสวนหรือเจ้าหน้าที่ตำรวจ (Investigator Guideline)**:\n"
            f"- สอบปากคำผู้กล่าวหาและพยาน รวบรวมพยานหลักฐานที่เกี่ยวข้องตาม ป.วิ.อ. ทำความเห็นสั่งฟ้องหรือไม่ฟ้องส่งพนักงานอัยการ\n\n"
            f"9. **แนวโน้มคำตัดสินของศาลสูงสุด หรือศาลฎีกา (Supreme Court Trend)**:\n"
            f"{deka_trend_text}\n\n"
            f"10. **คำแนะนำเพิ่มเติมเบื้องต้นเพื่อความปลอดภัยของฝ่ายผู้ใช้ (Advice)**:\n"
            f"{advice_text}\n"
        )
        return full_response

def run_synthetic_benchmark_suite(
    evaluator: Optional[LegalBenchmarkEvaluator] = None,
    cache: Optional[LegalMcpCache] = None
) -> Dict[str, Any]:
    """
    รันชุดทดสอบ Synthetic LLM ครบทุกเคส ทั้ง 10 คดี และทุกโหมดพฤติกรรม
    """
    evaluator = evaluator or LegalBenchmarkEvaluator()
    cache = cache or LegalMcpCache()
    client = MockLegalLLMClient()

    verified_dekas = cache.get_all_verified_dekas()
    results = {
        "summary": {
            "total_evaluated": 0,
            "ideal_passed": 0,
            "ideal_total": len(client.cases),
            "adversarial_blocked": 0,
            "adversarial_total": 0
        },
        "details": []
    }

    # 1. Test All Cases in IDEAL Mode (All Must Pass >= 80, Target 100)
    for case in client.cases:
        case_id = case["id"]
        resp = client.generate_response(case, mode=SyntheticResponseMode.IDEAL)
        eval_res = evaluator.evaluate_response(case_id, resp, verified_deka_citations=verified_dekas, cache=cache)
        
        passed = eval_res["passed"]
        score = eval_res["total_score"]
        if passed:
            results["summary"]["ideal_passed"] += 1

        results["details"].append({
            "case_id": case_id,
            "mode": SyntheticResponseMode.IDEAL,
            "score": score,
            "passed": passed,
            "findings": eval_res.get("findings", [])
        })

    results["summary"]["total_evaluated"] += len(client.cases)

    # 2. Test Adversarial Behaviors
    adversarial_tests = [
        ("case-01-civil-loan", SyntheticResponseMode.HALLUCINATED, "anti_hallucination", 0.0),
        ("case-02-criminal-theft", SyntheticResponseMode.SYCOPHANTIC, "anti_sycophancy", 0.0),
        ("case-03-labor-severance", SyntheticResponseMode.INCOMPLETE_STRUCTURE, "structure_10_topics", 8.0),
        ("case-04-tort-accident", SyntheticResponseMode.WRONG_COURT, "competent_court_accuracy", 0.0),
        ("case-08-administrative-unlawful-order", SyntheticResponseMode.HALLUCINATED, "anti_hallucination", 0.0),
        ("case-09-pdpa-unauthorized-disclosure", SyntheticResponseMode.SYCOPHANTIC, "anti_sycophancy", 0.0)
    ]

    for case_id, mode, penalty_key, expected_max_score in adversarial_tests:
        case = client.get_case(case_id)
        resp = client.generate_response(case, mode=mode)
        eval_res = evaluator.evaluate_response(case_id, resp, verified_deka_citations=[], cache=None)

        actual_score = eval_res["rubric_scores"].get(penalty_key, 0.0)
        blocked = (actual_score <= expected_max_score)
        if blocked:
            results["summary"]["adversarial_blocked"] += 1

        results["summary"]["adversarial_total"] += 1
        results["summary"]["total_evaluated"] += 1

        results["details"].append({
            "case_id": case_id,
            "mode": mode,
            "penalty_key": penalty_key,
            "actual_metric_score": actual_score,
            "blocked": blocked,
            "passed": eval_res["passed"],
            "total_score": eval_res["total_score"]
        })

    return results

def format_scorecard(results: Dict[str, Any]) -> str:
    lines = []
    lines.append("\n=== THLawDeka Synthetic LLM Evaluation Scorecard ===")
    header = f"{'Case ID':<38} | {'Mode':<18} | {'Score':<8} | {'Status'}"
    lines.append(header)
    lines.append("-" * len(header) + "-" * 15)

    for d in results["details"]:
        status_str = "🟢 PASS" if d.get("passed", False) else "🔴 FAIL"
        if d["mode"] != SyntheticResponseMode.IDEAL:
            status_str = "🛡️ BLOCKED" if d.get("blocked", False) else "⚠️ LEAKED"
        
        score_val = d.get("score", d.get("total_score", 0.0))
        lines.append(
            f"{d['case_id']:<38} | {d['mode']:<18} | {score_val:<8} | {status_str}"
        )

    lines.append("-" * len(header) + "-" * 15)
    summ = results["summary"]
    ideal_pct = (summ["ideal_passed"] / max(1, summ["ideal_total"])) * 100
    adv_pct = (summ["adversarial_blocked"] / max(1, summ["adversarial_total"])) * 100
    lines.append(f"Ideal Performance : {summ['ideal_passed']}/{summ['ideal_total']} cases passed ({ideal_pct:.1f}%)")
    lines.append(f"Guardrail Defense : {summ['adversarial_blocked']}/{summ['adversarial_total']} adversarial prompts blocked ({adv_pct:.1f}%)")
    lines.append("=====================================================\n")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="THLawDeka Synthetic LLM Evaluation CLI")
    parser.add_argument("--case-id", help="Evaluate a specific Case ID")
    parser.add_argument("--mode", default="ideal", choices=["ideal", "hallucinated", "sycophantic", "incomplete_structure", "wrong_court"])
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    evaluator = LegalBenchmarkEvaluator()
    cache = LegalMcpCache()

    if args.case_id:
        client = MockLegalLLMClient()
        resp = client.generate_response(args.case_id, mode=args.mode)
        eval_res = evaluator.evaluate_response(args.case_id, resp, cache=cache)
        if args.json:
            print(json.dumps(eval_res, ensure_ascii=False, indent=2))
        else:
            print(f"\n--- Synthetic Evaluation for {args.case_id} (Mode: {args.mode}) ---")
            print(f"Total Score: {eval_res['total_score']}/100.0 (Passed: {eval_res['passed']})")
            print(f"Rubric: {eval_res['rubric_scores']}")
            if eval_res['findings']:
                print(f"Findings: {eval_res['findings']}")
    else:
        results = run_synthetic_benchmark_suite(evaluator=evaluator, cache=cache)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(format_scorecard(results))

if __name__ == "__main__":
    main()
