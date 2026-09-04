# Thai Legal Intelligence Advisor (AGY Project - Harness v3.0) ⚖️
**ผู้ช่วยผู้เชี่ยวชาญด้านกฎหมายไทยและทนายความผู้มีความรอบรู้ (Thai Legal Intelligence Advisor)**

โปรเจกต์นี้เป็นการแปลง **Gemini Gem** สำหรับคำปรึกษาทางกฎหมายไทยให้เป็น **Google Antigravity (AGY) Project** ที่สมบูรณ์ พร้อมระบบ **Agent Harness v3.0 (Enterprise Caching & Resilience Edition)** ที่ผสาน:
1. การวิเคราะห์แบบ **IRAC (Issue, Rule, Application, Conclusion)**
2. ระบบ **Legal MCP Dual-Layer Cache** (L1 In-Memory LRU + L2 SQLite Compressed BLOB zlib Level 6 พร้อมการันตี **Zero Legal Loss** และงบประมาณพื้นที่ 100 MB)
3. ระบบรักษาเสถียรภาพ MCP (`mcp_resilience_guardian` มี Exponential Backoff และ Safe Fallback)
4. ระบบตรวจสอบคำอ้างอิงและเลขฎีกา (`anti_hallucination_verifier` และ `deka_citation_verifier`)
5. ชุดทดสอบทางกฎหมายอัตโนมัติ (Benchmark Testbed & Cache Performance Suite)

---

## 📂 โครงสร้างโปรเจกต์ (Project Structure)

```text
thlawdeka/
├── .agents/
│   ├── AGENTS.md                  # Project-scoped rules (Harness v3.0: แคชข้อมูล, กฎ 10 หัวข้อ, IRAC, Guardrails 5 ชั้น)
│   ├── mcp_config.json            # ไฟล์ตั้งค่าสำหรับเชื่อมต่อ MCP (fourcorners-tlex, slegaltools-legal-v2, thai-legal)
│   └── skills/
│       ├── legal_advisor/         # [Core] ความสามารถวิเคราะห์คดี/ข้อกฎหมายไทย 10 หัวข้อ (IRAC Framework)
│       ├── legal_fact_elicitation/# [New] ระบบสกัดและซักถามข้อเท็จจริงสำคัญ (อายุความ/สัญญา) ก่อนวิเคราะห์
│       ├── deka_citation_verifier/# [New] ระบบตรวจสอบความถูกต้องของเลขฎีกาและตัวบท ป้องกันข้อมูลหลอน
│       ├── mcp_resilience_guardian/# [New] ระบบ Tier-0 Caching, 429 Rate Limit, Backoff และ Fallback
│       ├── api_key_setup/         # ความสามารถตั้งค่า API Key แบบ Interactive
│       ├── fc_mcp/                # ความสามารถตั้งค่า MCP setting ของ fourcorners-tlex
│       ├── sl_mcp/                # ความสามารถตั้งค่า MCP setting ของ slegaltools
│       └── tl_mcp/                # ความสามารถตั้งค่า MCP setting ของ thai-legal
├── tests/                         # [Evaluation & Benchmark Testbed]
│   ├── benchmark_cases.json       # ชุดคดีทดสอบมาตรฐาน (แพ่ง, อาญา, แรงงาน, ผู้บริโภค)
│   ├── legal_mcp_cache.py         # [New v3.0] โมดูลแคช L1/L2, zlib compression, query normalization, auto-recovery
│   ├── test_legal_cache.py        # [New v3.0] Unit tests ทดสอบแคช, zlib, Tiered TTL, 100MB budget, Concurrency
│   ├── test_legal_benchmarks.py   # Unit tests ตรวจสอบความถูกต้องของโครงสร้างกฎหมายและการตรวจจับเลขฎีกาหลอน
│   └── test_mcp_resilience.py     # Unit tests ทดสอบ Fault Injection, Caching Interceptor, Backoff และ Config
├── legal_mcp_cache.py             # Root export สำหรับเรียกใช้งานแคชโดยตรง
├── .env                           # เก็บข้อมูล API Keys (DEKA_API_KEY, FC_API_KEY, TL_API_KEY)
├── output/                        # โฟลเดอร์สำหรับบันทึกผลลัพธ์ UTF-8
└── README.md                      # คำอธิบายการใช้งาน (ไฟล์นี้)
```

---

## 💬 ข้อมูลที่ต้องเตรียมก่อนติดตั้ง

หากท่านต้องการเลขที่ฎีกาเทียบเคียง เนื่องจากมีการใช้บริการค้นหาฎีกา 3 บริการ ท่านจึงต้องเตรียม API KEY จากบริการเหล่านี้ :

1. https://app.fourcorners.law/settings?tab=mcp    ** FourCorners
2. https://api.slegaltools.digital/dashboard     ** SLegalTools
3. https://legaltech.in.th/dashboard/api-keys     ** Thai Legal

---

## 🛠️ วิธีการติดตั้งและเริ่มใช้งาน (Getting Started)

1. **เปิดโฟลเดอร์โปรเจกต์ใน Antigravity CLI หรือ Desktop**
   ระบบ Antigravity จะโหลดการตั้งค่าทั้งหมดจากโฟลเดอร์ `.agents/` โดยอัตโนมัติ

2. **ตั้งค่า API Key เพื่อใช้ค้นหาเลขที่คำพิพากษาศาลฎีกา**
   ระบบรองรับการค้นหาและตรวจสอบความถูกต้องของเลขที่ฎีกาผ่าน 3 บริการหลัก โดยบันทึกค่าไว้ในไฟล์ `.env` ที่ Root Directory:
   ```env
   DEKA_API_KEY=your_slegaltools_api_key_here
   FC_API_KEY=your_fourcorners_api_key_here
   TL_API_KEY=your_thailegal_api_key_here
   ```

   * **การตั้งค่าอัตโนมัติผ่าน Skill:**
     พิมพ์บอกเอเจนต์:
     ```text
     setup api key
     ```
     หรือสำหรับการตั้งค่า MCP เฉพาะค่าย:
     ```text
     set mcp fourcorners
     set mcp slegaltools
     set mcp thailegal
     ```

---

## 💬 รูปแบบการตอบกลับและกระบวนการทำงาน (Response Modes & Workflow)

1. **การตอบแบบทั่วไปเป็นลำดับแรกเสมอ (Default - General Response)**:
   * ให้คำปรึกษา วิเคราะห์ข้อกฎหมาย และแนวทางปฏิบัติอย่างกระชับ ตรงประเด็น และเข้าใจง่าย
2. **การตอบแบบโครงสร้าง 10 ข้อ (10 Topics on Explicit Request)**:
   * เมื่อผู้ใช้ระบุว่าต้องการ **"แบบ 10 ข้อ"** หรือ **"สรุป 10 หัวข้อ"** ระบบจะดำเนินกระบวนการดังนี้:
     1. **Fact Intake**: หากข้อเท็จจริงขาดมิติสำคัญ (เช่น วันที่เกิดเหตุ/อายุความ หรือหลักฐานสัญญา) ระบบจะซักถามสั้นๆ 2-3 ข้อ (`legal_fact_elicitation`)
     2. **ถามบริการค้นหาฎีกา**: ให้ผู้ใช้เลือกว่าต้องการใช้ fourcorners, slegaltools, thailegal หรือไม่ใช้บริการ
     3. **วิเคราะห์ด้วย IRAC Framework**: จัดโครงสร้าง 10 หัวข้ออย่างเป็นระบบ
     4. **สืบค้นและป้องกันข้อผิดพลาด**: ค้นหาผ่าน MCP ด้วยการควบคุมของ `mcp_resilience_guardian` (มี Backoff Retry) และตรวจทานความถูกต้องด้วย `deka_citation_verifier`

---

## 📋 โครงสร้างผลลัพธ์ 10 หัวข้อ (10 Topics Output Schema)

1. **บทสรุปของสถานการณ์ว่าเข้าข่ายประเด็นอะไร (Summary)** - สรุปเนื้อหาของคดีหรือข้อขัดแย้ง
2. **หมวดหมู่สำหรับข้อกฎหมายหลัก (Category)** - แยกแยะหมวดหมู่กฎหมาย เช่น กฎหมายครอบครัว, กฎหมายแรงงาน
3. **รายการของข้อกฎหมาย/มาตราที่เกี่ยวข้องโดยตรง (Laws & Statutes - IRAC)** - ระบุชื่อกฎหมาย เลขมาตรา สาระสำคัญ และการปรับใช้กับข้อเท็จจริง (Application)
4. **ประเภทคดีเป็นภาษาไทย (Case Category)** - เช่น คดีแพ่ง, คดีอาญา, คดีผู้บริโภค
5. **ประเภทของศาลที่ตัดสินคดีนี้โดยตรง (Competent Court)** - เช่น ศาลอาญา, ศาลแพ่ง, ศาลแขวง, ศาลชำนัญพิเศษ
6. **แนวทางต่อสู้คดีของ โจทก์ / ผู้ร้อง / ผู้เสียหาย (Plaintiff Strategy)** - วิธีการรวบรวมหลักฐาน, **ภาระการพิสูจน์ (Burden of Proof)**, **กำหนดอายุความ (Prescription Period)**
7. **แนวทางต่อสู้คดีของ จำเลย / ผู้ถูกกล่าวหา (Defendant Strategy)** - แนวทางแก้ต่าง, การโต้แย้งภาระการพิสูจน์, การยกข้อต่อสู้เรื่อง **อายุความขาด**
8. **แนวทางทำคดีของพนักงานสอบสวนหรือเจ้าหน้าที่ (Investigator Guideline)** - วิธีสืบสวนและการรวบรวมสำนวน
9. **แนวโน้มคำตัดสินของศาลสูงสุด หรือศาลฎีกา (Supreme Court Trend)** - บรรทัดฐานคำตัดสินศาลฎีกาที่พึงเทียบเคียง (ผ่านการตรวจรับรองจาก MCP)
10. **คำแนะนำเพิ่มเติมเพื่อความปลอดภัย (Advice)** - ข้อควรระวังและการปฏิบัติตัวขั้นเริ่มต้นเพื่อความปลอดภัย

---

## 🧪 การรันชุดทดสอบ Evaluation, Benchmark & CI/CD Testbed

ท่านสามารถรันการทดสอบ Unit Tests (44 Tests), ตรวจสอบสุขภาพแคช และประเมินคุณภาพเอกสารกฎหมายได้ผ่านสคริปต์อัตโนมัติ:

```bash
# 1. รันกระบวนการตรวจสอบทั้งหมดในคำสั่งเดียว (Full Pipeline)
./run_harness.sh
# หรือใช้ Make:
make all
```

หรือเลือกรันเฉพาะคำสั่งที่ต้องการ:

```bash
# รันเฉพาะ Unit Tests ทั้งหมด (44/44 ผ่าน 100% ภายใน 2.5s)
make test
# หรือ: python3 -m unittest discover -s tests -p "test_*.py" -v

# ตรวจสอบสถิติแคชและรายงานความคุ้มค่าทางธุรกิจ (FinOps Telemetry: Hit Ratio, Latency, Cost Saved)
python3 legal_mcp_cache.py --stats

# ตรวจสอบรายชื่อเลขฎีกาที่ผ่านการตรวจสอบจาก MCP ในฐานข้อมูลแคช (Grounding Oracle)
python3 legal_mcp_cache.py --verified-dekas

# ล้างแคชเฉพาะหมวดหมู่กฎหมาย (Tag-Based Invalidation เช่น หมวดที่ดิน)
python3 legal_mcp_cache.py --purge-tag land

# สแกนและให้คะแนนเอกสารบทวิเคราะห์ใน output/ ด้วยระบบประเมินผลอัตโนมัติ
python3 tests/eval_benchmark_runner.py --audit-outputs
```

ผลการทดสอบครอบคลุม:
- ความครบถ้วนของ Schema 10 หัวข้อ และการประเมินผล Ground Truth ด้วย IRAC Framework
- การป้องกันการแต่งเลขฎีกาหลอนอัตโนมัติ (Deka Grounding Gate & Cache Auto-Whitelist)
- การทำงานของ Dual-Layer Cache ระดับ Enterprise (L1 LRU <0.2ms, L2 SQLite zlib Level 6 <2.0ms)
- การกลั่นกรองข้อมูล Zero Legal Loss 100% และการประหยัด Gemini Input Tokens (50% - 70%)
- การทำ Legal Query Normalization และการจำแนกคำสลับตำแหน่ง (Token Permutations)
- การล้างแคชรายหมวด (Tag-Based Invalidation) และการคืนพื้นที่ดิสก์อัตโนมัติ (100 MB Quota)
- เสถียรภาพ Concurrency / Multi-threading และระบบกู้คืนอัตโนมัติ (Self-Healing & Disaster Recovery)
- การจำลอง Fault Injection (HTTP 429, Backoff with Jitter) และ Safe Fallback Protocol

---

## 💾 การบันทึกไฟล์ (File Saving & Encoding)
* หากผู้ใช้ขอให้บันทึกไฟล์ข้อมูล ให้บันทึกไฟล์ไว้ที่โฟลเดอร์ `./output` เสมอ
* เข้ารหัสแบบ **UTF-8 (Encoding: UTF-8)** เสมอ

---

## ⚖️ ข้อจำกัดความรับผิดชอบ (Disclaimer)
*คำแนะนำกฎหมายจากโปรแกรมนี้เป็นเพียงข้อมูลเบื้องต้นที่วิเคราะห์ตามหลักตัวบทกฎหมายและเทคโนโลยีปัญญาประดิษฐ์ ไม่สามารถนำมาใช้แทนคำแนะนำของทนายความวิชาชีพหรือที่ปรึกษากฎหมายอย่างเป็นทางการได้*
