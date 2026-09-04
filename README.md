# Thai Legal Intelligence Advisor (AGY Project - Harness v3.0) ⚖️
**ผู้ช่วยผู้เชี่ยวชาญด้านกฎหมายไทยและทนายความผู้มีความรอบรู้ (Thai Legal Intelligence Advisor)**

**Ai Agent**  สำหรับคำปรึกษาทางกฎหมายไทยใช้งานกับ **Google Antigravity Desktop/CLI** ที่สมบูรณ์ พร้อมระบบ **Agent Harness v3.0 (Enterprise Caching & Resilience Edition)** ที่ผสาน:
1. การวิเคราะห์แบบ **IRAC (Issue, Rule, Application, Conclusion)**
2. ระบบ **MCP Dual-Layer Cache** ช่วยประหยัด Quota MCP และ AI Token
3. ระบบรักษาเสถียรภาพ MCP 
4. ระบบตรวจสอบคำอ้างอิงและเลขฎีกา กันอาการหลอนของเอไอ
5. ชุดทดสอบทางกฎหมายอัตโนมัติ (Benchmark Testbed & Cache Performance Suite)

---

## 📑 สารบัญ (Table of Contents)

- [1. 📂 โครงสร้างโปรเจกต์ (Project Structure)](#1--โครงสร้างโปรเจกต์-project-structure)
- [2. 🔑 ข้อมูลที่ต้องเตรียมก่อนติดตั้ง (Prerequisites)](#2--ข้อมูลที่ต้องเตรียมก่อนติดตั้ง-prerequisites)
- [3. 🛠️ วิธีการติดตั้งและเริ่มใช้งาน (Getting Started)](#3-️-วิธีการติดตั้งและเริ่มใช้งาน-getting-started)
- [4. 🔄 รูปแบบการตอบกลับและกระบวนการทำงาน (Response Modes & Workflow)](#4--รูปแบบการตอบกลับและกระบวนการทำงาน-response-modes--workflow)
- [5. 📋 โครงสร้างผลลัพธ์ 10 หัวข้อ (10 Topics Output Schema)](#5--โครงสร้างผลลัพธ์-10-หัวข้อ-10-topics-output-schema)
- [6. 🧪 การรันชุดทดสอบ Evaluation, Benchmark & CI/CD Testbed](#6--การรันชุดทดสอบ-evaluation-benchmark--cicd-testbed)
- [7. 💾 การบันทึกไฟล์ (File Saving & Encoding)](#7--การบันทึกไฟล์-file-saving--encoding)
- [8. ⚖️ ข้อจำกัดความรับผิดชอบ (Disclaimer)](#8-️-ข้อจำกัดความรับผิดชอบ-disclaimer)

---

<a id="1--โครงสร้างโปรเจกต์-project-structure"></a>
## 📂 1. โครงสร้างโปรเจกต์ (Project Structure)

```text
thlawdeka/
├── README.md                      # คำอธิบายการใช้งาน (ไฟล์นี้)
├── AGENTS.md                      # [Mirrored] กฎหลักและระบบวิเคราะห์ 10 หัวข้อ (IRAC & Guardrails)
├── Makefile                       # ทางลัดสำหรับรันชุดทดสอบ (make, make test, make stats, make audit)
├── .env.example                   # ตัวอย่างการตั้งค่า API Keys
├── .agents/
│   ├── AGENTS.md                  # Workspace rules mirror สำหรับ Antigravity Engine
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
├── harness/                       # 🛡️ [Harness Core & Evaluation Engine]
│   ├── __init__.py                # Package export สำหรับโมดูลหลัก
│   ├── cache.py                   # ตัวจัดการแคช L1/L2, zlib compression, query normalization, FinOps CLI
│   ├── verifier.py                # ตัวตรวจสอบและกรองเลขฎีกา/ตัวบทหลอนอัตโนมัติ (Anti-Hallucination)
│   ├── evaluator.py               # ระบบประเมินผลคำปรึกษาและ Output Auditor
│   └── benchmark_cases.json       # ชุดคดีทดสอบมาตรฐาน (แพ่ง, อาญา, แรงงาน, ผู้บริโภค, ที่ดิน ส.ค.1)
├── tests/                         # 🧪 [Pure Test Suites เท่านั้น]
│   ├── __init__.py
│   ├── test_legal_cache.py        # Unit tests ทดสอบแคช, zlib, Tiered TTL, 100MB budget, Concurrency
│   ├── test_legal_benchmarks.py   # Unit tests ตรวจสอบความถูกต้องของโครงสร้างกฎหมายและ Mirror Sync
│   ├── test_anti_hallucination.py # Unit tests ทดสอบ Auto-Grounding Oracle และตัวบทกฎหมาย
│   └── test_mcp_resilience.py     # Unit tests ทดสอบ Fault Injection, Caching Interceptor, Backoff และ Config
├── scripts/                       # 🚀 [DevOps & Automation Scripts]
│   └── run_harness.sh             # สคริปต์รันการทดสอบและ Audit คุณภาพทั้งระบบ (Unified Pipeline)
├── output/                        # โฟลเดอร์สำหรับบันทึกผลลัพธ์ UTF-8 และสเปก v3.3
└── .env                           # เก็บข้อมูล API Keys (DEKA_API_KEY, FC_API_KEY, TL_API_KEY)
```

---

<a id="2--ข้อมูลที่ต้องเตรียมก่อนติดตั้ง-prerequisites"></a>
## 🔑 2. ข้อมูลที่ต้องเตรียมก่อนติดตั้ง (Prerequisites)

หากท่านต้องการเลขที่ฎีกาเทียบเคียง เนื่องจากมีการใช้บริการค้นหาฎีกา 3 บริการ ท่านจึงต้องเตรียม API KEY จากบริการเหล่านี้ :

1. https://app.fourcorners.law/settings?tab=mcp    ** FourCorners
2. https://api.slegaltools.digital/dashboard     ** SLegalTools
3. https://legaltech.in.th/dashboard/api-keys     ** Thai Legal

---

<a id="3-️-วิธีการติดตั้งและเริ่มใช้งาน-getting-started"></a>
## 🛠️ 3. วิธีการติดตั้งและเริ่มใช้งาน (Getting Started)

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

<a id="4--รูปแบบการตอบกลับและกระบวนการทำงาน-response-modes--workflow"></a>
## 🔄 4. รูปแบบการตอบกลับและกระบวนการทำงาน (Response Modes & Workflow)

1. **การตอบแบบทั่วไปเป็นลำดับแรกเสมอ (Default - General Response)**:
   * ให้คำปรึกษา วิเคราะห์ข้อกฎหมาย และแนวทางปฏิบัติอย่างกระชับ ตรงประเด็น และเข้าใจง่าย
2. **การตอบแบบโครงสร้าง 10 ข้อ (10 Topics on Explicit Request)**:
   * เมื่อผู้ใช้ระบุว่าต้องการ **"แบบ 10 ข้อ"** หรือ **"สรุป 10 หัวข้อ"** ระบบจะดำเนินกระบวนการดังนี้:
     1. **Fact Intake**: หากข้อเท็จจริงขาดมิติสำคัญ (เช่น วันที่เกิดเหตุ/อายุความ หรือหลักฐานสัญญา) ระบบจะซักถามสั้นๆ 2-3 ข้อ (`legal_fact_elicitation`)
     2. **ถามบริการค้นหาฎีกา**: ให้ผู้ใช้เลือกว่าต้องการใช้ fourcorners, slegaltools, thailegal หรือไม่ใช้บริการ
     3. **วิเคราะห์ด้วย IRAC Framework**: จัดโครงสร้าง 10 หัวข้ออย่างเป็นระบบ
     4. **สืบค้นและป้องกันข้อผิดพลาด**: ค้นหาผ่าน MCP ด้วยการควบคุมของ `mcp_resilience_guardian` (มี Backoff Retry) และตรวจทานความถูกต้องด้วย `deka_citation_verifier`

---

<a id="5--โครงสร้างผลลัพธ์-10-หัวข้อ-10-topics-output-schema"></a>
## 📋 5. โครงสร้างผลลัพธ์ 10 หัวข้อ (10 Topics Output Schema)

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

<a id="6--การรันชุดทดสอบ-evaluation-benchmark--cicd-testbed"></a>
## 🧪 6. การรันชุดทดสอบ Evaluation, Benchmark & CI/CD Testbed

ท่านสามารถรันการทดสอบ Unit Tests (45 Tests), ตรวจสอบสุขภาพแคช และประเมินคุณภาพเอกสารกฎหมายได้ผ่านสคริปต์อัตโนมัติ:

```bash
# 1. รันกระบวนการตรวจสอบทั้งหมดในคำสั่งเดียว (Full Pipeline)
./scripts/run_harness.sh
# หรือใช้ Make:
make all
```

หรือเลือกรันเฉพาะคำสั่งที่ต้องการ:

```bash
# รันเฉพาะ Unit Tests ทั้งหมด (45/45 ผ่าน 100% ภายใน 2.5s)
make test
# หรือ: python3 -m unittest discover -s tests -p "test_*.py" -v

# ตรวจสอบสถิติแคชและรายงานความคุ้มค่าทางธุรกิจ (FinOps Telemetry: Hit Ratio, Latency, Cost Saved)
python3 harness/cache.py --stats
# หรือ: make stats

# ตรวจสอบรายชื่อเลขฎีกาที่ผ่านการตรวจสอบจาก MCP ในฐานข้อมูลแคช (Grounding Oracle)
python3 harness/cache.py --verified-dekas

# ล้างแคชเฉพาะหมวดหมู่กฎหมาย (Tag-Based Invalidation เช่น หมวดที่ดิน)
python3 harness/cache.py --purge-tag land

# สแกนและให้คะแนนเอกสารบทวิเคราะห์ใน output/ ด้วยระบบประเมินผลอัตโนมัติ
python3 harness/evaluator.py --audit-outputs
# หรือ: make audit
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

<a id="7--การบันทึกไฟล์-file-saving--encoding"></a>
## 💾 7. การบันทึกไฟล์ (File Saving & Encoding)
* หากผู้ใช้ขอให้บันทึกไฟล์ข้อมูล ให้บันทึกไฟล์ไว้ที่โฟลเดอร์ `./output` เสมอ
* เข้ารหัสแบบ **UTF-8 (Encoding: UTF-8)** เสมอ

---

<a id="8-️-ข้อจำกัดความรับผิดชอบ-disclaimer"></a>
## ⚖️ 8. ข้อจำกัดความรับผิดชอบ (Disclaimer)
*คำแนะนำกฎหมายจากโปรแกรมนี้เป็นเพียงข้อมูลเบื้องต้นที่วิเคราะห์ตามหลักตัวบทกฎหมายและเทคโนโลยีปัญญาประดิษฐ์ ไม่สามารถนำมาใช้แทนคำแนะนำของทนายความวิชาชีพหรือที่ปรึกษากฎหมายอย่างเป็นทางการได้*
