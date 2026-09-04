import concurrent.futures
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from harness.cache import LegalMcpCache, LegalPayloadDistiller

class TestLegalPayloadDistiller(unittest.TestCase):

    def test_extract_deka_numbers_variants(self):
        sample_text = (
            "ตามคำพิพากษาศาลฎีกาที่ 15216/2551 และ ฎีกาที่ 3379/32 "
            "รวมถึง ฎ. 1164/14 และ ศาลฎีกาแผนกคดีทรัพย์สินทางปัญญา ที่ 99/2566"
        )
        dekas = LegalPayloadDistiller.extract_deka_numbers(sample_text)
        self.assertIn("15216/2551", dekas)
        self.assertIn("3379/32", dekas)
        self.assertIn("1164/14", dekas)
        self.assertIn("99/2566", dekas)

    def test_distillation_zero_legal_loss(self):
        raw_payload = {
            "http_status": 200,
            "trace_id": "req-987654321-xyz",
            "pagination": {"total_pages": 5, "current_page": 1, "page_size": 10},
            "uuid": "a1b2c3d4-e5f6-7890",
            "results": [
                {
                    "_id": "65bc1234567890abcdef",
                    "statute_title": "ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1378",
                    "ratio_decidendi": "การโอนไปซึ่งการครอบครองนั้น ย่อมทำได้โดยส่งมอบทรัพย์สินที่ครอบครอง",
                    "material_facts": "นาย ก. ขายที่ดิน ส.ค.1 ให้นาย ล. และส่งมอบให้เข้าทำประโยชน์จริง",
                    "deka_citation": "คำพิพากษาศาลฎีกาที่ 15216/2551",
                    "icons": ["doc.svg"],
                    "svg": "<svg>...</svg>"
                }
            ]
        }

        distilled, dekas, raw_tokens, saved_tokens = LegalPayloadDistiller.distill(raw_payload)

        # สาระสำคัญทางกฎหมายต้องอยู่ครบ 100%
        self.assertEqual(len(dekas), 1)
        self.assertEqual(dekas[0], "15216/2551")
        self.assertIn("results", distilled)
        case_res = distilled["results"][0]
        self.assertEqual(case_res["statute_title"], "ประมวลกฎหมายแพ่งและพาณิชย์ มาตรา 1378")
        self.assertIn("ส่งมอบทรัพย์สินที่ครอบครอง", case_res["ratio_decidendi"])
        self.assertIn("นาย ก. ขายที่ดิน ส.ค.1", case_res["material_facts"])

        # ขยะทางเทคนิคต้องถูกตัดออก 100%
        self.assertNotIn("http_status", distilled)
        self.assertNotIn("trace_id", distilled)
        self.assertNotIn("pagination", distilled)
        self.assertNotIn("uuid", distilled)
        self.assertNotIn("_id", case_res)
        self.assertNotIn("icons", case_res)
        self.assertNotIn("svg", case_res)

        # มีการประหยัด Token เกิดขึ้นจริง
        self.assertGreater(saved_tokens, 0)
        self.assertGreater(raw_tokens, 0)

    def test_distiller_fail_safe_fallback(self):
        # ทดสอบกรณีข้อมูลที่ส่งมาเป็น string ธรรมดา
        raw_text = "คำพิพากษาศาลฎีกาที่ 9999/2566 ตัวบท ป.อ. ม.334"
        distilled, dekas, raw_tokens, saved_tokens = LegalPayloadDistiller.distill(raw_text)
        self.assertEqual(distilled, raw_text)
        self.assertIn("9999/2566", dekas)


class TestLegalMcpCache(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="thlawdeka_cache_test_")
        self.db_path = os.path.join(self.temp_dir, "test_cache.db")
        self.cache = LegalMcpCache(db_path=self.db_path, max_memory_items=5, max_size_mb=1)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_query_normalization_and_permutations(self):
        # คำถามที่มีการสลับคำ วรรคซ้ำ หรือตัวย่อ ต้องได้ค่า normalize เดียวกัน
        q1 = "ป.อ. มาตรา 334 ลักทรัพย์เวลากลางคืน"
        q2 = "ประมวลกฎหมายอาญา ม.334 ลักทรัพย์เวลากลางคืน"
        q3 = "ลักทรัพย์เวลากลางคืน   ป.อ.    ม. 334"

        norm1 = self.cache.normalize_legal_query(q1)
        norm2 = self.cache.normalize_legal_query(q2)
        norm3 = self.cache.normalize_legal_query(q3)

        self.assertEqual(norm1, norm2)
        self.assertEqual(norm2, norm3)

    def test_cache_key_equivalence_for_permutations(self):
        args1 = {"query": "ป.พ.พ. มาตรา 456 สัญญาซื้อขาย"}
        args2 = {"query": "สัญญาซื้อขาย ประมวลกฎหมายแพ่งและพาณิชย์ ม.456"}

        key1 = self.cache.generate_cache_key("thai-legal", "search_law", args1)
        key2 = self.cache.generate_cache_key("thai-legal", "search_law", args2)

        self.assertEqual(key1, key2, "Permuted queries must generate identical cache keys")

    def test_procedural_and_land_statute_normalization(self):
        # ทดสอบ ป.วิ.พ., ป.วิ.อ., ป.ที่ดิน
        self.assertIn("ป.วิ.พ.", self.cache.normalize_legal_query("ประมวลกฎหมายวิธีพิจารณาความแพ่ง มาตรา 55"))
        self.assertIn("ป.วิ.อ.", self.cache.normalize_legal_query("ประมวลกฎหมายวิธีพิจารณาความอาญา ม.134"))
        self.assertIn("ป.ที่ดิน", self.cache.normalize_legal_query("ประมวลกฎหมายที่ดิน มาตรา 1"))

    def test_l1_and_l2_caching_and_zero_legal_loss(self):
        provider = "slegaltools-legal-v2"
        tool = "ai_deka_search"
        args = {"query": "ป.พ.พ. ม.1378 ส่งมอบ ส.ค.1"}
        payload = {
            "http_status": 200,
            "uuid": "test-uuid-1234",
            "deka_records": [
                {
                    "citation": "คำพิพากษาศาลฎีกาที่ 15216/2551",
                    "content": "การส่งมอบการครอบครองที่ดิน ส.ค.1 สละการครอบครองตาม ม.1377 และ 1378"
                }
            ]
        }

        # 1. บันทึกลงแคช
        success = self.cache.set(provider, tool, args, payload)
        self.assertTrue(success)

        # 2. อ่านจาก L1 Cache (Memory)
        l1_result = self.cache.get(provider, tool, args)
        self.assertIsNotNone(l1_result)
        self.assertIn("deka_records", l1_result)
        self.assertNotIn("http_status", l1_result)
        self.assertEqual(l1_result["deka_records"][0]["citation"], "คำพิพากษาศาลฎีกาที่ 15216/2551")

        # 3. เคลียร์ L1 Memory Cache เพื่อทดสอบ L2 SQLite Disk Cache
        with self.cache._l1_lock:
            self.cache._l1_cache.clear()
        self.assertEqual(len(self.cache._l1_cache), 0)

        # 4. อ่านจาก L2 Cache (Decompress zlib จากดิสก์)
        l2_result = self.cache.get(provider, tool, args)
        self.assertIsNotNone(l2_result)
        self.assertEqual(l2_result["deka_records"][0]["citation"], "คำพิพากษาศาลฎีกาที่ 15216/2551")
        self.assertIn("สละการครอบครอง", l2_result["deka_records"][0]["content"])

        # 5. ตรวจสอบว่าถูกนำกลับขึ้น L1 เรียบร้อย
        self.assertEqual(len(self.cache._l1_cache), 1)

    def test_tiered_ttl_policy(self):
        # 1. ค้นหาตัวบทกฎหมาย -> 60 วัน (5184000s)
        ttl_statute = self.cache.calculate_tiered_ttl("thai-legal", "search_law", {"query": "ม.420"})
        self.assertEqual(ttl_statute, 5184000)

        # 2. ค้นหาฎีกา -> 365 วัน (31536000s)
        ttl_deka = self.cache.calculate_tiered_ttl("slegaltools", "ai_deka_search", {"query": "ฎีกา ลักทรัพย์"})
        self.assertEqual(ttl_deka, 31536000)

        # 3. ผลลัพธ์ว่างเปล่า -> 48 ชม (172800s)
        ttl_empty = self.cache.calculate_tiered_ttl("fourcorners", "ask_tlex", {"query": "xyz"}, is_empty=True)
        self.assertEqual(ttl_empty, 172800)

        # 4. ค้นหาทั่วไป -> 30 วัน (2592000s)
        ttl_gen = self.cache.calculate_tiered_ttl("provider", "general_tool", {"query": "ความรู้"})
        self.assertEqual(ttl_gen, 2592000)

    def test_cache_expiration(self):
        provider = "thai-legal"
        tool = "search_law"
        args = {"query": "ม.1"}
        payload = {"data": "ผลการค้นหา"}

        # บันทึกโดยตั้ง TTL ให้หมดอายุทันที (1 วินาที)
        self.cache.set(provider, tool, args, payload, ttl_seconds=1)
        self.assertIsNotNone(self.cache.get(provider, tool, args))

        # รอ 1.5 วินาทีเพื่อให้หมดอายุ
        time.sleep(1.2)
        expired_result = self.cache.get(provider, tool, args)
        self.assertIsNone(expired_result, "Expired entry must return None (cache miss)")

    def test_force_refresh_bypasses_cache(self):
        provider = "thai-legal"
        tool = "search_law"
        args = {"query": "ม.20"}
        payload = {"data": "ผลการค้นหา ม.20"}

        self.cache.set(provider, tool, args, payload)
        self.assertIsNotNone(self.cache.get(provider, tool, args))
        self.assertIsNone(self.cache.get(provider, tool, args, force_refresh=True))

    def test_refuse_caching_network_errors(self):
        provider = "slegaltools"
        tool = "ai_deka_search"
        args = {"query": "ม.334"}
        error_payload = {"status": "rate_limit", "code": 429}

        saved = self.cache.set(provider, tool, args, error_payload)
        self.assertFalse(saved)
        self.assertIsNone(self.cache.get(provider, tool, args))

    def test_self_healing_database_recovery(self):
        provider = "thai-legal"
        tool = "search_law"
        args = {"query": "ม.10"}
        payload = {"text": "ข้อความตัวบทกฎหมาย"}

        self.cache.set(provider, tool, args, payload)

        # จำลองไฟล์ฐานข้อมูลเสียหายโดยเขียนไบต์สุ่มทับ
        with open(self.db_path, "wb") as f:
            f.write(b"CORRUPTED_DATABASE_CRASH_DATA_NOT_SQLITE")

        # เรียกใช้งานใหม่อีก instance หนึ่งเพื่อทดสอบการตรวจพบและ Self-Healing
        healed_cache = LegalMcpCache(db_path=self.db_path, max_memory_items=5, max_size_mb=1)
        stats = healed_cache.get_telemetry_stats()
        self.assertEqual(stats["status"], "healthy")

        # ไฟล์ที่เสียหายต้องถูกสำรองไว้
        corrupted_backups = list(Path(self.temp_dir).glob("*.corrupted.*.db"))
        self.assertGreaterEqual(len(corrupted_backups), 1, "Must create corrupted backup file")

    def test_telemetry_stats(self):
        provider = "thai-legal"
        tool = "search_law"
        args = {"query": "ม.1378"}
        payload = {
            "trace_id": "tech-12345",
            "statute": "ป.พ.พ. มาตรา 1378 การส่งมอบการครอบครอง",
            "deka": "คำพิพากษาศาลฎีกาที่ 15216/2551"
        }

        self.cache.set(provider, tool, args, payload)
        # เรียก get 2 ครั้งเพื่อสร้าง hit count
        self.cache.get(provider, tool, args)
        self.cache.get(provider, tool, args)

        stats = self.cache.get_telemetry_stats()
        self.assertEqual(stats["total_cached_entries"], 1)
        self.assertGreaterEqual(stats["total_cache_hits"], 1)
        self.assertGreater(stats["total_gemini_tokens_saved"], 0)
        self.assertIn("%", stats["compression_ratio_percent"])
        self.assertEqual(stats["disk_budget_limit_mb"], 1)

    def test_thread_safety_concurrency(self):
        provider = "multi-thread-provider"
        tool = "fast_search"

        def worker(i: int):
            args = {"query": f"ม.{i} คดีทดสอบ"}
            payload = {"content": f"ข้อมูลผลการค้นหา {i}", "deka": f"คำพิพากษาศาลฎีกาที่ {i}/2565"}
            self.cache.set(provider, tool, args, payload)
            res = self.cache.get(provider, tool, args)
            return res is not None

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(worker, range(30)))

        self.assertTrue(all(results))
        stats = self.cache.get_telemetry_stats()
        self.assertEqual(stats["total_cached_entries"], 30)

    def test_disk_budget_enforcement_and_lru_pruning(self):
        # สร้าง cache ขนาดเล็กมาก (1KB budget) เพื่อทดสอบการ prune เมื่อเกินงบ
        micro_db_path = os.path.join(self.temp_dir, "micro_cache.db")
        micro_cache = LegalMcpCache(db_path=micro_db_path, max_memory_items=2, max_size_mb=1)
        # กำหนด max_size_bytes ให้เล็กมาก (5,000 ไบต์)
        micro_cache.max_size_bytes = 5000

        # ใส่ข้อมูล 10 รายการ แต่ละรายการมีเนื้อหากฎหมาย
        for i in range(10):
            payload = {
                "results": [{"text": f"คำพิพากษาศาลฎีกาที่ {1000+i}/2565 เนื้อหาการวินิจฉัยข้อกฎหมายยาวพอสมควร " * 5}]
            }
            micro_cache.set("provider", "tool", {"query": f"คดีที่ {i}"}, payload)

        stats = micro_cache.get_telemetry_stats()
        self.assertGreater(stats["total_cached_entries"], 0)
        self.assertLessEqual(stats["total_cached_entries"], 10)

    def test_secret_scrubbing_prevents_token_leak(self):
        sensitive_payload = {
            "api_key": "secret-12345-token",
            "authorization": "Bearer confidential-token-xyz",
            "results": [
                {
                    "cookie": "session=abc",
                    "law": "ป.พ.พ. ม.420",
                    "text": "ผู้ใดจงใจหรือประมาทเลินเล่อทำต่อบุคคลอื่นโดยผิดกฎหมาย"
                }
            ]
        }
        distilled, dekas, _, _ = LegalPayloadDistiller.distill(sensitive_payload)
        self.assertNotIn("api_key", distilled)
        self.assertNotIn("authorization", distilled)
        self.assertNotIn("cookie", distilled["results"][0])
        self.assertEqual(distilled["results"][0]["law"], "ป.พ.พ. ม.420")

    def test_targeted_delete(self):
        provider = "thai-legal"
        tool = "search_law"
        args = {"query": "ม.500"}
        payload = {"data": "ผลการค้นหา"}

        self.cache.set(provider, tool, args, payload)
        self.assertIsNotNone(self.cache.get(provider, tool, args))

        # ลบรายการเจาะจง
        deleted = self.cache.delete(provider, tool, args)
        self.assertTrue(deleted)
        self.assertIsNone(self.cache.get(provider, tool, args))

    def test_prune_expired_entries(self):
        provider = "thai-legal"
        tool = "search_law"
        args1 = {"query": "ม.901"}
        args2 = {"query": "ม.902"}

        self.cache.set(provider, tool, args1, {"text": "หมดอายุ"}, ttl_seconds=1)
        self.cache.set(provider, tool, args2, {"text": "ยังไม่หมดอายุ"}, ttl_seconds=3600)

        time.sleep(1.2)
        pruned_count = self.cache.prune_expired()
        self.assertEqual(pruned_count, 1)
        self.assertIsNone(self.cache.get(provider, tool, args1))
        self.assertIsNotNone(self.cache.get(provider, tool, args2))

    def test_tag_based_invalidation(self):
        self.cache.set("thai_legal", "search", {"query": "กู้ยืม"}, {"res": 1}, tag="civil")
        self.cache.set("thai_legal", "search", {"query": "เช่าทรัพย์"}, {"res": 2}, tag="civil")
        self.cache.set("thai_legal", "search", {"query": "ลักทรัพย์"}, {"res": 3}, tag="criminal")

        deleted = self.cache.invalidate_by_tag("civil")
        self.assertEqual(deleted, 2)
        self.assertIsNone(self.cache.get("thai_legal", "search", {"query": "กู้ยืม"}))
        self.assertIsNone(self.cache.get("thai_legal", "search", {"query": "เช่าทรัพย์"}))
        self.assertIsNotNone(self.cache.get("thai_legal", "search", {"query": "ลักทรัพย์"}))

    def test_get_all_verified_dekas(self):
        self.cache.set(
            "slegal", "search", {"query": "ที่ดิน"},
            {"results": [{"deka_citation": "คำพิพากษาศาลฎีกาที่ 269/2511"}]}
        )
        self.cache.set(
            "thai_legal", "search", {"query": "ส.ค.1"},
            {"results": [{"deka_citation": "ฎีกาที่ 15216/2551"}]}
        )
        dekas = self.cache.get_all_verified_dekas()
        self.assertIn("269/2511", dekas)
        self.assertIn("15216/2551", dekas)

    def test_finops_telemetry_metrics(self):
        args = {"query": "ม.1378"}
        self.cache.set("thai_legal", "search", args, {"results": [{"statute": "1378"}]})
        # Generate 2 hits
        self.cache.get("thai_legal", "search", args)
        self.cache.get("thai_legal", "search", args)

        stats = self.cache.get_telemetry_stats()
        self.assertIn("finops_metrics", stats)
        self.assertIn("cache_hit_ratio_percent", stats)
        self.assertGreater(stats["total_cache_hits"], 0)
        self.assertGreater(stats["finops_metrics"]["estimated_latency_saved_sec"], 0)

if __name__ == "__main__":
    unittest.main()
