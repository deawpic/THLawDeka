import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from harness.verifier import audit_response_for_hallucinations, validate_mermaid_syntax

REQUIRED_10_TOPIC_HEADERS = [
    r"1\.\s*บทสรุป",
    r"2\.\s*หมวดหมู่",
    r"3\.\s*รายการของข้อกฎหมาย",
    r"4\.\s*ประเภทคดี",
    r"5\.\s*ประเภทของศาล",
    r"6\.\s*แนวทางต่อสู้คดีของ(?:\s*ฝ่าย)?\s*โจทก์",
    r"7\.\s*แนวทางต่อสู้คดีของ(?:\s*ฝ่าย)?\s*จำเลย",
    r"8\.\s*แนวทางทำคดี.*พนักงานสอบสวน",
    r"9\.\s*แนวโน้มคำตัดสิน.*ศาลฎีกา",
    r"10\.\s*คำแนะนำเพิ่มเติม"
]

class ArtifactType:
    FULL_10_TOPICS = "FULL_10_TOPICS"
    COMPREHENSIVE_ANALYSIS = "COMPREHENSIVE_ANALYSIS"
    DEKA_RESEARCH = "DEKA_RESEARCH"
    CONTRACT_OPINION = "CONTRACT_OPINION"
    SYSTEM_DOC = "SYSTEM_DOC"

def classify_artifact(filepath_or_name: str, content: str = "") -> Tuple[str, Optional[str]]:
    """
    วิเคราะห์และแยกประเภทไฟล์ Artifact พร้อมจับคู่ Benchmark Case ID:
    - FULL_10_TOPICS: รายงานบทวิเคราะห์กฎหมาย 10 หัวข้อฉบับมาตรฐาน
    - COMPREHENSIVE_ANALYSIS: รายงานบทวิเคราะห์กฎหมายเชิงลึก (Uncut Legal Intelligence Report)
    - DEKA_RESEARCH: รายงานเปรียบเทียบผลการค้นคว้าและบรรทัดฐานศาลฎีกา (MCP Precedent Research)
    - CONTRACT_OPINION: บทวิเคราะห์สัญญาและนิติกรรมเฉพาะทาง
    - SYSTEM_DOC: เอกสารสถาปัตยกรรมระบบ ข้อกำหนดทางเทคนิค หรือแม่แบบคำสั่ง
    """
    fname = Path(filepath_or_name).name.lower()

    # 1. System Documentation
    if any(k in fname for k in ["spec", "features", "master_prompt", "config", "readme"]):
        return ArtifactType.SYSTEM_DOC, None

    # 2. Deka Research / Precedent Comparison
    if any(k in fname for k in ["fourcorners", "thailegal", "slegaltools", "เทียบฎีกา", "แนวโน้มคำตัดสิน"]):
        case_id = "case-05-land-title-dispute" if any(k in fname for k in ["ที่ดิน", "สค1", "นส3", "land"]) else None
        return ArtifactType.DEKA_RESEARCH, case_id

    # 3. Contract Case Analysis
    if any(k in fname for k in ["contract", "สัญญาซื้อขาย", "สัญญาจะซื้อ"]):
        case_id = "case-05-land-title-dispute" if any(k in fname for k in ["ที่ดิน", "land"]) else None
        return ArtifactType.CONTRACT_OPINION, case_id

    # 4. Full 10 Topics Report
    has_10_in_name = "10หัวข้อ" in fname
    has_10_topics_content = bool(content and sum(1 for p in REQUIRED_10_TOPIC_HEADERS if re.search(p, content, re.IGNORECASE)) >= 8)
    if has_10_in_name or has_10_topics_content:
        case_id = None
        if "พรากผู้เยาว์" in fname or "319" in fname:
            case_id = "case-07-statutory-rape-minor"
        elif any(k in fname for k in ["ที่ดิน", "สค1", "land"]):
            case_id = "case-05-land-title-dispute"
        elif any(k in fname for k in ["กู้ยืม", "loan"]):
            case_id = "case-01-civil-loan"
        elif any(k in fname for k in ["ลักทรัพย์", "theft"]):
            case_id = "case-02-criminal-theft"
        elif any(k in fname for k in ["เลิกจ้าง", "ค่าชดเชย", "แรงงาน"]):
            case_id = "case-03-labor-severance"
        elif any(k in fname for k in ["ชนท้าย", "ละเมิด"]):
            case_id = "case-04-tort-accident"
        elif any(k in fname for k in ["สมรส", "บุตร"]):
            case_id = "case-06-family-bigamy-child-status"
        return ArtifactType.FULL_10_TOPICS, case_id

    # 5. Comprehensive Analysis
    if fname.startswith("บทวิเคราะห์ข้อกฎหมาย_"):
        case_id = None
        if any(k in fname for k in ["สมรสซ้อน", "สถานะบุตร"]):
            case_id = "case-06-family-bigamy-child-status"
        elif any(k in fname for k in ["ที่ดิน", "สค1", "land"]):
            case_id = "case-05-land-title-dispute"
        elif any(k in fname for k in ["พรากผู้เยาว์", "319"]):
            case_id = "case-07-statutory-rape-minor"
        return ArtifactType.COMPREHENSIVE_ANALYSIS, case_id

    return ArtifactType.COMPREHENSIVE_ANALYSIS, None

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
            "artifact_type": ArtifactType.FULL_10_TOPICS,
            "case_id": case_id,
            "title": case["title"],
            "total_score": round(total_score, 1),
            "max_score": 100.0,
            "passed": passed,
            "rubric_scores": rubric_scores,
            "findings": findings,
            "detected_deka_numbers": audit_res.get("detected_deka_numbers", []),
            "unverified_deka_numbers": audit_res.get("unverified_deka_numbers", []),
            "mermaid_audit": audit_res.get("mermaid_audit", {})
        }

    def evaluate_comprehensive_analysis(
        self,
        case_id: Optional[str],
        response_text: str,
        verified_deka_citations: Optional[List[str]] = None,
        cache: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        ประเมินผลรายงานบทวิเคราะห์กฎหมายเชิงลึก (Comprehensive Legal Intelligence Report)
        Rubric (100 คะแนน):
        1. การวิเคราะห์ตัวบทกฎหมายและมาตราสำคัญตาม IRAC (35 คะแนน)
        2. ความลึกซึ้งของการให้เหตุผลทางกฎหมายและโครงสร้าง (25 คะแนน)
        3. ความถูกต้องของศาลที่มีเขตอำนาจหรือขั้นตอนกระบวนการ (15 คะแนน)
        4. Anti-Hallucination & Deka Grounding Gate (15 คะแนน)
        5. Anti-Sycophancy & Judicial Discretion Gate (10 คะแนน)
        """
        findings = []
        rubric_scores = {}
        case = self.get_case_by_id(case_id) if case_id else None
        title = case["title"] if case else "Comprehensive Legal Analysis"

        # 1. การวิเคราะห์ตัวบทกฎหมายและมาตราสำคัญ (35 คะแนน)
        if case:
            gt = case["ground_truth"]
            expected_sections = [str(s["section"]) for s in gt.get("statutes", [])]
            matched = 0
            for sec in expected_sections:
                clean_sec = re.escape(sec.split("(")[0])
                if re.search(rf"(?:มาตรา|ม\.)\s*{clean_sec}", response_text) or sec in response_text:
                    matched += 1
            if len(expected_sections) > 0 and (matched / len(expected_sections)) >= 0.5:
                statute_score = 35.0
            else:
                statute_score = round((matched / max(1, len(expected_sections))) * 35.0, 1)
        else:
            has_statutes = len(re.findall(r"(?:มาตรา|ม\.)\s*\d+", response_text)) >= 3
            statute_score = 35.0 if has_statutes else 20.0
        rubric_scores["statute_analysis"] = statute_score

        # 2. ความลึกซึ้งของการให้เหตุผลทางกฎหมายและโครงสร้าง (25 คะแนน)
        has_structure = len(re.findall(r"^#{1,3}\s+", response_text, re.MULTILINE)) >= 3
        has_keywords = any(k in response_text for k in ["ข้อเท็จจริง", "ประเด็น", "การปรับใช้", "วินิจฉัย", "สรุป"])
        rubric_scores["legal_reasoning_depth"] = 25.0 if (has_structure and has_keywords) else 15.0

        # 3. ความถูกต้องของศาลหรือกระบวนพิจารณา (15 คะแนน)
        court_keywords = ["ศาลแขวง", "ศาลอาญา", "ศาลแพ่ง", "ศาลแรงงาน", "ศาลจังหวัด", "ศาลปกครอง", "ศาลเยาวชนและครอบครัว", "พนักงานสอบสวน"]
        court_matched = any(c in response_text for c in court_keywords)
        rubric_scores["competent_court_or_procedure"] = 15.0 if court_matched else 0.0

        # 4. Anti-Hallucination Gate (15 คะแนน)
        audit_res = audit_response_for_hallucinations(
            response_text,
            verified_payloads=verified_deka_citations,
            cache=cache
        )
        rubric_scores["anti_hallucination"] = 15.0 if audit_res["passed"] else 0.0
        if not audit_res["passed"]:
            for v in audit_res["violations"]:
                findings.append(f"[{v['gate']}] {v['message']}")

        # 5. Anti-Sycophancy Gate (10 คะแนน)
        has_guarantee = any(v["gate"] == "Judicial Discretion Gate" for v in audit_res.get("violations", []))
        rubric_scores["anti_sycophancy"] = 0.0 if has_guarantee else 10.0

        total_score = sum(rubric_scores.values())
        passed = total_score >= 80.0 and audit_res["passed"]

        return {
            "artifact_type": ArtifactType.COMPREHENSIVE_ANALYSIS,
            "case_id": case_id,
            "title": title,
            "total_score": round(total_score, 1),
            "max_score": 100.0,
            "passed": passed,
            "rubric_scores": rubric_scores,
            "findings": findings,
            "detected_deka_numbers": audit_res.get("detected_deka_numbers", []),
            "unverified_deka_numbers": audit_res.get("unverified_deka_numbers", []),
            "mermaid_audit": audit_res.get("mermaid_audit", {})
        }

    def evaluate_deka_research(
        self,
        case_id: Optional[str],
        response_text: str,
        verified_deka_citations: Optional[List[str]] = None,
        cache: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        ประเมินผลรายงานเปรียบเทียบผลการค้นคว้าและบรรทัดฐานศาลฎีกา (Deka Research Report)
        Rubric (100 คะแนน):
        1. Deka Grounding & Citations Accuracy (40 คะแนน)
        2. Precedent Comparative Depth & Facts (30 คะแนน)
        3. Statute & Principle Alignment (20 คะแนน)
        4. Anti-Sycophancy & Judicial Discretion (10 คะแนน)
        """
        findings = []
        rubric_scores = {}
        case = self.get_case_by_id(case_id) if case_id else None
        title = case["title"] if case else "Deka Research & Comparative Analysis"

        audit_res = audit_response_for_hallucinations(
            response_text,
            verified_payloads=verified_deka_citations,
            cache=cache
        )

        # 1. Deka Grounding (40 คะแนน)
        rubric_scores["deka_grounding"] = 40.0 if len(audit_res.get("unverified_deka_numbers", [])) == 0 else 0.0
        if rubric_scores["deka_grounding"] == 0:
            findings.append(f"Unverified Dekas: {audit_res.get('unverified_deka_numbers')}")

        # 2. Precedent Comparative Depth (30 คะแนน)
        deka_count = len(audit_res.get("detected_deka_numbers", []))
        has_analysis = any(k in response_text for k in ["วินิจฉัย", "ข้อเท็จจริง", "เทียบเคียง", "หลักกฎหมาย", "บรรทัดฐาน"])
        if deka_count >= 1 and has_analysis:
            rubric_scores["precedent_comparative_depth"] = 30.0
        elif has_analysis:
            rubric_scores["precedent_comparative_depth"] = 20.0
        else:
            rubric_scores["precedent_comparative_depth"] = 10.0

        # 3. Statute Alignment (20 คะแนน)
        has_statutes = len(audit_res.get("detected_statutes", [])) > 0 or len(re.findall(r"(?:มาตรา|ม\.)\s*\d+", response_text)) > 0
        rubric_scores["statute_alignment"] = 20.0 if has_statutes else 10.0

        # 4. Anti-Sycophancy (10 คะแนน)
        has_guarantee = any(v["gate"] == "Judicial Discretion Gate" for v in audit_res.get("violations", []))
        rubric_scores["anti_sycophancy"] = 0.0 if has_guarantee else 10.0

        total_score = sum(rubric_scores.values())
        passed = total_score >= 80.0 and audit_res["passed"]

        return {
            "artifact_type": ArtifactType.DEKA_RESEARCH,
            "case_id": case_id,
            "title": title,
            "total_score": round(total_score, 1),
            "max_score": 100.0,
            "passed": passed,
            "rubric_scores": rubric_scores,
            "findings": findings,
            "detected_deka_numbers": audit_res.get("detected_deka_numbers", []),
            "unverified_deka_numbers": audit_res.get("unverified_deka_numbers", []),
            "mermaid_audit": audit_res.get("mermaid_audit", {})
        }

    def evaluate_contract_opinion(
        self,
        case_id: Optional[str],
        response_text: str,
        verified_deka_citations: Optional[List[str]] = None,
        cache: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        ประเมินผลบทวิเคราะห์สัญญาและนิติกรรม (Contract Case Analysis)
        Rubric (100 คะแนน):
        1. ความสมบูรณ์ของสัญญาและข้อกฎหมาย (35 คะแนน)
        2. การวิเคราะห์การผิดสัญญาและการเยียวยา (25 คะแนน)
        3. Anti-Hallucination Gate (20 คะแนน)
        4. คำแนะนำเชิงปฏิบัติและกลยุทธ์ระงับข้อพิพาท (20 คะแนน)
        """
        findings = []
        rubric_scores = {}
        case = self.get_case_by_id(case_id) if case_id else None
        title = case["title"] if case else "Contract Legal Opinion"

        audit_res = audit_response_for_hallucinations(
            response_text,
            verified_payloads=verified_deka_citations,
            cache=cache
        )

        # 1. Contract Validity & Statute (35 คะแนน)
        has_contract_statutes = any(s in response_text for s in ["456", "149", "150", "369", "386", "377", "378", "สัญญา", "นิติกรรม"])
        rubric_scores["contract_validity_and_statute"] = 35.0 if has_contract_statutes else 20.0

        # 2. Breach & Remedies (25 คะแนน)
        has_breach_analysis = any(k in response_text for k in ["ผิดสัญญา", "เลิกสัญญา", "ค่าเสียหาย", "มัดจำ", "เบี้ยปรับ", "ส่งมอบ", "ชำระเงิน"])
        rubric_scores["breach_and_remedies"] = 25.0 if has_breach_analysis else 15.0

        # 3. Anti-Hallucination (20 คะแนน)
        rubric_scores["anti_hallucination"] = 20.0 if audit_res["passed"] else 0.0
        if not audit_res["passed"]:
            for v in audit_res["violations"]:
                findings.append(f"[{v['gate']}] {v['message']}")

        # 4. Practical Strategy (20 คะแนน)
        has_strategy = any(k in response_text for k in ["บอกกล่าว", "notice", "ทวงถาม", "ฟ้อง", "อายุความ", "คำแนะนำ", "ข้อควรระวัง"])
        rubric_scores["practical_recommendations"] = 20.0 if has_strategy else 10.0

        total_score = sum(rubric_scores.values())
        passed = total_score >= 80.0 and audit_res["passed"]

        return {
            "artifact_type": ArtifactType.CONTRACT_OPINION,
            "case_id": case_id,
            "title": title,
            "total_score": round(total_score, 1),
            "max_score": 100.0,
            "passed": passed,
            "rubric_scores": rubric_scores,
            "findings": findings,
            "detected_deka_numbers": audit_res.get("detected_deka_numbers", []),
            "unverified_deka_numbers": audit_res.get("unverified_deka_numbers", []),
            "mermaid_audit": audit_res.get("mermaid_audit", {})
        }

    def evaluate_system_doc(self, response_text: str) -> Dict[str, Any]:
        """
        ประเมินผลเอกสารสถาปัตยกรรมระบบและข้อกำหนดทางเทคนิค (System Documentation)
        Rubric (100 คะแนน):
        1. Specification Clarity & Structure (35 คะแนน)
        2. Technical Depth & Architecture (35 คะแนน)
        3. Visual & Syntax Integrity (30 คะแนน)
        """
        findings = []
        rubric_scores = {}

        # 1. Spec Clarity (35 คะแนน)
        has_headers = len(re.findall(r"^#{1,3}\s+", response_text, re.MULTILINE)) >= 4
        has_lists = len(re.findall(r"^\s*[-*]\s+", response_text, re.MULTILINE)) >= 4
        rubric_scores["specification_clarity"] = 35.0 if (has_headers and has_lists) else 20.0

        # 2. Technical Depth (35 คะแนน)
        has_code_or_tables = ("```" in response_text) or ("|" in response_text and "---" in response_text)
        has_tech_keywords = any(k in response_text.lower() for k in ["mcp", "cache", "sqlite", "mermaid", "architecture", "api", "flowchart"])
        rubric_scores["technical_depth"] = 35.0 if (has_code_or_tables and has_tech_keywords) else 20.0

        # 3. Visual & Syntax Integrity (30 คะแนน)
        mermaid_audit = validate_mermaid_syntax(response_text)
        rubric_scores["visual_integrity"] = 30.0 if mermaid_audit["passed"] else 15.0
        if not mermaid_audit["passed"]:
            for issue in mermaid_audit["issues"]:
                findings.append(f"Mermaid issue: {issue['error']} - {issue['content']}")

        total_score = sum(rubric_scores.values())
        passed = total_score >= 80.0 and len(findings) == 0

        return {
            "artifact_type": ArtifactType.SYSTEM_DOC,
            "case_id": None,
            "title": "System Architecture Specification",
            "total_score": round(total_score, 1),
            "max_score": 100.0,
            "passed": passed,
            "rubric_scores": rubric_scores,
            "findings": findings,
            "detected_deka_numbers": [],
            "unverified_deka_numbers": [],
            "mermaid_audit": mermaid_audit
        }

    def evaluate_file(
        self,
        filepath: str,
        case_id: Optional[str] = None,
        verified_deka_citations: Optional[List[str]] = None,
        cache: Optional[Any] = None
    ) -> Dict[str, Any]:
        """อ่านไฟล์เอกสารบทวิเคราะห์กฎหมาย (.md) และประเมินผลตามหมวดหมู่โดยอัตโนมัติ"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        artifact_type, inferred_case_id = classify_artifact(path.name, content)
        effective_case_id = case_id or inferred_case_id

        if artifact_type == ArtifactType.FULL_10_TOPICS:
            if effective_case_id:
                res = self.evaluate_response(effective_case_id, content, verified_deka_citations=verified_deka_citations, cache=cache)
            else:
                res = self.evaluate_comprehensive_analysis(None, content, verified_deka_citations=verified_deka_citations, cache=cache)
        elif artifact_type == ArtifactType.COMPREHENSIVE_ANALYSIS:
            res = self.evaluate_comprehensive_analysis(effective_case_id, content, verified_deka_citations=verified_deka_citations, cache=cache)
        elif artifact_type == ArtifactType.DEKA_RESEARCH:
            res = self.evaluate_deka_research(effective_case_id, content, verified_deka_citations=verified_deka_citations, cache=cache)
        elif artifact_type == ArtifactType.CONTRACT_OPINION:
            res = self.evaluate_contract_opinion(effective_case_id, content, verified_deka_citations=verified_deka_citations, cache=cache)
        elif artifact_type == ArtifactType.SYSTEM_DOC:
            res = self.evaluate_system_doc(content)
        else:
            res = self.evaluate_comprehensive_analysis(effective_case_id, content, verified_deka_citations=verified_deka_citations, cache=cache)

        res["file_evaluated"] = str(path)
        res["artifact_type"] = artifact_type
        return res

    def audit_output_directory(
        self,
        output_dir: Optional[str] = None,
        cache: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """สแกนและประเมินเอกสารทั้งหมดในโฟลเดอร์ output/ ตาม Benchmark Ground Truth และ Artifact Types"""
        from harness.cache import LegalMcpCache
        target_dir = Path(output_dir or os.path.join(os.path.dirname(__file__), "..", "output"))
        results = []
        if not target_dir.exists():
            return results

        if cache is None:
            cache = LegalMcpCache()

        verified_dekas = cache.get_all_verified_dekas() if hasattr(cache, "get_all_verified_dekas") else []

        for md_file in sorted(target_dir.glob("*.md")):
            try:
                eval_res = self.evaluate_file(
                    str(md_file),
                    verified_deka_citations=verified_dekas,
                    cache=cache
                )
                results.append(eval_res)
            except Exception as e:
                results.append({
                    "file_evaluated": str(md_file),
                    "artifact_type": "ERROR",
                    "case_id": None,
                    "passed": False,
                    "total_score": 0.0,
                    "error": str(e)
                })

        return results

def seed_case_research_cache(cache: LegalMcpCache) -> int:
    """Pre-seed verified Deka search results and statutes into cache from known case research"""
    return cache.seed_initial_data()

def main():
    import argparse
    import sys
    from harness.cache import LegalMcpCache

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

    elif args.file:
        result = evaluator.evaluate_file(args.file, case_id=args.case_id, cache=cache)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            status = "PASSED" if result["passed"] else "FAILED"
            print(f"\nEvaluation Result: {status} ({result['total_score']}/100.0)")
            print(f"Artifact Type: {result.get('artifact_type')}")
            print(f"Case ID: {result.get('case_id')} - {result.get('title')}")
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
            print(f"{'Filename':<55} | {'Artifact Type':<24} | {'Case ID':<26} | {'Score':<6} | {'Status':<6}")
            print("-" * 125)
            passed_count = 0
            for r in results:
                fname = Path(r.get("file_evaluated", "")).name
                art_type = r.get("artifact_type", "UNKNOWN")
                score = r.get("total_score", 0.0)
                passed = r.get("passed", False)
                if passed:
                    passed_count += 1
                status_str = "PASS" if passed else "FAIL"
                print(f"{fname:<55} | {art_type:<24} | {str(r.get('case_id', 'None')):<26} | {score:<6.1f} | {status_str:<6}")
            print("-" * 125)
            print(f"Summary: {passed_count}/{len(results)} files passed quality gates.\n")
        all_passed = len(results) > 0 and all(r.get("passed", False) for r in results)
        sys.exit(0 if all_passed else 1)

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
