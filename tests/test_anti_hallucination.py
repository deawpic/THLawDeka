import unittest
from tests.anti_hallucination_verifier import (
    extract_all_deka_numbers,
    detect_unverified_deka_citations,
    sanitize_hallucinated_deka_numbers,
    detect_absolute_guarantees,
    audit_response_for_hallucinations
)

class TestAntiHallucination(unittest.TestCase):

    def test_extract_all_deka_variants(self):
        sample_text = (
            "ตามคำพิพากษาศาลฎีกาที่ 1234/2565 และคำพิพากษาฎีกาที่ 5678/2564 "
            "อีกทั้งยังมี ฎีกาที่ 999/2563 และ ฎ. 888/2562 รวมถึง ฎีกาเลขที่ 777/2561"
        )
        extracted = extract_all_deka_numbers(sample_text)
        self.assertIn("1234/2565", extracted)
        self.assertIn("5678/2564", extracted)
        self.assertIn("999/2563", extracted)
        self.assertIn("888/2562", extracted)
        self.assertIn("777/2561", extracted)
        self.assertEqual(len(extracted), 5)

    def test_detect_unverified_citations(self):
        sample_text = "คำพิพากษาศาลฎีกาที่ 1234/2565 และ ฎีกาที่ 9999/2566"
        verified_payload = ["1234/2565"] # Only 1234/2565 is verified from MCP
        
        unverified = detect_unverified_deka_citations(sample_text, verified_payload)
        self.assertEqual(unverified, ["9999/2566"])

    def test_sanitize_hallucinated_numbers(self):
        sample_text = "ตามคำพิพากษาศาลฎีกาที่ 9999/2566 ได้วางหลักการว่าการยืมเงิน..."
        sanitized = sanitize_hallucinated_deka_numbers(sample_text, verified_payloads=[])
        self.assertNotIn("9999/2566", sanitized)
        self.assertIn("แนวคำพิพากษาศาลฎีกาที่พึงเทียบเคียง", sanitized)

    def test_detect_judicial_discretion_violations(self):
        bad_text = "หากท่านนำสืบตามนี้ ท่านจะ ชนะคดีแน่นอน 100% อย่างแน่นอน"
        violations = detect_absolute_guarantees(bad_text)
        self.assertGreater(len(violations), 0)

    def test_audit_response_clean_pass(self):
        clean_text = (
            "หัวข้อที่ 9: แนวบรรทัดฐานคำตัดสินศาลฎีกาเคยวินิจฉัยว่า การยืมเงินผ่านสื่ออิเล็กทรอนิกส์ "
            "ถือเป็นหลักฐานเป็นหนังสือตามกฎหมายธุรกรรมทางอิเล็กทรอนิกส์\n"
            "(หมายเหตุ: ไม่สามารถดึงเลขที่ฎีกาจริงได้เนื่องจากระบบเชื่อมต่อฐานข้อมูลภายนอกไม่พร้อมใช้งาน)"
        )
        audit = audit_response_for_hallucinations(clean_text, verified_payloads=[])
        self.assertTrue(audit["passed"])
        self.assertEqual(len(audit["violations"]), 0)

    def test_audit_response_unverified_failure(self):
        hallucinated_text = "หัวข้อที่ 9: ตามคำพิพากษาศาลฎีกาที่ 9876/2560 ชนะคดีแน่นอน 100%"
        audit = audit_response_for_hallucinations(hallucinated_text, verified_payloads=[])
        self.assertFalse(audit["passed"])
        self.assertEqual(len(audit["violations"]), 2) # Deka Grounding Gate + Judicial Discretion Gate

if __name__ == "__main__":
    unittest.main()
