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
| **Network Timeout / Hang** | เรียก Tool แล้วไม่มีการตอบสนองเกิน 15 วินาที | ทำการ Retry อีก 1 ครั้ง หากยัง Timeout ให้สลับสู่ Fallback Mode ทันที |
| **JSON Malformed / Truncated** | Payload ไม่สมบูรณ์ หรือตัวอักษรภาษาไทยขาดหาย | ขอเฉพาะข้อมูลสรุปสั้นๆ (Summary only) หรือสกัดเฉพาะข้อความที่อ่านได้ |
| **Authentication Error (401/403)** | API Key ใน `.env` ไม่ถูกต้องหรือหมดอายุ | แจ้งเตือนผู้ใช้ให้รัน skill `api_key_setup` และดำเนินกระบวนการต่อในโหมด Fallback |
| **Server Error (500/502/503/504)** | เซิร์ฟเวอร์ต้นทางมีปัญหา | ลองใหม่ 1 ครั้งด้วยหน่วงเวลา 2 วินาที หากไม่สำเร็จให้ Fallback |

---

## 3. ขั้นตอนการทำงาน (Operational Flow)

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
- ✅ ปรับ Query คำค้นหาให้เป็นคำหลักเชิงกฎหมายก่อนส่งเข้า MCP
- ✅ บันทึก Error Log เพื่อตรวจสอบสาเหตุ
- ❌ ห้าม Retry ซ้ำเกิน 3 ครั้งเพื่อป้องกันการติดแบล็กลิสต์ IP
- ❌ ห้ามแสดง Exception ดิบของระบบให้ผู้ใช้ทั่วไปเห็น ให้แปลงเป็นข้อความแนะนำที่เข้าใจง่าย
