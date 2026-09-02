import json
import re
import os
import unittest

BENCHMARK_PATH = os.path.join(os.path.dirname(__file__), "benchmark_cases.json")
AGENTS_MD_PATH = os.path.join(os.path.dirname(__file__), "..", ".agents", "AGENTS.md")
LEGAL_ADVISOR_PATH = os.path.join(os.path.dirname(__file__), "..", ".agents", "skills", "legal_advisor", "SKILL.md")

EXPECTED_10_TOPICS = [
    "บทสรุปของสถานการณ์ว่าเข้าข่ายประเด็นอะไร (Summary)",
    "หมวดหมู่สำหรับข้อกฎหมายหลัก (Category)",
    "รายการของข้อกฎหมาย/มาตราที่เกี่ยวข้องโดยตรง (Laws",
    "ประเภทคดีเป็นภาษาไทย (Case Category)",
    "ประเภทของศาลที่ตัดสินคดีนี้โดยตรง (Competent Court)",
    "แนวทางต่อสู้คดีของ โจทก์ / ผู้ร้อง / ผู้เสียหาย (Plaintiff Strategy)",
    "แนวทางต่อสู้คดีของ จำเลย / ผู้ถูกกล่าวหา (Defendant Strategy)",
    "แนวทางทำคดีความของพนักงานสอบสวนหรือเจ้าหน้าที่ตำรวจ (Investigator Guideline)",
    "แนวโน้มคำตัดสินของศาลสูงสุด หรือศาลฎีกา (Supreme Court Trend)",
    "คำแนะนำเพิ่มเติมเบื้องต้นเพื่อความปลอดภัยของฝ่ายผู้ใช้ (Advice)"
]

class TestLegalBenchmarks(unittest.TestCase):

    def test_benchmark_cases_structure(self):
        self.assertTrue(os.path.exists(BENCHMARK_PATH), "benchmark_cases.json must exist")
        with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)
        self.assertGreaterEqual(len(cases), 4, "Must contain at least 4 benchmark cases")
        for c in cases:
            self.assertIn("id", c)
            self.assertIn("title", c)
            self.assertIn("user_query", c)
            self.assertIn("ground_truth", c)
            gt = c["ground_truth"]
            self.assertIn("category", gt)
            self.assertIn("statutes", gt)
            self.assertIn("case_type", gt)
            self.assertIn("competent_court", gt)
            self.assertIn("prescription_years", gt)
            self.assertIn("anti_sycophancy_check", gt)
            self.assertIn("mcp_search_keywords", gt)

    def test_agents_md_contains_all_10_topics(self):
        self.assertTrue(os.path.exists(AGENTS_MD_PATH), "AGENTS.md must exist")
        with open(AGENTS_MD_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        for topic in EXPECTED_10_TOPICS:
            self.assertIn(topic, content, f"AGENTS.md missing topic: {topic}")

    def test_legal_advisor_contains_irac_and_guardrails(self):
        self.assertTrue(os.path.exists(LEGAL_ADVISOR_PATH), "legal_advisor/SKILL.md must exist")
        with open(LEGAL_ADVISOR_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        self.assertIn("IRAC", content)
        self.assertIn("Deka Grounding Gate", content)
        self.assertIn("Anti-Sycophancy", content)
        self.assertIn("mcp_resilience_guardian", content)

    def test_anti_hallucination_deka_regex_detector(self):
        fake_response_with_hallucination = (
            "หัวข้อที่ 9: แนวคำพิพากษาศาลฎีกาที่ 9876/2563 ได้ตัดสินว่าการกู้ยืมเงิน..."
        )
        fake_response_grounded_fallback = (
            "หัวข้อที่ 9: แนวบรรทัดฐานคำตัดสินศาลฎีกาเคยวินิจฉัยว่าการยืมเงินผ่านสื่ออิเล็กทรอนิกส์... "
            "(หมายเหตุ: ไม่สามารถดึงเลขที่ฎีกาจริงได้เนื่องจากระบบเชื่อมต่อฐานข้อมูลภายนอกไม่พร้อมใช้งาน)"
        )
        
        deka_regex = re.compile(r"ฎีกาที่\s*\d+/\d{4}")
        
        self.assertIsNotNone(deka_regex.search(fake_response_with_hallucination), "Should detect unverified deka number")
        self.assertIsNone(deka_regex.search(fake_response_grounded_fallback), "Fallback should not contain deka number")

if __name__ == "__main__":
    unittest.main()
