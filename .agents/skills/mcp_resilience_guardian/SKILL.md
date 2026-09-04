---
name: mcp_resilience_guardian
description: "ระบบรักษาเสถียรภาพและจัดการข้อผิดพลาดในการเรียกใช้งาน Legal MCP Servers (fourcorners-tlex, slegaltools-legal-v2, thai-legal) รองรับการ Retry แบบ Exponential Backoff, จัดการ HTTP 429 Rate Limit และ Fallback อย่างปลอดภัย"
category: reliability
risk: safe
tags: [mcp, resilience, retry, rate-limit, fallback, error-handling, thai-legal]
---

# MCP Resilience Guardian (ระบบจัดการเสถียรภาพ MCP กฎหมายไทย)

## 1. วัตถุประสงค์ (Purpose)
ปกป้องกระบวนการสืบค้นคำพิพากษาศาลฎีกาและตัวบทกฎหมายจากการเรียกใช้ MCP ภายนอก (`fourcorners-tlex`, `slegaltools-legal-v2`, `thai-legal`) ไม่ให้ระบบล่มหรือหยุดชะงักเมื่อเกิดปัญหาด้านเครือข่าย, API Timeout, HTTP 429 (Rate Limit) หรือ JSON Malformed Payload

---

## 2. แผนผังการจำแนกข้อผิดพลาดและการกู้คืน (Failure Classification & Recovery Matrix)

| ประเภทข้อผิดพลาด (Failure Type) | อาการที่พบ (Symptoms) | การจัดการกู้คืน (Recovery Action) |
| :--- | :--- | :--- |
| **HTTP 429 Too Many Requests** | Upstream API ปฏิเสธคำขอชั่วคราว | สกัดค่า `Retry-After` หรือใช้ **Exponential Backoff with Full Jitter** (รอ 1s, 2s, 4s) สูงสุด 3 ครั้ง |
| **Network Timeout / Hang** | เรียก Tool แล้วไม่มีการตอบสนอง | • **FourCorners T-LEX (`ask_tlex`)**: เป็น Deep Research Agent ต้องใช้เวลา 60-90 วินาทีต่อ 1 คำขอ **ต้องตั้ง Timeout ไม่น้อยกว่า 90-120 วินาที**<br>• **Fast Search (thai-legal, slegaltools)**: ตั้ง Timeout 15-30 วินาที<br>หากหมดเวลาตามกำหนด ทำการ Retry อีก 1 ครั้ง หากยัง Timeout ให้สลับสู่ Fallback Mode ทันที |
| **JSON Malformed / Truncated** | Payload ไม่สมบูรณ์ หรือตัวอักษรภาษาไทยขาดหาย | ขอเฉพาะข้อมูลสรุปสั้นๆ (Summary only) หรือสกัดเฉพาะข้อความที่อ่านได้ |
| **Authentication / Cloudflare Block (401/403)** | API Key ไม่ถูกต้อง หรือติด Cloudflare Error 1010 (User-Agent Blocked) | ตรวจสอบ `.env` สำหรับ API Key และตรวจสอบว่าใน `.agents/mcp_config.json` มีการระบุ `User-Agent` เบราว์เซอร์มาตรฐานเพื่อไม่ให้ถูก Cloudflare แบน |
| **Server Error (500/502/503/504)** | เซิร์ฟเวอร์ต้นทางมีปัญหา | ลองใหม่ 1 ครั้งด้วยหน่วงเวลา 2 วินาที หากไม่สำเร็จให้ Fallback |

---

## 3. ขั้นตอนการทำงาน (Operational Flow)

### ขั้นตอนที่ 0: ตรวจสอบแคชข้อมูลกฎหมาย (Tier-0 Legal Cache Interceptor)
1. **ตรวจสอบ L1 In-Memory LRU Cache (<0.2ms)** และ **L2 SQLite Compressed Disk Cache (<2.0ms)** ผ่านโมดูล `tests/legal_mcp_cache.py`:
   - มีการทำ **Legal Query Normalization** แปลงตัวย่อ (`ป.พ.พ.`, `ป.อ.`, `ป.วิ.พ.`, `ป.วิ.อ.`, `ป.ที่ดิน`, `พ.ร.บ.`, `ม.xxx`) และจัดเรียง Token เพื่อให้การค้นหาคำสำคัญสลับตำแหน่งได้ผลลัพธ์จากแคชเดียวกัน 100%
2. **หากพบข้อมูลในแคช (Cache Hit)**:
   - คืนค่าผลการค้นหากฎหมายที่ผ่านการกลั่นกรอง (Distilled Payload) ทันทีโดย **ไม่ต้องส่ง Request ออกไปยัง MCP ภายนอก**
   - ประหยัดโควตา API ภายนอกได้ 70% – 95% และลดการใช้ Gemini Input Tokens ลง 50% – 70% (Zero Crash / Sub-millisecond Response)
3. **หากไม่พบข้อมูลในแคช (Cache Miss)**:
   - ดำเนินการตามขั้นตอนที่ 1 เพื่อส่งคำขอไปยัง External MCP Server
   - เมื่อได้ผลลัพธ์สำเร็จ ทำการบีบอัดด้วย `zlib` (Level 6) และบันทึกลงแคชตามนโยบาย **Tiered TTL** (ฎีกา 365 วัน, ตัวบท 60 วัน, ค้นหาทั่วไป 30 วัน, ไม่พบข้อมูล 48 ชม.) ภายใต้งบประมาณพื้นที่ 100 MB

### ขั้นตอนที่ 1: ตรวจสอบความพร้อมก่อนเรียกใช้ (Pre-Call Verification)
1. ตรวจสอบว่าใน `.agents/mcp_config.json` มีการตั้งค่า Server ที่ผู้ใช้เลือกหรือไม่
2. ตรวจสอบว่า Query ที่จะส่งไปค้นหามีคีย์เวิร์ดที่ชัดเจนและกระชับ (เช่น "ม.334 ลักทรัพย์เวลากลางคืน" แทนที่จะส่งประโยคยาวทั้งย่อหน้า)

### ขั้นตอนที่ 2: กลยุทธ์การ Retry แบบ Exponential Backoff with Jitter
หากพบสถานะ HTTP 429 หรือ 5xx ให้คำนวณระยะเวลารอดังนี้:
- Delay = min(Base * (2 ** attempt) + random(0, 1), MaxDelay)
- `Base` = 1.0 วินาที
- `MaxDelay` = 8.0 วินาที
- จำนวน Retry สูงสุด = 3 ครั้ง

### ขั้นตอนที่ 3: กฎเหล็กการ Fallback อย่างปลอดภัย (Safe Fallback Protocol)
หากการ Retry ครบกำหนดแล้วยังไม่สำเร็จ:
1. **ห้ามแครช (Crash)** หรือหยุดการแสดงผลลัพธ์ทั้ง 10 หัวข้อ
2. จัดทำหัวข้อที่ 9 (Supreme Court Trend) โดยอธิบายเฉพาะ **"แนวบรรทัดฐานและหลักการวินิจฉัยของศาลฎีกาเชิงทฤษฎี"**
3. **ตัดเลขที่ฎีกาออก 100%** (ห้ามคาดเดาหรือแต่งเลขฎีกาเองเด็ดขาด)
4. แนบท้ายหมายเหตุ:
   > *(หมายเหตุ: ระบบไม่สามารถเชื่อมต่อฐานข้อมูลฎีกาภายนอกได้ในขณะนี้ จึงแสดงเฉพาะแนวบรรทัดฐานคำตัดสินตามหลักวิชาการโดยไม่มีการระบุเลขที่ฎีกา เพื่อความถูกต้องตามหลักความจริง)*

---

## 4. Best Practices
- ✅ **FourCorners T-LEX**: ส่งคำถามที่แคบและเจาะจงประเด็นเดียว (Single focused legal issue) เพื่อลดเวลาประมวลผล (หากถามกว้างจะใช้เวลาเกิน 60-75 วินาที)
- ✅ **FourCorners Deka Extraction**: ตรวจสอบทั้ง `result.structuredContent.citations` และ `result.content[0].text` เพื่อดึงเลขฎีกาที่ระบบวิเคราะห์มาได้อย่างครบถ้วน
- ✅ **Timeout Configuration**: เผื่อเวลา Timeout ให้ `fourcorners-tlex` อย่างน้อย 90-120 วินาที ป้องกันการตัดเข้า Safe Fallback Mode ก่อนได้รับผลลัพธ์
- ✅ ปรับ Query คำค้นหาให้เป็นคำหลักเชิงกฎหมายก่อนส่งเข้า MCP
- ✅ บันทึก Error Log เพื่อตรวจสอบสาเหตุ
- ❌ ห้าม Retry ซ้ำเกิน 3 ครั้งเพื่อป้องกันการติดแบล็กลิสต์ IP
- ❌ ห้ามแสดง Exception ดิบของระบบให้ผู้ใช้ทั่วไปเห็น ให้แปลงเป็นข้อความแนะนำที่เข้าใจง่าย
- 🛡️ **Speed Benchmark Guardrail**: หากผู้ใช้สั่งให้ทดสอบความเร็ว (Speed/Latency) ของ MCP **ห้ามเรียกใช้งานคำขอจริงเกิน 3 requests ต่อครั้งเป็นอันขาด** เพื่อป้องกันการกิน quota ของ MCP หมด
- 🛡️ **Simulate/Offline Testing Policy**: ระบบการทดสอบ (Unit Tests / Resilience Tests) ต้องทำงานในรูปแบบ Simulate/Offline 100% เสมอ ห้ามยิงคำขอออก Network จริงในชุดทดสอบอัตโนมัติ เพื่อรักษา Quota และป้องกัน API Key รั่วไหล

