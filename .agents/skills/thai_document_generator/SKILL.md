---
name: thai_document_generator
description: "ระบบสร้างและส่งออกเอกสารภาษาไทย (PDF, Word DOCX, OpenDocument ODT) ข้ามระบบปฏิบัติการระดับ Production (Multi-OS Architecture) ป้องกันปัญหาสระลอย/วรรณยุกต์หายด้วย Chromium HarfBuzz Engine, ป้องกัน Tofu Box ด้วย Font Stack สารบรรณ 16pt line-height 1.5, ป้องกันตัวอักษรถ่างใน DOCX และแก้ปัญหา CTL Binding ใน ODT"
category: document-engineering
risk: safe
tags: [thai-document, pdf, docx, odt, saraban, harfbuzz, cross-platform, multi-os, font-shaping]
---

# Thai Document & PDF Generation Skill (คู่มือวิศวกรรมการสร้างเอกสารภาษาไทยระดับ Production)

ทักษะนี้มีไว้สำหรับแปลงผลลัพธ์บทวิเคราะห์ข้อกฎหมายไทย สรุป 10 หัวข้อ หรือเอกสารสัญญาทางกฎหมาย ให้เป็นไฟล์เอกสารระดับมืออาชีพ (PDF, DOCX, ODT) ที่รองรับการเปิดอ่านบนทุกระบบปฏิบัติการ (Windows, macOS, Linux, Docker Containers) 100% ปราศจากข้อผิดพลาดตามคู่มือมาตรฐาน **`software_bugs_reference_guide.md`**

---

## 1. กฎเหล็กป้องกัน 6 Software Bugs ประจำสถาปัตยกรรมเอกสารไทย (The 6 Production Traps)

| Bug ประจำสถาปัตยกรรม | อาการที่ต้องป้องกัน | มาตรการแก้ไขระดับ Production |
| :--- | :--- | :--- |
| **Bug 1: ตัวอักษรสี่เหลี่ยม (Tofu Box)** | การแทรก `\u200b` หรือฟอนต์ไม่มี CMap ทำให้เกิดกล่อง `[ ]` | กำหนด **Font Stack Fallback Hierarchy** ใน CSS:<br>`'TH Sarabun New', 'Sarabun', 'Thonburi', 'Sukhumvit Set', 'Loma', 'Garuda', 'Noto Sans Thai', 'Leelawadee UI', Tahoma, sans-serif` |
| **Bug 2: วรรณยุกต์ชั้นบนสุดหาย / สระลอย** | สระบนและไม้เอก/ไม้โท ซ้อนทับหรือหลุดหาย (เช่น "ที่", "พื้นที่") | ห้ามใช้ FPDF / ReportLab ให้ใช้ **Chromium Headless (`--headless=new`)** ที่มี HarfBuzz + ICU Thai Line-Breaker ในตัว พร้อมใส่ `--no-sandbox` และ `--disable-dev-shm-usage` เสมอ |
| **Bug 3: Subprocess Multi-line Execution Traps** | คำสั่ง `python -c "..."` หลายบรรทัดพังบน Windows/Linux Shell | 1. ใช้ `sys.executable` เสมอ ห้าม hardcode `"python"`<br>2. เขียนโค้ดลง `tempfile.NamedTemporaryFile` ในการรัน |
| **Bug 4: สระบน-ล่างชนกัน / ฟอนต์เล็ก** | ฟอนต์ 11-14pt เล็กเกินไป หรือ 16pt แล้วสระชนกัน | ใช้มาตรฐานระเบียบสารบรรณ: **ฟอนต์เนื้อหา 16pt** และ **`line-height: 1.5`** เสมอ หน้ากระดาษ A4 ขอบ 20mm/15mm |
| **Bug 5: ตัวอักษรถ่างผิดรูปใน Word (`.docx`)** | การใช้ `thaiDistribute` ทำให้ตัวอักษรถูกถ่างช่องไฟจนเละ | **ห้ามใช้ `thaiDistribute`** เด็ดขาด! ให้ใช้ **`WD_ALIGN_PARAGRAPH.LEFT` (ชิดซ้ายปกติ)** ร่วมกับ Line Spacing 1.2–1.25 เท่า และ space_after 4–6 pt |
| **Bug 6: ฟอนต์และขนาดเพี้ยนใน OpenDocument (`.odt`)** | เปิดใน LibreOffice แล้วกลายเป็น Liberation Sans 12pt | ต้องกำหนดคุณสมบัติกลุ่ม **Complex Text Layout (CTL)** ใน `odfpy` คู่กันเสมอ:<br>`fontnamecomplex="TH Sarabun New"`, `fontsizecomplex="16pt"` |

---

## 2. ขั้นตอนการแปลงบทวิเคราะห์กฎหมายเป็น PDF ภาษาไทย (Operational Workflow)

เมื่อผู้ใช้ขอให้บันทึกหรือส่งออกผลลัพธ์เป็นไฟล์ PDF หรือเอกสารทางการ:

1. **ตรวจสอบความพร้อมของระบบ (Environment Pre-flight Check)**:
   ```bash
   python3 harness/document.py --check-env
   ```
   ระบบจะตรวจสอบหา Chromium / Chrome / Edge Binary และฟอนต์ภาษาไทย

2. **แปลง Markdown บทวิเคราะห์เป็น PDF มาตรฐานสารบรรณ**:
   ```bash
   python3 harness/document.py --markdown-to-pdf "./output/บทวิเคราะห์ข้อกฎหมาย_10หัวข้อ.md" "./output/บทวิเคราะห์ข้อกฎหมาย_10หัวข้อ.pdf"
   ```

3. **หรือเรียกใช้ผ่าน Python API ([`harness/document.py`](file:///home/deaw/Projects/thlawdeka/harness/document.py))**:
   ```python
   from harness.document import convert_markdown_to_thai_pdf, convert_html_to_thai_pdf

   # แปลงจากไฟล์ Markdown โดยตรง
   pdf_path = convert_markdown_to_thai_pdf(
       markdown_path_or_content="./output/รายงานคดี.md",
       output_pdf_path="./output/รายงานคดี.pdf",
       doc_title="บทวิเคราะห์ข้อกฎหมายและแนวคำพิพากษาศาลฎีกา"
   )
   ```

---

## 3. มาตรฐาน CSS Print ภาษาไทย (Thai Saraban Print Standard)

```css
@page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
}
body {
    font-family: 'TH Sarabun New', 'Sarabun', 'Thonburi', 'Sukhumvit Set', 
                 'Loma', 'Garuda', 'Noto Sans Thai', 'Leelawadee UI', Tahoma, sans-serif;
    font-size: 16pt;        /* ขนาดมาตรฐานหนังสือราชการไทย */
    line-height: 1.5;       /* ป้องกันสระบน-ล่างชนกัน */
    text-align: justify;
    text-justify: inter-cluster; /* ICU / HarfBuzz word cluster boundary */
}
h1 { font-size: 22pt; font-weight: bold; line-height: 1.25; }
h2 { font-size: 18pt; font-weight: bold; line-height: 1.35; }
h3 { font-size: 16pt; font-weight: bold; }
p { text-indent: 1.25cm; margin-bottom: 8pt; }
```

---

## 4. Production Verification Checklist

ก่อนส่งมอบไฟล์เอกสารแก่ผู้ใช้ ให้ตรวจสอบความถูกต้องตาม Checklist ต่อไปนี้:
- [x] ไฟล์ถูกบันทึกไว้ในไดเรกทอรี `./output/` เสมอ
- [x] การเข้ารหัสไฟล์ข้อความต้นฉบับเป็น `UTF-8`
- [x] ตรวจสอบว่าไม่มีตัวอักษรสี่เหลี่ยม (Tofu Box) ปรากฏในไฟล์ PDF
- [x] สระบนและวรรณยุกต์ซ้อน (เช่น ไม้เอก ไม้โท บน สระอี สระอือ) แสดงผลตรงตำแหน่งแนวดิ่ง ไม่ตกหล่น
- [x] ตัวอักษรภาษาไทยขนาด 16pt อ่านสบายตา และระยะบรรทัดไม่ทับซ้อนกัน
- [x] หากส่งออก Word (`.docx`) ใช้การจัดหน้าแบบชิดซ้าย (Left) ไม่ใช้ `thaiDistribute`
- [x] หากส่งออก OpenDocument (`.odt`) มีการตั้งค่าแอตทริบิวต์กลุ่ม `...complex` (CTL) ครบถ้วน
