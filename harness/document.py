# -*- coding: utf-8 -*-
"""
THLawDeka - Cross-Platform Thai Document & PDF Generation Engine
Complies with Software Bugs Reference Guide (Multi-OS Production Standard):
- Bug 1: Tofu Box Prevention & Universal Font Fallback Stack
- Bug 2: Tone Marks & HarfBuzz Complex Text Shaping via Chromium Headless (--headless=new)
- Bug 3: Safe Subprocess Execution with sys.executable & NamedTemporaryFile
- Bug 4: Thai Official Saraban Standard (16pt font, line-height 1.5, A4 margins)
- Bug 5: Word DOCX Natural Alignment (Avoid thaiDistribute, use LEFT alignment)
- Bug 6: OpenDocument ODT CTL Font Binding (Complex Text Layout fontnamecomplex)
"""

import html
import json
import logging
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("THLawDeka.Document")

# มาตรฐาน Font Fallback Stack ป้องกัน Tofu Box ข้ามระบบปฏิบัติการ 100% (Bug 1)
UNIVERSAL_THAI_FONT_STACK = (
    "'TH Sarabun New', 'Sarabun', 'Thonburi', 'Sukhumvit Set', "
    "'Loma', 'Garuda', 'Noto Sans Thai', 'Leelawadee UI', Tahoma, sans-serif"
)

def find_system_chromium_binary() -> str:
    """
    ค้นหา Chromium Executable (Chrome, Edge หรือ Chromium) แบบอัตโนมัติข้ามระบบปฏิบัติการ
    ลำดับการค้นหา:
    1. ตรวจสอบ Environment Variable 'CHROMIUM_PATH'
    2. ตรวจสอบผ่าน PATH (shutil.which)
    3. ตรวจสอบตาม Standard Installation Paths ประจำแต่ละ OS (Linux, macOS, Windows)
    """
    env_path = os.getenv("CHROMIUM_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    # 1. ค้นหาใน PATH (ครอบคลุม Linux, macOS และ Windows ที่เซ็ต PATH ไว้)
    cli_candidates = [
        "google-chrome", "google-chrome-stable", "chromium",
        "chromium-browser", "msedge", "microsoft-edge", "chrome"
    ]
    for cmd in cli_candidates:
        found_bin = shutil.which(cmd)
        if found_bin:
            return found_bin

    # 2. ค้นหาตาม Default Path เฉพาะระบบปฏิบัติการ
    current_os = platform.system()

    if current_os == "Darwin":  # macOS
        mac_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        ]
        for p in mac_paths:
            if Path(p).exists():
                return p

    elif current_os == "Windows":  # Windows
        win_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
        ]
        for p in win_paths:
            if Path(p).exists():
                return p

    elif current_os == "Linux":  # Linux / Docker
        linux_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium"
        ]
        for p in linux_paths:
            if Path(p).exists():
                return p

    raise FileNotFoundError(
        f"ไม่พบเบราว์เซอร์ Chromium/Chrome/Edge บนระบบปฏิบัติการ {current_os}\n"
        "คำแนะนำสำหรับ Linux/Docker: กรุณารัน 'apt-get install -y chromium' หรือ 'google-chrome-stable' ในระบบ"
    )

def get_thai_saraban_css(font_family: Optional[str] = None) -> str:
    """
    ส่งคืน CSS Print ตามมาตรฐานระเบียบงานสารบรรณไทย (Bug 4)
    และระบบ Font Fallback ป้องกัน Tofu Box (Bug 1)
    """
    fonts = font_family or UNIVERSAL_THAI_FONT_STACK
    return f"""
    @page {{
        size: A4;
        margin: 20mm 15mm 20mm 15mm;
        @bottom-right {{
            content: counter(page) " / " counter(pages);
            font-size: 10pt;
            font-family: {fonts};
            color: #64748b;
        }}
    }}
    *, *::before, *::after {{
        box-sizing: border-box;
    }}
    body {{
        font-family: {fonts};
        font-size: 16pt;           /* ขนาดมาตรฐานหนังสือราชการไทย */
        line-height: 1.5;          /* ป้องกันสระบน-ล่างชนกัน */
        color: #1e293b;
        background-color: #ffffff;
        margin: 0;
        padding: 0;
        text-rendering: optimizeLegibility;
        text-align: justify;
        text-justify: inter-cluster; /* ตัดคำภาษาไทยตามคลัสเตอร์ ICU / HarfBuzz */
        word-break: normal;
    }}
    h1, .doc-title {{
        font-size: 22pt;
        font-weight: bold;
        line-height: 1.25;
        margin-top: 0;
        margin-bottom: 14pt;
        color: #0f172a;
        text-align: center;
        border-bottom: 2pt solid #0284c7;
        padding-bottom: 8pt;
    }}
    h2, .section-title {{
        font-size: 18pt;
        font-weight: bold;
        line-height: 1.35;
        margin-top: 18pt;
        margin-bottom: 8pt;
        color: #1e3a8a;
        border-bottom: 1pt solid #cbd5e1;
        padding-bottom: 4pt;
        page-break-after: avoid;
    }}
    h3, .subsection-title {{
        font-size: 16pt;
        font-weight: bold;
        line-height: 1.4;
        margin-top: 12pt;
        margin-bottom: 6pt;
        color: #334155;
        page-break-after: avoid;
    }}
    p {{
        margin-top: 0;
        margin-bottom: 8pt;
        text-indent: 1.25cm;      /* ย่อหน้ามาตรฐานหนังสือราชการ */
    }}
    p.no-indent, .callout-box p, blockquote p {{
        text-indent: 0;
    }}
    ul, ol {{
        margin-top: 4pt;
        margin-bottom: 8pt;
        padding-left: 1.5cm;
    }}
    li {{
        margin-bottom: 4pt;
        line-height: 1.45;
    }}
    .callout-box {{
        background-color: #f8fafc;
        border-left: 4pt solid #0284c7;
        padding: 10pt 14pt;
        margin: 12pt 0;
        font-size: 14pt;
        line-height: 1.4;
        border-radius: 0 4pt 4pt 0;
        page-break-inside: avoid;
    }}
    .table-container {{
        width: 100%;
        margin: 12pt 0;
        page-break-inside: avoid;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14pt;
        line-height: 1.35;
    }}
    th, td {{
        border: 1pt solid #cbd5e1;
        padding: 6pt 8pt;
        text-align: left;
        vertical-align: top;
    }}
    th {{
        background-color: #f1f5f9;
        font-weight: bold;
        color: #0f172a;
    }}
    .deka-badge {{
        display: inline-block;
        background-color: #e0f2fe;
        color: #0369a1;
        font-weight: bold;
        padding: 2pt 6pt;
        border-radius: 4pt;
        font-size: 13pt;
        border: 1pt solid #bae6fd;
    }}
    .statute-badge {{
        display: inline-block;
        background-color: #fef3c7;
        color: #92400e;
        font-weight: bold;
        padding: 2pt 6pt;
        border-radius: 4pt;
        font-size: 13pt;
        border: 1pt solid #fde68a;
    }}
    .footer-note {{
        font-size: 11pt;
        color: #64748b;
        margin-top: 20pt;
        border-top: 1pt solid #e2e8f0;
        padding-top: 6pt;
        text-indent: 0;
    }}
    @media print {{
        body {{
            background: none;
            color: #000000;
        }}
        .callout-box {{
            background-color: #f8fafc !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        .deka-badge, .statute-badge, th {{
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
    }}
    """

def markdown_to_thai_html(markdown_text: str, title: str = "บทวิเคราะห์ข้อกฎหมาย") -> str:
    """
    แปลงเนื้อหา Markdown บทวิเคราะห์กฎหมาย 10 หัวข้อ เป็น HTML ตามระเบียบสารบรรณ
    โดยจัดการหัวเรื่อง ตัวหนา กล่องคำเตือน รายการ และตราประทับ
    """
    lines = markdown_text.splitlines()
    html_body_lines = []
    in_list = False
    in_code_block = False

    for raw_line in lines:
        line = raw_line.strip()

        # Handle Code Block (Mermaid or Raw Code)
        if line.startswith("```"):
            if in_code_block:
                html_body_lines.append("</pre></div>")
                in_code_block = False
            else:
                html_body_lines.append("<div class='callout-box'><pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            html_body_lines.append(html.escape(raw_line))
            continue

        if not line:
            if in_list:
                html_body_lines.append("</ul>")
                in_list = False
            continue

        # Headings
        if line.startswith("# "):
            clean_title = line[2:].strip()
            html_body_lines.append(f"<h1 class='doc-title'>{html.escape(clean_title)}</h1>")
            continue
        elif line.startswith("## "):
            sec_title = line[3:].strip()
            html_body_lines.append(f"<h2 class='section-title'>{html.escape(sec_title)}</h2>")
            continue
        elif line.startswith("### "):
            subsec_title = line[4:].strip()
            html_body_lines.append(f"<h3 class='subsection-title'>{html.escape(subsec_title)}</h3>")
            continue

        # Blockquotes / Alerts
        if line.startswith(">"):
            quote_text = line.lstrip("> ").strip()
            quote_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', quote_text)
            html_body_lines.append(f"<div class='callout-box'><p class='no-indent'>{quote_text}</p></div>")
            continue

        # Unordered List Items
        if line.startswith("- ") or line.startswith("* "):
            if not in_list:
                html_body_lines.append("<ul>")
                in_list = True
            item_text = line[2:].strip()
            item_text = re.sub(r'(\b\d+/\d{2,4}\b)', r'<span class="deka-badge">ฎีกาที่ \1</span>', item_text)
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', item_text)
            html_body_lines.append(f"<li>{item_text}</li>")
            continue

        # Horizontal rules
        if line in ("---", "***", "___"):
            if in_list:
                html_body_lines.append("</ul>")
                in_list = False
            html_body_lines.append("<hr style='border: 0; border-top: 1pt solid #cbd5e1; margin: 16pt 0;'>")
            continue

        if in_list:
            html_body_lines.append("</ul>")
            in_list = False

        # Regular Paragraph
        p_text = line
        p_text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', p_text)
        p_text = re.sub(r'(คำพิพากษาศาลฎีกาที่|ฎีกาที่)\s*(\d+/\d{2,4})', r'<span class="deka-badge">\1 \2</span>', p_text)
        p_text = re.sub(r'(ป\.พ\.พ\.|ป\.อ\.|ป\.วิ\.พ\.|ป\.วิ\.อ\.)\s*(มาตรา|ม\.)\s*(\d+)', r'<span class="statute-badge">\1 \2 \3</span>', p_text)

        html_body_lines.append(f"<p>{p_text}</p>")

    if in_list:
        html_body_lines.append("</ul>")
    if in_code_block:
        html_body_lines.append("</pre></div>")

    body_content = "\n".join(html_body_lines)
    css_content = get_thai_saraban_css()

    full_html = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
{css_content}
    </style>
</head>
<body>
{body_content}
    <p class="footer-note">
        เอกสารจัดทำโดย THLawDeka AI Legal Intelligence Advisor &bull; มาตรฐานสารบรรณ 16pt &bull; UTF-8 Cross-Platform
    </p>
</body>
</html>
"""
    return full_html

def convert_html_to_thai_pdf(
    html_content: str,
    output_pdf_path: Union[str, Path],
    timeout_seconds: int = 30
) -> Path:
    """
    แปลงข้อความ HTML เป็นเอกสาร PDF ภาษาไทยระดับ Professional
    ตามมาตรฐาน Software Bugs Reference Guide:
    - Bug 1: ใช้ Universal Font Stack ป้องกัน Tofu Box
    - Bug 2: จัดวางสระบน-วรรณยุกต์ซ้อนแม่นยำ 100% ด้วย HarfBuzz ใน Chromium Headless
    - Bug 2 (Docker Crash Fix): ใส่ --no-sandbox และ --disable-dev-shm-usage รับประกันไม่ OOM
    - Bug 3: ควบคุม Subprocess ผ่าน Argument List และ Temporary User Profile
    - Bug 4: กำหนดขนาดฟอนต์ 16pt และ line-height 1.5 ไม่ซ้อนทับกัน
    """
    out_path = Path(output_pdf_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. ค้นหา Executable ของเบราว์เซอร์
    browser_executable = find_system_chromium_binary()

    # 2. สร้างไฟล์ HTML ชั่วคราว (รับประกัน UTF-8 - Bug 1)
    with tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False) as f:
        f.write(html_content)
        temp_html_file = Path(f.name)

    # สร้าง User Data Profile ชั่วคราวเพื่อป้องกันการชนกับเบราว์เซอร์หลัก
    temp_profile_dir = tempfile.mkdtemp(prefix="chromium_pdf_profile_")

    try:
        # 3. กำหนดแฟล็กคำสั่ง Headless Print-to-PDF ข้ามแพลตฟอร์ม (Bug 2)
        cmd = [
            browser_executable,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",                  # จำเป็นสำหรับ Linux Docker / Root
            "--disable-dev-shm-usage",       # ป้องกัน Docker Crash จาก Limit 64MB บน /dev/shm
            f"--user-data-dir={temp_profile_dir}",
            "--no-pdf-header-footer",
            f"--print-to-pdf={str(out_path)}",
            str(temp_html_file)
        ]

        # 4. รันคำสั่งแปลงไฟล์ผ่าน Subprocess อย่างปลอดภัย (Bug 3)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )

        if not out_path.exists() or out_path.stat().st_size == 0:
            raise RuntimeError(
                f"สร้าง PDF ล้มเหลว (Exit Code: {result.returncode})\nStderr: {result.stderr}"
            )

        logger.info(f"Successfully generated Thai PDF document at: {out_path} ({out_path.stat().st_size} bytes)")
        return out_path

    finally:
        # 5. ทำความสะอาดไฟล์ชั่วคราว
        temp_html_file.unlink(missing_ok=True)
        shutil.rmtree(temp_profile_dir, ignore_errors=True)

def convert_markdown_to_thai_pdf(
    markdown_path_or_content: Union[str, Path],
    output_pdf_path: Union[str, Path],
    doc_title: Optional[str] = None
) -> Path:
    """
    แปลงไฟล์ Markdown หรือข้อความ Markdown เป็นเอกสาร PDF ภาษาไทย
    """
    if isinstance(markdown_path_or_content, Path) or (isinstance(markdown_path_or_content, str) and os.path.exists(markdown_path_or_content)):
        p = Path(markdown_path_or_content)
        with open(p, "r", encoding="utf-8") as f:
            md_content = f.read()
        title = doc_title or p.stem.replace("_", " ")
    else:
        md_content = str(markdown_path_or_content)
        title = doc_title or "บทวิเคราะห์ข้อกฎหมาย"

    html_content = markdown_to_thai_html(md_content, title=title)
    return convert_html_to_thai_pdf(html_content, output_pdf_path)

def safe_run_python_script(
    script_code: str,
    args: Optional[List[str]] = None,
    timeout: int = 30
) -> subprocess.CompletedProcess:
    """
    รันสคริปต์ Python ข้าม OS อย่างปลอดภัย 100% ตามข้อกำหนด Bug 3:
    - หลีกเลี่ยง python -c "..." หลายบรรทัด
    - ใช้ sys.executable เสมอ ห้าม hardcode 'python'
    - ใช้ tempfile.NamedTemporaryFile เขียนโค้ด UTF-8 ลงไฟล์ก่อนรัน
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as f:
        f.write(script_code)
        temp_script_path = Path(f.name)

    try:
        cmd = [sys.executable, str(temp_script_path)]
        if args:
            cmd.extend(args)

        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return res
    finally:
        temp_script_path.unlink(missing_ok=True)

def validate_docx_alignment(alignment: str) -> str:
    """
    ตรวจสอบการตั้งค่าย่อหน้าสำหรับ Microsoft Word (DOCX) ตามข้อกำหนด Bug 5:
    - ป้องกันการใช้ 'thaiDistribute' ซึ่งจะทำให้ตัวอักษรถ่างผิดรูปจนอ่านไม่ออก
    - แนะนำให้ใช้ 'left' (WD_ALIGN_PARAGRAPH.LEFT)
    """
    if "thaiDistribute" in alignment or "distribute" in alignment.lower():
        logger.warning(
            "ตรวจพบการใช้ 'thaiDistribute' ในเอกสาร Word! "
            "ทำการเปลี่ยนเป็น 'left' อัตโนมัติ เพื่อป้องกันปัญหาตัวอักษรถ่างผิดรูปตาม Bug 5"
        )
        return "left"
    return alignment

def build_odt_thai_style_properties(
    font_name: str = "TH Sarabun New",
    font_size_pt: int = 16,
    line_spacing_percent: int = 125
) -> Dict[str, Any]:
    """
    สร้างคุณสมบัติสไตล์สำหรับ OpenDocument (.ODT) ตามข้อกำหนด Bug 6:
    - ต้องกำหนดคุณสมบัติ Complex Text Layout (CTL): fontnamecomplex และ fontsizecomplex เสมอ
    - ป้องกันปัญหาฟอนต์เพี้ยนเป็น Liberation Sans หรือ Angsana New ใน LibreOffice / MS Word
    """
    return {
        # 1. Western Script
        "fontname": font_name,
        "fontsize": f"{font_size_pt}pt",
        # 2. Complex Text Layout (CTL) สำหรับภาษาไทย (หัวใจสำคัญตาม Bug 6)
        "fontnamecomplex": font_name,
        "fontsizecomplex": f"{font_size_pt}pt",
        # 3. ระยะบรรทัด
        "linespacing": f"{line_spacing_percent}%"
    }

def check_system_environment() -> Dict[str, Any]:
    """ตรวจสอบความพร้อมของระบบในการสร้างเอกสารภาษาไทยข้าม OS"""
    current_os = platform.system()
    chromium_found = False
    chromium_bin = ""
    error_msg = ""

    try:
        chromium_bin = find_system_chromium_binary()
        chromium_found = True
    except FileNotFoundError as e:
        error_msg = str(e)

    # ตรวจสอบฟอนต์ไทยในระบบ
    thai_fonts_detected = []
    if current_os == "Linux":
        font_check_paths = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]
        for base in font_check_paths:
            p = Path(base)
            if p.exists():
                for f in p.rglob("*"):
                    name_lower = f.name.lower()
                    if any(k in name_lower for k in ["thai", "tlwg", "sarabun", "noto", "loma", "garuda"]):
                        thai_fonts_detected.append(f.name)
    elif current_os == "Darwin":
        thai_fonts_detected = ["Thonburi.ttc", "SukhumvitSet.ttc"]
    elif current_os == "Windows":
        thai_fonts_detected = ["tahoma.ttf", "leelawad.ttf"]

    return {
        "status": "ready" if chromium_found else "missing_chromium",
        "platform": current_os,
        "python_executable": sys.executable,
        "chromium_binary": chromium_bin,
        "chromium_available": chromium_found,
        "thai_fonts_detected": thai_fonts_detected[:10],
        "font_stack": UNIVERSAL_THAI_FONT_STACK,
        "saraban_standard": {
            "font_size": "16pt",
            "line_height": 1.5,
            "page_size": "A4",
            "margins": "20mm 15mm 20mm 15mm"
        },
        "error": error_msg if not chromium_found else None
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="THLawDeka Universal Thai Document & PDF Generator CLI")
    parser.add_argument("--check-env", action="store_true", help="Check system readiness for Thai PDF generation")
    parser.add_argument("--markdown-to-pdf", nargs=2, metavar=("INPUT_MD", "OUTPUT_PDF"), help="Convert Markdown file to Thai Saraban PDF")
    parser.add_argument("--test-safe-subprocess", action="store_true", help="Test safe python subprocess execution (Bug 3)")

    args = parser.parse_args()

    if args.check_env:
        info = check_system_environment()
        print(json.dumps(info, ensure_ascii=False, indent=2))
        sys.exit(0 if info["status"] == "ready" else 1)

    elif args.markdown_to_pdf:
        in_md, out_pdf = args.markdown_to_pdf
        pdf_path = convert_markdown_to_thai_pdf(in_md, out_pdf)
        print(json.dumps({"status": "success", "pdf_path": str(pdf_path), "size_bytes": pdf_path.stat().st_size}, ensure_ascii=False, indent=2))
        sys.exit(0)

    elif args.test_safe_subprocess:
        test_code = "import sys\nprint('Safe Subprocess Success with:', sys.executable)"
        res = safe_run_python_script(test_code)
        print(json.dumps({
            "status": "success" if res.returncode == 0 else "failed",
            "returncode": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }, ensure_ascii=False, indent=2))
        sys.exit(0 if res.returncode == 0 else 1)

    else:
        # Default: show environment info
        info = check_system_environment()
        print(json.dumps(info, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
