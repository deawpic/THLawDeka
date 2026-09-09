# -*- coding: utf-8 -*-
"""
Unit & Integration Tests for Thai Document & PDF Generator
Validates compliance with Multi-OS Production Standards:
- Bug 1: Tofu Box Prevention & Universal Font Stack
- Bug 2: HarfBuzz Tone Marks & Docker Shm Safety Flags
- Bug 3: Safe Subprocess Multi-line Execution
- Bug 4: Thai Official Saraban Standard (16pt, line-height 1.5)
- Bug 5: Word DOCX Alignment Safety (Blocks thaiDistribute)
- Bug 6: OpenDocument ODT CTL Font Binding
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from harness.document import (
    find_system_chromium_binary,
    get_thai_saraban_css,
    markdown_to_thai_html,
    convert_markdown_to_thai_html,
    convert_html_to_thai_pdf,
    convert_markdown_to_thai_pdf,
    convert_markdown_to_docx,
    convert_markdown_to_odt,
    export_all_formats,
    safe_run_python_script,
    validate_docx_alignment,
    build_odt_thai_style_properties,
    check_system_environment,
    UNIVERSAL_THAI_FONT_STACK,
    DOCX_AVAILABLE,
    ODF_AVAILABLE,
)

class TestThaiDocumentGenerator(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="thlawdeka_doc_test_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bug1_universal_thai_font_stack_covers_all_os(self):
        """Bug 1: ตรวจสอบว่า Font Stack มีฟอนต์ครอบคลุมทั้ง Windows, macOS, Linux"""
        stack = UNIVERSAL_THAI_FONT_STACK.lower()
        # Windows Fonts
        self.assertIn("tahoma", stack)
        self.assertIn("leelawadee", stack)
        # macOS Apple Fonts
        self.assertIn("thonburi", stack)
        self.assertIn("sukhumvit", stack)
        # Linux / Noto Fonts
        self.assertIn("noto sans thai", stack)
        self.assertIn("sarabun", stack)

    def test_bug2_saraban_css_and_line_breaker(self):
        """Bug 2 & 4: ตรวจสอบ CSS Print มาตรฐานสารบรรณ 16pt, line-height 1.5 และ A4 margin"""
        css = get_thai_saraban_css()
        self.assertIn("size: A4", css)
        self.assertIn("margin: 20mm 15mm 20mm 15mm", css)
        self.assertIn("font-size: 16pt", css)
        self.assertIn("line-height: 1.5", css)
        self.assertIn("text-justify: inter-cluster", css)

    def test_bug3_safe_subprocess_execution(self):
        """Bug 3: ตรวจสอบการรัน Python ข้าม OS ปลอดภัยด้วย sys.executable และ tempfile"""
        code = (
            "import sys\n"
            "print('OK:' + sys.version_info.__class__.__name__)\n"
        )
        res = safe_run_python_script(code)
        self.assertEqual(res.returncode, 0)
        self.assertIn("OK:", res.stdout)

    def test_bug5_docx_alignment_blocks_thai_distribute(self):
        """Bug 5: ตรวจสอบว่าระบบเปลี่ยน thaiDistribute เป็น left อัตโนมัติ ป้องกันอักษรถ่าง"""
        safe_align1 = validate_docx_alignment("thaiDistribute")
        self.assertEqual(safe_align1, "left")

        safe_align2 = validate_docx_alignment("distribute")
        self.assertEqual(safe_align2, "left")

        safe_align3 = validate_docx_alignment("left")
        self.assertEqual(safe_align3, "left")

    def test_bug6_odt_ctl_style_properties(self):
        """Bug 6: ตรวจสอบว่าสร้างคุณสมบัติ Complex Text Layout (CTL) คู่กับ Western เสมอ"""
        props = build_odt_thai_style_properties(font_name="TH Sarabun New", font_size_pt=16)
        self.assertEqual(props["fontname"], "TH Sarabun New")
        self.assertEqual(props["fontsize"], "16pt")
        # CTL properties
        self.assertIn("fontnamecomplex", props)
        self.assertIn("fontsizecomplex", props)
        self.assertEqual(props["fontnamecomplex"], "TH Sarabun New")
        self.assertEqual(props["fontsizecomplex"], "16pt")

    def test_markdown_to_thai_html_structure(self):
        """ทดสอบการจัดโครงสร้าง HTML ตามรูปแบบสารบรรณ"""
        sample_md = (
            "# บทวิเคราะห์ข้อกฎหมายคดีที่ดิน\n\n"
            "## 1. บทสรุปของสถานการณ์\n"
            "ข้อพิพาทเกี่ยวกับที่ดิน ส.ค.1 ตามคำพิพากษาศาลฎีกาที่ 15216/2551\n\n"
            "## 3. รายการข้อกฎหมาย\n"
            "- ป.พ.พ. มาตรา 1378 การส่งมอบการครอบครอง\n"
        )
        html_out = markdown_to_thai_html(sample_md, title="คดีที่ดิน")
        self.assertIn("<h1 class='doc-title'>บทวิเคราะห์ข้อกฎหมายคดีที่ดิน</h1>", html_out)
        self.assertIn("<h2 class='section-title'>1. บทสรุปของสถานการณ์</h2>", html_out)
        self.assertIn("15216/2551", html_out)
        self.assertIn("1378", html_out)
        self.assertIn("TH Sarabun New", html_out)

    def test_check_system_environment(self):
        """ตรวจสอบความพร้อมของระบบสภาพแวดล้อม"""
        env = check_system_environment()
        self.assertIn("platform", env)
        self.assertIn("chromium_available", env)
        self.assertIn("font_stack", env)
        self.assertIn("saraban_standard", env)

    def test_actual_pdf_generation(self):
        """ทดสอบการสร้างไฟล์ PDF จริงผ่าน Chromium Headless"""
        env = check_system_environment()
        if not env["chromium_available"]:
            self.skipTest("Chromium not installed in test environment")

        output_pdf = os.path.join(self.temp_dir, "test_output.pdf")
        html_content = "<h1>ทดสอบเอกสารภาษาไทย</h1><p>คำพิพากษาศาลฎีกาที่ 1234/2565 ป.อ. ม.334</p>"
        res_path = convert_html_to_thai_pdf(html_content, output_pdf)

        self.assertTrue(os.path.exists(res_path))
        self.assertGreater(os.path.getsize(res_path), 1000)

    def test_markdown_to_thai_html_tables_and_links(self):
        """ทดสอบการแปลง Table, ลิงก์ และ Ordered List ใน Markdown to HTML"""
        sample_md = (
            "# รายงานกฎหมาย\n\n"
            "## สารบัญ\n"
            "1. [บทสรุป](#summary)\n"
            "2. [ข้อกฎหมาย](#statutes)\n\n"
            "| ลำดับ | ประเด็น | ผลทางกฎหมาย |\n"
            "| :---: | :--- | :---: |\n"
            "| 1 | การสมรส | โมฆะ |\n"
        )
        html_out = markdown_to_thai_html(sample_md, title="รายงาน")
        self.assertIn("<ol>", html_out)
        self.assertIn("<a href=\"#summary\">บทสรุป</a>", html_out)
        self.assertIn("<div class='table-container'><table>", html_out)
        self.assertIn("<th style='text-align: center;'>ลำดับ</th>", html_out)
        self.assertIn("<td style='text-align: center;'>1</td>", html_out)
        self.assertIn("<td style='text-align: left;'>การสมรส</td>", html_out)

    def test_convert_markdown_saves_companion_html(self):
        """ทดสอบว่า convert_markdown_to_thai_pdf สร้างไฟล์ companion .html คู่กันอย่างถูกต้อง"""
        env = check_system_environment()
        if not env["chromium_available"]:
            self.skipTest("Chromium not installed in test environment")

        md_file = os.path.join(self.temp_dir, "test_doc.md")
        pdf_file = os.path.join(self.temp_dir, "test_doc.pdf")
        html_file = os.path.join(self.temp_dir, "test_doc.html")

        Path(md_file).write_text("# หัวข้อทดสอบ\n\nข้อความเนื้อหา", encoding="utf-8")
        convert_markdown_to_thai_pdf(md_file, pdf_file, save_html=True)

        self.assertTrue(os.path.exists(pdf_file), "PDF file must exist")
        self.assertTrue(os.path.exists(html_file), "Companion HTML file must exist")
        self.assertIn("หัวข้อทดสอบ", Path(html_file).read_text(encoding="utf-8"))

    def test_convert_markdown_to_docx(self):
        """ทดสอบการสร้างไฟล์ Word (.docx) ตามมาตรฐานสารบรรณ 16pt และบล็อก thaiDistribute"""
        if not DOCX_AVAILABLE:
            self.skipTest("python-docx is not installed in test environment")

        md_content = (
            "# รายงานผลการวิเคราะห์กฎหมาย\n\n"
            "## 1. ข้อเท็จจริง\n"
            "ทดสอบข้อความภาษาไทย **ตัวหนา** และ *ตัวเอียง* รวมทั้ง [คำพิพากษาศาลฎีกาที่ 15216/2551]\n\n"
            "| ลำดับ | รายการ | ผลลัพธ์ |\n"
            "| :---: | :--- | :---: |\n"
            "| 1 | การตรวจสอบ | สมบูรณ์ |\n\n"
            "- รายการย่อยที่หนึ่ง\n"
            "- รายการย่อยที่สอง\n"
        )
        docx_file = os.path.join(self.temp_dir, "test_output.docx")
        out_path = convert_markdown_to_docx(md_content, docx_file, doc_title="รายงานผลการวิเคราะห์กฎหมาย")

        self.assertTrue(os.path.exists(out_path), "DOCX file must exist")
        self.assertGreater(os.path.getsize(out_path), 1000, "DOCX file size must be > 1000 bytes")

        # Verify paragraph alignment does not use thaiDistribute (Bug 5)
        import docx
        doc = docx.Document(str(out_path))
        for p in doc.paragraphs:
            # alignment should be LEFT or None (default left), never DISTRIBUTE
            self.assertNotEqual(p.alignment, docx.enum.text.WD_ALIGN_PARAGRAPH.DISTRIBUTE)

    def test_convert_markdown_to_odt(self):
        """ทดสอบการสร้างไฟล์ OpenDocument (.odt) พร้อมคุณสมบัติ CTL"""
        if not ODF_AVAILABLE:
            self.skipTest("odfpy is not installed in test environment")

        md_content = (
            "# รายงานผลการวิเคราะห์กฎหมาย OpenDocument\n\n"
            "## 1. สรุปประเด็น\n"
            "การทดสอบการส่งออก ODT ตามระเบียบงานสารบรรณ\n\n"
            "| หัวข้อ | รายละเอียด |\n"
            "| :--- | :--- |\n"
            "| ข้อ 1 | ข้อเท็จจริง |\n"
        )
        odt_file = os.path.join(self.temp_dir, "test_output.odt")
        out_path = convert_markdown_to_odt(md_content, odt_file, doc_title="รายงาน ODT")

        self.assertTrue(os.path.exists(out_path), "ODT file must exist")
        self.assertGreater(os.path.getsize(out_path), 1000, "ODT file size must be > 1000 bytes")

    def test_export_all_formats(self):
        """ทดสอบการส่งออกครบทุกฟอร์แมตในคำสั่งเดียว (HTML, PDF, DOCX, ODT)"""
        md_file = os.path.join(self.temp_dir, "multi_export.md")
        base_output = os.path.join(self.temp_dir, "multi_export")
        Path(md_file).write_text("# รายงานครบฟอร์แมต\n\nทดสอบเนื้อหา", encoding="utf-8")

        results = export_all_formats(md_file, base_output, doc_title="รายงานครบฟอร์แมต")

        self.assertIn("html", results)
        self.assertTrue(os.path.exists(results["html"]))

        if DOCX_AVAILABLE:
            self.assertIn("docx", results)
            self.assertTrue(os.path.exists(results["docx"]))

        if ODF_AVAILABLE:
            self.assertIn("odt", results)
            self.assertTrue(os.path.exists(results["odt"]))

        env = check_system_environment()
        if env["chromium_available"]:
            self.assertIn("pdf", results)
            self.assertTrue(os.path.exists(results["pdf"]))

if __name__ == "__main__":
    unittest.main()

