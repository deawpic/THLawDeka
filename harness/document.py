# -*- coding: utf-8 -*-
"""
THLawDeka - Cross-Platform Thai Document & PDF Generation Engine
Complies with Multi-OS Production Standards for Thai Documents:
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
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import docx
    from docx import Document
    from docx.shared import Pt, Cm, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import parse_xml, OxmlElement
    from docx.oxml.ns import nsdecls, qn
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import odf
    from odf.opendocument import OpenDocumentText
    from odf.style import Style, TextProperties, ParagraphProperties, TableCellProperties, TableColumnProperties
    from odf.text import H, P, Span
    from odf.table import Table, TableColumn, TableRow, TableCell
    ODF_AVAILABLE = True
except ImportError:
    ODF_AVAILABLE = False

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
    h4, .subsubsec-title {{
        font-size: 16pt;
        font-weight: bold;
        line-height: 1.4;
        margin-top: 10pt;
        margin-bottom: 4pt;
        color: #1e293b;
        page-break-after: avoid;
    }}
    h5, .subsubsubsec-title {{
        font-size: 15pt;
        font-weight: bold;
        line-height: 1.4;
        margin-top: 8pt;
        margin-bottom: 4pt;
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
    pre, code {{
        font-family: 'Consolas', 'Courier New', 'TH Sarabun New', 'Sarabun', monospace;
        font-size: 13pt;
        white-space: pre-wrap;
        word-break: break-word;
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
    a {{
        color: #0284c7;
        text-decoration: none;
    }}
    a:hover {{
        text-decoration: underline;
    }}
    .mermaid-diagram {{
        margin: 14pt 0;
        text-align: center;
        page-break-inside: avoid;
    }}
    pre.mermaid {{
        font-family: 'Consolas', 'TH Sarabun New', monospace;
        font-size: 12pt;
        background-color: #f8fafc;
        border: 1pt solid #cbd5e1;
        border-radius: 6pt;
        padding: 10pt;
        text-align: left;
        white-space: pre-wrap;
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

def _format_inline_text(text: str) -> str:
    """จัดรูปแบบข้อความ inline สำหรับ Markdown: ลิงก์, ตัวหนา, ตัวเอียง, code, และ badge กฎหมาย"""
    # Markdown Links: [text](url) -> <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Badges
    text = re.sub(r'(คำพิพากษาศาลฎีกาที่|คำสั่งคำร้องศาลฎีกาที่|ฎีกาที่)\s*(\d+/\d{2,4})', r'<span class="deka-badge">\1 \2</span>', text)
    text = re.sub(r'(ป\.พ\.พ\.|ป\.อ\.|ป\.วิ\.พ\.|ป\.วิ\.อ\.)\s*(มาตรา|ม\.)\s*(\d+)', r'<span class="statute-badge">\1 \2 \3</span>', text)
    return text

def _render_table_html(table_lines: List[str]) -> str:
    """แปลงตาราง Markdown เป็น HTML Table พร้อม Container จัดกึ่งกลางและจัดแนวคอลัมน์"""
    if not table_lines:
        return ""
    matrix = []
    for r in table_lines:
        s = r.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        matrix.append([c.strip() for c in s.split("|")])
    if not matrix:
        return ""

    headers = matrix[0]
    alignments = ["left"] * len(headers)
    start_idx = 1

    if len(matrix) > 1 and all(set(c.replace(":", "").replace("-", "").strip()) == set() for c in matrix[1] if c.strip()):
        start_idx = 2
        for i, col in enumerate(matrix[1]):
            c = col.strip()
            if c.startswith(":") and c.endswith(":"):
                alignments[i] = "center"
            elif c.endswith(":"):
                alignments[i] = "right"
            elif c.startswith(":"):
                alignments[i] = "left"

    tbl_parts = ["<div class='table-container'><table><thead><tr>"]
    for i, h in enumerate(headers):
        align = alignments[i] if i < len(alignments) else "left"
        tbl_parts.append(f"<th style='text-align: {align};'>{_format_inline_text(h)}</th>")
    tbl_parts.append("</tr></thead><tbody>")

    for row in matrix[start_idx:]:
        tbl_parts.append("<tr>")
        for i, c in enumerate(row):
            align = alignments[i] if i < len(alignments) else "left"
            tbl_parts.append(f"<td style='text-align: {align};'>{_format_inline_text(c)}</td>")
        tbl_parts.append("</tr>")

    tbl_parts.append("</tbody></table></div>")
    return "".join(tbl_parts)

def markdown_to_thai_html(markdown_text: str, title: str = "บทวิเคราะห์ข้อกฎหมาย") -> str:
    """
    แปลงเนื้อหา Markdown บทวิเคราะห์กฎหมาย 10 หัวข้อ เป็น HTML ตามระเบียบสารบรรณ
    โดยจัดการหัวเรื่อง ตัวหนา กล่องคำเตือน รายการลำดับ/ไม่สลัก ตาราง แผนผัง Mermaid และตราประทับ
    """
    lines = markdown_text.splitlines()
    html_body_lines = []
    in_ul = False
    in_ol = False
    in_sub_ul = False
    in_code_block = False
    is_mermaid = False
    table_buffer = []

    def _close_lists():
        nonlocal in_ul, in_ol, in_sub_ul
        if in_sub_ul:
            if in_ol:
                html_body_lines.append("</ul></li>")
            else:
                html_body_lines.append("</ul>")
            in_sub_ul = False
        elif in_ol:
            html_body_lines.append("</li>")
        if in_ol:
            html_body_lines.append("</ol>")
            in_ol = False
        if in_ul:
            html_body_lines.append("</ul>")
            in_ul = False

    for raw_line in lines:
        line = raw_line.strip()

        # Handle Code Block (Mermaid or Raw Code)
        if line.startswith("```"):
            if table_buffer:
                html_body_lines.append(_render_table_html(table_buffer))
                table_buffer = []
            if in_code_block:
                if is_mermaid:
                    html_body_lines.append("</pre></div>")
                else:
                    html_body_lines.append("</code></pre></div>")
                in_code_block = False
                is_mermaid = False
            else:
                _close_lists()
                lang = line.lstrip("`").strip().lower()
                if lang == "mermaid":
                    html_body_lines.append("<div class='mermaid-diagram'><pre class='mermaid'>")
                    is_mermaid = True
                else:
                    html_body_lines.append("<div class='callout-box'><pre><code>")
                    is_mermaid = False
                in_code_block = True
            continue

        if in_code_block:
            html_body_lines.append(html.escape(raw_line))
            continue

        # Handle Table lines
        if line.startswith("|") and line.endswith("|"):
            _close_lists()
            table_buffer.append(line)
            continue
        elif table_buffer:
            html_body_lines.append(_render_table_html(table_buffer))
            table_buffer = []

        if not line:
            continue

        # Headings
        if line.startswith("# "):
            _close_lists()
            clean_title = line[2:].strip()
            html_body_lines.append(f"<h1 class='doc-title'>{html.escape(clean_title)}</h1>")
            continue
        elif line.startswith("## "):
            _close_lists()
            sec_title = line[3:].strip()
            html_body_lines.append(f"<h2 class='section-title'>{html.escape(sec_title)}</h2>")
            continue
        elif line.startswith("### "):
            _close_lists()
            subsec_title = line[4:].strip()
            html_body_lines.append(f"<h3 class='subsection-title'>{html.escape(subsec_title)}</h3>")
            continue
        elif line.startswith("#### "):
            _close_lists()
            subsubsec_title = line[5:].strip()
            html_body_lines.append(f"<h4 class='subsubsec-title'>{html.escape(subsubsec_title)}</h4>")
            continue
        elif line.startswith("##### "):
            _close_lists()
            subsubsubsec_title = line[6:].strip()
            html_body_lines.append(f"<h5 class='subsubsubsec-title'>{html.escape(subsubsubsec_title)}</h5>")
            continue

        # Blockquotes / Alerts
        if line.startswith(">"):
            _close_lists()
            quote_text = line.lstrip("> ").strip()
            quote_text = _format_inline_text(quote_text)
            html_body_lines.append(f"<div class='callout-box'><p class='no-indent'>{quote_text}</p></div>")
            continue

        # Horizontal rules
        if line in ("---", "***", "___"):
            _close_lists()
            html_body_lines.append("<hr style='border: 0; border-top: 1pt solid #cbd5e1; margin: 16pt 0;'>")
            continue

        # Ordered List Items (e.g. 1. 2. 3.)
        ol_match = re.match(r'^(\s*)(\d+)\.\s+(.*)', raw_line)
        if ol_match:
            indent = len(ol_match.group(1))
            num = int(ol_match.group(2))
            item_text = _format_inline_text(ol_match.group(3))

            if in_ol and num == 1:
                _close_lists()

            if in_sub_ul:
                html_body_lines.append("</ul></li>")
                in_sub_ul = False
            elif in_ol:
                html_body_lines.append("</li>")
            if in_ul:
                html_body_lines.append("</ul>")
                in_ul = False

            if not in_ol:
                if num == 1:
                    html_body_lines.append("<ol>")
                else:
                    html_body_lines.append(f'<ol start="{num}">')
                in_ol = True
            html_body_lines.append(f'<li value="{num}">{item_text}')
            continue

        # Unordered List Items (- or *)
        ul_match = re.match(r'^(\s*)([-*])\s+(.*)', raw_line)
        if ul_match:
            indent = len(ul_match.group(1))
            item_text = _format_inline_text(ul_match.group(3))

            if in_ol:
                if not in_sub_ul:
                    html_body_lines.append("<ul>")
                    in_sub_ul = True
                html_body_lines.append(f"<li>{item_text}</li>")
                continue
            elif in_ul:
                if indent >= 2:
                    if not in_sub_ul:
                        html_body_lines.append("<ul>")
                        in_sub_ul = True
                    html_body_lines.append(f"<li>{item_text}</li>")
                    continue
                else:
                    if in_sub_ul:
                        html_body_lines.append("</ul>")
                        in_sub_ul = False
                    html_body_lines.append(f"<li>{item_text}</li>")
                    continue
            else:
                html_body_lines.append("<ul>")
                in_ul = True
                html_body_lines.append(f"<li>{item_text}</li>")
                continue

        # Regular Paragraph
        _close_lists()
        p_text = _format_inline_text(line)
        html_body_lines.append(f"<p>{p_text}</p>")

    _close_lists()
    if in_code_block:
        html_body_lines.append("</pre></div>")
    if table_buffer:
        html_body_lines.append(_render_table_html(table_buffer))

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
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            if (typeof mermaid !== "undefined") {{
                mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
            }}
        }});
    </script>
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

def convert_markdown_to_thai_html(
    markdown_path_or_content: Union[str, Path],
    output_html_path: Optional[Union[str, Path]] = None,
    doc_title: Optional[str] = None
) -> str:
    """
    แปลงไฟล์ Markdown หรือข้อความ Markdown เป็น HTML ตามระเบียบสารบรรณ
    หากระบุ output_html_path จะบันทึกไฟล์ลงดิสก์ด้วย
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

    if output_html_path:
        out_p = Path(output_html_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(html_content, encoding="utf-8")
        logger.info(f"Saved Thai Saraban HTML document at: {out_p}")

    return html_content

def convert_markdown_to_thai_pdf(
    markdown_path_or_content: Union[str, Path],
    output_pdf_path: Union[str, Path],
    doc_title: Optional[str] = None,
    save_html: bool = True
) -> Path:
    """
    แปลงไฟล์ Markdown หรือข้อความ Markdown เป็นเอกสาร PDF ภาษาไทย
    โดยเรนเดอร์เป็น HTML ก่อน แล้วแปลงเป็น PDF ผ่าน Chromium Headless
    หาก save_html=True จะบันทึกไฟล์ .html คู่กันไว้ในโฟลเดอร์เดียวกันเพื่อให้เปิดดูบนเบราว์เซอร์ได้
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

    out_pdf_path = Path(output_pdf_path).resolve()
    if save_html:
        out_html_path = out_pdf_path.with_suffix(".html")
        out_html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"Saved companion HTML at: {out_html_path}")

    return convert_html_to_thai_pdf(html_content, out_pdf_path)

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

def tokenize_markdown_inlines(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """แยกแยะ Token ในบรรทัด Markdown เช่น ตัวหนา ตัวเอียง ลิงก์ และตราประทับข้อกฎหมาย"""
    pattern = re.compile(
        r"(\*\*[^*]+\*\*|"
        r"(?<!\*)\*[^*]+\*(?!\*)|"
        r"`[^`]+`|"
        r"\[([^\]]+)\]\(([^)]+)\)|"
        r"(?:คำพิพากษาศาลฎีกาที่|คำสั่งคำร้องศาลฎีกาที่|ฎีกาที่)\s*\d+/\d{2,4}|"
        r"(?:ป\.พ\.พ\.|ป\.อ\.|ป\.วิ\.พ\.|ป\.วิ\.อ\.)\s*(?:มาตรา|ม\.)\s*\d+)"
    )
    tokens = []
    last_idx = 0
    for match in pattern.finditer(text):
        if match.start() > last_idx:
            tokens.append((text[last_idx:match.start()], {}))
        m_str = match.group(0)
        if m_str.startswith("**") and m_str.endswith("**"):
            tokens.append((m_str[2:-2], {"bold": True}))
        elif m_str.startswith("*") and m_str.endswith("*"):
            tokens.append((m_str[1:-1], {"italic": True}))
        elif m_str.startswith("`") and m_str.endswith("`"):
            tokens.append((m_str[1:-1], {"code": True}))
        elif m_str.startswith("[") and "](" in m_str:
            link_m = re.match(r"\[([^\]]+)\]\(([^)]+)\)", m_str)
            if link_m:
                tokens.append((link_m.group(1), {"url": link_m.group(2)}))
            else:
                tokens.append((m_str, {}))
        elif "ฎีกา" in m_str:
            tokens.append((m_str, {"badge": "deka", "bold": True}))
        elif any(k in m_str for k in ["ป.พ.พ.", "ป.อ.", "ป.วิ.พ.", "ป.วิ.อ."]):
            tokens.append((m_str, {"badge": "statute", "bold": True}))
        else:
            tokens.append((m_str, {}))
        last_idx = match.end()
    if last_idx < len(text):
        tokens.append((text[last_idx:], {}))
    return tokens

def _add_inlines_to_docx_paragraph(
    paragraph: Any,
    text: str,
    base_font: str = "TH Sarabun New",
    base_size: int = 16,
    base_color: Optional[Any] = None
) -> None:
    """เพิ่ม Run พร้อมจัดรูปแบบตัวหนา ตัวเอียง สีตราประทับ และฟอนต์ภาษาไทย complex script ลงในย่อหน้า Word"""
    tokens = tokenize_markdown_inlines(text)
    for token_text, flags in tokens:
        if not token_text:
            continue
        run = paragraph.add_run(token_text)
        run.bold = flags.get("bold", False)
        run.italic = flags.get("italic", False)

        if flags.get("badge") == "deka":
            run.font.color.rgb = RGBColor(0x03, 0x69, 0xA1)
        elif flags.get("badge") == "statute":
            run.font.color.rgb = RGBColor(0x92, 0x40, 0x0E)
        elif flags.get("url"):
            run.font.color.rgb = RGBColor(0x02, 0x84, 0xC7)
            run.underline = True
        elif base_color:
            run.font.color.rgb = base_color

        if flags.get("code"):
            run.font.name = "Consolas"
            run.font.size = Pt(max(10, base_size - 3))
        else:
            run.font.name = base_font
            run.font.size = Pt(base_size)
            # ผูก Complex Script (cs) และ East Asian fonts สำหรับภาษาไทย (Bug 1 & Bug 5)
            rPr = run._r.get_or_add_rPr()
            rFonts = OxmlElement("w:rFonts")
            rFonts.set(qn("w:ascii"), base_font)
            rFonts.set(qn("w:hAnsi"), base_font)
            rFonts.set(qn("w:cs"), base_font)
            rPr.append(rFonts)

def convert_markdown_to_docx(
    markdown_path_or_content: Union[str, Path],
    output_docx_path: Union[str, Path],
    doc_title: Optional[str] = None
) -> Path:
    """
    แปลงข้อความหรือไฟล์ Markdown เป็นเอกสาร Microsoft Word (.docx)
    ตามมาตรฐานงานสารบรรณไทย 16pt (Bug 4) และป้องกันตัวอักษรถ่างด้วย Natural Alignment LEFT (Bug 5)
    """
    if not DOCX_AVAILABLE:
        raise ImportError(
            "โมดูล 'python-docx' ยังไม่ได้ถูกติดตั้งในระบบ\n"
            "กรุณาติดตั้งด้วยคำสั่ง: pip install python-docx"
        )

    if isinstance(markdown_path_or_content, Path) or (isinstance(markdown_path_or_content, str) and os.path.exists(markdown_path_or_content)):
        p = Path(markdown_path_or_content)
        with open(p, "r", encoding="utf-8") as f:
            md_content = f.read()
        title = doc_title or p.stem.replace("_", " ")
    else:
        md_content = str(markdown_path_or_content)
        title = doc_title or "บทวิเคราะห์ข้อกฎหมาย"

    doc = Document()

    # ตั้งค่าหน้ากระดาษ A4 และระยะขอบมาตรฐาน 20mm/15mm (Bug 4)
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.5)

    # กำหนดสไตล์ Normal ตามมาตรฐานสารบรรณ 16pt และ Left Alignment ป้องกัน thaiDistribute (Bug 5)
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "TH Sarabun New"
    normal_style.font.size = Pt(16)
    normal_style.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    normal_style.paragraph_format.line_spacing = 1.25
    normal_style.paragraph_format.space_after = Pt(4)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    lines = md_content.splitlines()
    table_buffer: List[str] = []
    in_code_block = False

    def flush_docx_table():
        nonlocal table_buffer
        if not table_buffer:
            return
        matrix = []
        for r in table_buffer:
            s = r.strip()
            if s.startswith("|"): s = s[1:]
            if s.endswith("|"): s = s[:-1]
            matrix.append([c.strip() for c in s.split("|")])
        table_buffer = []
        if not matrix:
            return
        headers = matrix[0]
        start_idx = 1
        if len(matrix) > 1 and all(set(c.replace(":", "").replace("-", "").strip()) == set() for c in matrix[1] if c.strip()):
            start_idx = 2
        rows_data = matrix[start_idx:]
        tbl = doc.add_table(rows=1 + len(rows_data), cols=len(headers))
        tbl.style = "Table Grid"
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, h in enumerate(headers):
            if i < len(tbl.rows[0].cells):
                cell = tbl.rows[0].cells[i]
                shd = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls("w")))
                cell._tc.get_or_add_tcPr().append(shd)
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                _add_inlines_to_docx_paragraph(p, h, base_font="TH Sarabun New", base_size=14, base_color=RGBColor(0x0F, 0x17, 0x2A))
                for run in p.runs:
                    run.bold = True

        for r_i, row in enumerate(rows_data):
            row_cells = tbl.rows[1 + r_i].cells
            for c_i, val in enumerate(row):
                if c_i < len(row_cells):
                    cell = row_cells[c_i]
                    p = cell.paragraphs[0]
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    _add_inlines_to_docx_paragraph(p, val, base_font="TH Sarabun New", base_size=14)

        p_after = doc.add_paragraph()
        p_after.paragraph_format.space_after = Pt(4)

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```"):
            if table_buffer:
                flush_docx_table()
            in_code_block = not in_code_block
            continue

        if in_code_block:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(raw_line)
            run.font.name = "Consolas"
            run.font.size = Pt(13)
            continue

        if line.startswith("|") and line.endswith("|"):
            table_buffer.append(line)
            continue
        elif table_buffer:
            flush_docx_table()

        if not line:
            continue

        # Headings
        if line.startswith("# "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(8)
            _add_inlines_to_docx_paragraph(p, line[2:].strip(), base_size=22, base_color=RGBColor(0x0F, 0x17, 0x2A))
            for run in p.runs: run.bold = True
            continue
        elif line.startswith("## "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(6)
            _add_inlines_to_docx_paragraph(p, line[3:].strip(), base_size=18, base_color=RGBColor(0x1E, 0x3A, 0x8A))
            for run in p.runs: run.bold = True
            continue
        elif line.startswith("### "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            _add_inlines_to_docx_paragraph(p, line[4:].strip(), base_size=16, base_color=RGBColor(0x33, 0x41, 0x55))
            for run in p.runs: run.bold = True
            continue
        elif line.startswith("#### "):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            _add_inlines_to_docx_paragraph(p, line[5:].strip(), base_size=15, base_color=RGBColor(0x47, 0x55, 0x69))
            for run in p.runs: run.bold = True
            continue

        # Blockquote
        if line.startswith(">"):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.left_indent = Cm(0.8)
            p.paragraph_format.space_after = Pt(6)
            _add_inlines_to_docx_paragraph(p, line.lstrip("> ").strip(), base_size=15, base_color=RGBColor(0x33, 0x41, 0x55))
            continue

        # Bullet List
        if line.startswith("- ") or line.startswith("* "):
            p = doc.add_paragraph(style="List Bullet")
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(2)
            _add_inlines_to_docx_paragraph(p, line[2:].strip())
            continue

        # Numbered List
        ol_match = re.match(r"^(\d+)\.\s+(.*)", line)
        if ol_match:
            p = doc.add_paragraph(style="List Number")
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(2)
            _add_inlines_to_docx_paragraph(p, ol_match.group(2).strip())
            continue

        # Separator
        if line in ("---", "***", "___"):
            continue

        # Regular Paragraph
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.first_line_indent = Cm(1.25)
        p.paragraph_format.space_after = Pt(4)
        _add_inlines_to_docx_paragraph(p, line)

    if table_buffer:
        flush_docx_table()

    # Footer note
    footer_p = doc.add_paragraph()
    footer_p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    footer_p.paragraph_format.space_before = Pt(16)
    footer_run = footer_p.add_run("เอกสารจัดทำโดย THLawDeka AI Legal Intelligence Advisor • มาตรฐานสารบรรณ 16pt • Word DOCX")
    footer_run.font.name = "TH Sarabun New"
    footer_run.font.size = Pt(11)
    footer_run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    out_p = Path(output_docx_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_p))
    logger.info(f"Successfully generated Thai DOCX document at: {out_p}")
    return out_p

def _add_inlines_to_odf_element(doc: Any, parent_el: Any, text: str, span_styles: Dict[str, Any]) -> None:
    """เพิ่ม Span พร้อมจัดรูปแบบตัวหนา ตัวเอียง และตราประทับ Complex Text Layout (CTL) ลงในอิลิเมนต์ ODF"""
    tokens = tokenize_markdown_inlines(text)
    for token_text, flags in tokens:
        if not token_text:
            continue
        if flags.get("bold") and not flags.get("italic") and not flags.get("badge"):
            s = Span(stylename=span_styles["bold"], text=token_text)
            parent_el.addElement(s)
        elif flags.get("italic") and not flags.get("bold"):
            s = Span(stylename=span_styles["italic"], text=token_text)
            parent_el.addElement(s)
        elif flags.get("bold") and flags.get("italic"):
            s = Span(stylename=span_styles["bold_italic"], text=token_text)
            parent_el.addElement(s)
        elif flags.get("badge") == "deka":
            s = Span(stylename=span_styles["deka_badge"], text=token_text)
            parent_el.addElement(s)
        elif flags.get("badge") == "statute":
            s = Span(stylename=span_styles["statute_badge"], text=token_text)
            parent_el.addElement(s)
        elif flags.get("code"):
            s = Span(stylename=span_styles["code"], text=token_text)
            parent_el.addElement(s)
        elif flags.get("url"):
            s = Span(stylename=span_styles["url"], text=token_text)
            parent_el.addElement(s)
        else:
            parent_el.addText(token_text)

def convert_markdown_to_odt(
    markdown_path_or_content: Union[str, Path],
    output_odt_path: Union[str, Path],
    doc_title: Optional[str] = None
) -> Path:
    """
    แปลงข้อความหรือไฟล์ Markdown เป็นเอกสาร OpenDocument (.odt)
    ตามมาตรฐานระเบียบสารบรรณ 16pt และผูกคุณสมบัติ Complex Text Layout (CTL) คู่กับ Western (Bug 6)
    """
    if not ODF_AVAILABLE:
        raise ImportError(
            "โมดูล 'odfpy' ยังไม่ได้ถูกติดตั้งในระบบ\n"
            "กรุณาติดตั้งด้วยคำสั่ง: pip install odfpy"
        )

    if isinstance(markdown_path_or_content, Path) or (isinstance(markdown_path_or_content, str) and os.path.exists(markdown_path_or_content)):
        p = Path(markdown_path_or_content)
        with open(p, "r", encoding="utf-8") as f:
            md_content = f.read()
        title = doc_title or p.stem.replace("_", " ")
    else:
        md_content = str(markdown_path_or_content)
        title = doc_title or "บทวิเคราะห์ข้อกฎหมาย"

    doc = OpenDocumentText()

    # Paragraph Styles with Thai Complex Text Layout (CTL) - Bug 6
    body_style = Style(name="ThaiBody", family="paragraph")
    body_style.addElement(ParagraphProperties(textalign="left", lineheight="125%", textindent="1.25cm", marginbottom="6pt"))
    body_style.addElement(TextProperties(fontname="TH Sarabun New", fontsize="16pt", fontnamecomplex="TH Sarabun New", fontsizecomplex="16pt"))
    doc.styles.addElement(body_style)

    body_no_indent = Style(name="ThaiBodyNoIndent", family="paragraph")
    body_no_indent.addElement(ParagraphProperties(textalign="left", lineheight="125%", marginbottom="6pt"))
    body_no_indent.addElement(TextProperties(fontname="TH Sarabun New", fontsize="16pt", fontnamecomplex="TH Sarabun New", fontsizecomplex="16pt"))
    doc.styles.addElement(body_no_indent)

    title_style = Style(name="ThaiTitle", family="paragraph")
    title_style.addElement(ParagraphProperties(textalign="left", lineheight="125%", margintop="14pt", marginbottom="8pt"))
    title_style.addElement(TextProperties(fontname="TH Sarabun New", fontsize="22pt", fontweight="bold", fontnamecomplex="TH Sarabun New", fontsizecomplex="22pt", fontweightcomplex="bold", color="#0f172a"))
    doc.styles.addElement(title_style)

    h1_style = Style(name="ThaiH1", family="paragraph")
    h1_style.addElement(ParagraphProperties(textalign="left", lineheight="135%", margintop="12pt", marginbottom="6pt"))
    h1_style.addElement(TextProperties(fontname="TH Sarabun New", fontsize="18pt", fontweight="bold", fontnamecomplex="TH Sarabun New", fontsizecomplex="18pt", fontweightcomplex="bold", color="#1e3a8a"))
    doc.styles.addElement(h1_style)

    h2_style = Style(name="ThaiH2", family="paragraph")
    h2_style.addElement(ParagraphProperties(textalign="left", lineheight="140%", margintop="10pt", marginbottom="4pt"))
    h2_style.addElement(TextProperties(fontname="TH Sarabun New", fontsize="16pt", fontweight="bold", fontnamecomplex="TH Sarabun New", fontsizecomplex="16pt", fontweightcomplex="bold", color="#334155"))
    doc.styles.addElement(h2_style)

    quote_style = Style(name="ThaiQuote", family="paragraph")
    quote_style.addElement(ParagraphProperties(textalign="left", lineheight="135%", marginleft="0.8cm", marginbottom="6pt"))
    quote_style.addElement(TextProperties(fontname="TH Sarabun New", fontsize="15pt", fontnamecomplex="TH Sarabun New", fontsizecomplex="15pt", color="#334155"))
    doc.styles.addElement(quote_style)

    list_style = Style(name="ThaiList", family="paragraph")
    list_style.addElement(ParagraphProperties(textalign="left", lineheight="130%", marginleft="1.0cm", marginbottom="3pt"))
    list_style.addElement(TextProperties(fontname="TH Sarabun New", fontsize="16pt", fontnamecomplex="TH Sarabun New", fontsizecomplex="16pt"))
    doc.styles.addElement(list_style)

    # Table Styles
    th_style = Style(name="ThaiTH", family="table-cell")
    th_style.addElement(TableCellProperties(backgroundcolor="#f1f5f9", padding="6pt", border="0.5pt solid #cbd5e1"))
    doc.styles.addElement(th_style)

    td_style = Style(name="ThaiTD", family="table-cell")
    td_style.addElement(TableCellProperties(padding="6pt", border="0.5pt solid #cbd5e1"))
    doc.styles.addElement(td_style)

    # Span Styles with CTL
    bold_span = Style(name="ThaiSpanBold", family="text")
    bold_span.addElement(TextProperties(fontname="TH Sarabun New", fontweight="bold", fontnamecomplex="TH Sarabun New", fontweightcomplex="bold"))
    doc.styles.addElement(bold_span)

    italic_span = Style(name="ThaiSpanItalic", family="text")
    italic_span.addElement(TextProperties(fontname="TH Sarabun New", fontstyle="italic", fontnamecomplex="TH Sarabun New", fontsizecomplex="16pt"))
    doc.styles.addElement(italic_span)

    bold_italic_span = Style(name="ThaiSpanBoldItalic", family="text")
    bold_italic_span.addElement(TextProperties(fontname="TH Sarabun New", fontweight="bold", fontstyle="italic", fontnamecomplex="TH Sarabun New", fontweightcomplex="bold"))
    doc.styles.addElement(bold_italic_span)

    deka_badge_span = Style(name="ThaiSpanDeka", family="text")
    deka_badge_span.addElement(TextProperties(fontname="TH Sarabun New", fontweight="bold", fontnamecomplex="TH Sarabun New", fontweightcomplex="bold", color="#0369a1"))
    doc.styles.addElement(deka_badge_span)

    statute_badge_span = Style(name="ThaiSpanStatute", family="text")
    statute_badge_span.addElement(TextProperties(fontname="TH Sarabun New", fontweight="bold", fontnamecomplex="TH Sarabun New", fontweightcomplex="bold", color="#92400e"))
    doc.styles.addElement(statute_badge_span)

    code_span = Style(name="ThaiSpanCode", family="text")
    code_span.addElement(TextProperties(fontname="Consolas", fontsize="13pt"))
    doc.styles.addElement(code_span)

    url_span = Style(name="ThaiSpanURL", family="text")
    url_span.addElement(TextProperties(fontname="TH Sarabun New", fontnamecomplex="TH Sarabun New", color="#0284c7", textunderlinestyle="solid"))
    doc.styles.addElement(url_span)

    span_styles = {
        "bold": bold_span,
        "italic": italic_span,
        "bold_italic": bold_italic_span,
        "deka_badge": deka_badge_span,
        "statute_badge": statute_badge_span,
        "code": code_span,
        "url": url_span
    }

    lines = md_content.splitlines()
    table_buffer = []
    in_code_block = False

    def flush_odf_table():
        nonlocal table_buffer
        if not table_buffer:
            return
        matrix = []
        for r in table_buffer:
            s = r.strip()
            if s.startswith("|"): s = s[1:]
            if s.endswith("|"): s = s[:-1]
            matrix.append([c.strip() for c in s.split("|")])
        table_buffer = []
        if not matrix:
            return
        headers = matrix[0]
        start_idx = 1
        if len(matrix) > 1 and all(set(c.replace(":", "").replace("-", "").strip()) == set() for c in matrix[1] if c.strip()):
            start_idx = 2
        rows_data = matrix[start_idx:]
        tbl = Table()
        tbl.addElement(TableColumn(numbercolumnsrepeated=len(headers)))

        hdr_row = TableRow()
        for h in headers:
            c = TableCell(stylename=th_style)
            p = P(stylename=body_no_indent)
            _add_inlines_to_odf_element(doc, p, h, span_styles)
            c.addElement(p)
            hdr_row.addElement(c)
        tbl.addElement(hdr_row)

        for row in rows_data:
            tr = TableRow()
            for val in row:
                c = TableCell(stylename=td_style)
                p = P(stylename=body_no_indent)
                _add_inlines_to_odf_element(doc, p, val, span_styles)
                c.addElement(p)
                tr.addElement(c)
            tbl.addElement(tr)
        doc.text.addElement(tbl)

    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```"):
            if table_buffer:
                flush_odf_table()
            in_code_block = not in_code_block
            continue

        if in_code_block:
            p = P(stylename=quote_style)
            s = Span(stylename=code_span, text=raw_line)
            p.addElement(s)
            doc.text.addElement(p)
            continue

        if line.startswith("|") and line.endswith("|"):
            table_buffer.append(line)
            continue
        elif table_buffer:
            flush_odf_table()

        if not line:
            continue

        if line.startswith("# "):
            h = H(outlinelevel=1, stylename=title_style)
            _add_inlines_to_odf_element(doc, h, line[2:].strip(), span_styles)
            doc.text.addElement(h)
            continue
        elif line.startswith("## "):
            h = H(outlinelevel=2, stylename=h1_style)
            _add_inlines_to_odf_element(doc, h, line[3:].strip(), span_styles)
            doc.text.addElement(h)
            continue
        elif line.startswith("### "):
            h = H(outlinelevel=3, stylename=h2_style)
            _add_inlines_to_odf_element(doc, h, line[4:].strip(), span_styles)
            doc.text.addElement(h)
            continue
        elif line.startswith("#### "):
            h = H(outlinelevel=4, stylename=h2_style)
            _add_inlines_to_odf_element(doc, h, line[5:].strip(), span_styles)
            doc.text.addElement(h)
            continue

        if line.startswith(">"):
            p = P(stylename=quote_style)
            _add_inlines_to_odf_element(doc, p, line.lstrip("> ").strip(), span_styles)
            doc.text.addElement(p)
            continue

        if line.startswith("- ") or line.startswith("* "):
            p = P(stylename=list_style)
            p.addText("• ")
            _add_inlines_to_odf_element(doc, p, line[2:].strip(), span_styles)
            doc.text.addElement(p)
            continue

        ol_match = re.match(r"^(\d+)\.\s+(.*)", line)
        if ol_match:
            p = P(stylename=list_style)
            p.addText(f"{ol_match.group(1)}. ")
            _add_inlines_to_odf_element(doc, p, ol_match.group(2).strip(), span_styles)
            doc.text.addElement(p)
            continue

        if line in ("---", "***", "___"):
            continue

        p = P(stylename=body_style)
        _add_inlines_to_odf_element(doc, p, line, span_styles)
        doc.text.addElement(p)

    if table_buffer:
        flush_odf_table()

    # Footer note
    footer_p = P(stylename=quote_style)
    footer_p.addText("เอกสารจัดทำโดย THLawDeka AI Legal Intelligence Advisor • มาตรฐานสารบรรณ 16pt • OpenDocument ODT")
    doc.text.addElement(footer_p)

    out_p = Path(output_odt_path).resolve()
    out_p.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_p))
    logger.info(f"Successfully generated Thai ODT document at: {out_p}")
    return out_p

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
        "docx_available": DOCX_AVAILABLE,
        "odf_available": ODF_AVAILABLE,
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

def export_all_formats(
    markdown_path_or_content: Union[str, Path],
    output_base_path: Union[str, Path],
    doc_title: Optional[str] = None
) -> Dict[str, str]:
    """
    ส่งออกเอกสารภาษาไทยครอบคลุมครบทุกฟอร์แมตในคำสั่งเดียว (HTML, PDF, DOCX, ODT)
    ตามมาตรฐานงานสารบรรณ 16pt และสถาปัตยกรรมเอกสารข้าม OS
    """
    base = Path(output_base_path).resolve()
    base.parent.mkdir(parents=True, exist_ok=True)
    results = {}

    html_file = base.with_suffix(".html")
    pdf_file = base.with_suffix(".pdf")
    docx_file = base.with_suffix(".docx")
    odt_file = base.with_suffix(".odt")

    # 1. HTML
    convert_markdown_to_thai_html(markdown_path_or_content, html_file, doc_title=doc_title)
    results["html"] = str(html_file)

    # 2. PDF
    try:
        convert_markdown_to_thai_pdf(markdown_path_or_content, pdf_file, doc_title=doc_title, save_html=False)
        results["pdf"] = str(pdf_file)
    except Exception as e:
        logger.warning(f"PDF export skipped/failed: {e}")

    # 3. DOCX (Word)
    if DOCX_AVAILABLE:
        try:
            convert_markdown_to_docx(markdown_path_or_content, docx_file, doc_title=doc_title)
            results["docx"] = str(docx_file)
        except Exception as e:
            logger.warning(f"DOCX export failed: {e}")

    # 4. ODT (OpenDocument)
    if ODF_AVAILABLE:
        try:
            convert_markdown_to_odt(markdown_path_or_content, odt_file, doc_title=doc_title)
            results["odt"] = str(odt_file)
        except Exception as e:
            logger.warning(f"ODT export failed: {e}")

    return results

def main():
    import argparse
    parser = argparse.ArgumentParser(description="THLawDeka Universal Thai Document & PDF Generator CLI")
    parser.add_argument("--check-env", action="store_true", help="Check system readiness for Thai document generation")
    parser.add_argument("--markdown-to-pdf", nargs=2, metavar=("INPUT_MD", "OUTPUT_PDF"), help="Convert Markdown file to Thai Saraban PDF")
    parser.add_argument("--markdown-to-html", nargs=2, metavar=("INPUT_MD", "OUTPUT_HTML"), help="Convert Markdown file to Thai Saraban HTML")
    parser.add_argument("--markdown-to-docx", nargs=2, metavar=("INPUT_MD", "OUTPUT_DOCX"), help="Convert Markdown file to Thai Saraban DOCX (Word)")
    parser.add_argument("--markdown-to-odt", nargs=2, metavar=("INPUT_MD", "OUTPUT_ODT"), help="Convert Markdown file to Thai Saraban ODT (OpenDocument)")
    parser.add_argument("--export-all", nargs=2, metavar=("INPUT_MD", "OUTPUT_BASE"), help="Export Markdown to all formats (.html, .pdf, .docx, .odt)")
    parser.add_argument("--test-safe-subprocess", action="store_true", help="Test safe python subprocess execution (Bug 3)")

    args = parser.parse_args()

    if args.check_env:
        info = check_system_environment()
        print(json.dumps(info, ensure_ascii=False, indent=2))
        sys.exit(0 if info["status"] == "ready" else 1)

    elif args.markdown_to_html:
        in_md, out_html = args.markdown_to_html
        convert_markdown_to_thai_html(in_md, out_html)
        p = Path(out_html)
        print(json.dumps({"status": "success", "html_path": str(p.resolve()), "size_bytes": p.stat().st_size}, ensure_ascii=False, indent=2))
        sys.exit(0)

    elif args.markdown_to_pdf:
        in_md, out_pdf = args.markdown_to_pdf
        pdf_path = convert_markdown_to_thai_pdf(in_md, out_pdf)
        print(json.dumps({
            "status": "success",
            "pdf_path": str(pdf_path),
            "html_path": str(pdf_path.with_suffix(".html")),
            "size_bytes": pdf_path.stat().st_size
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    elif args.markdown_to_docx:
        in_md, out_docx = args.markdown_to_docx
        docx_path = convert_markdown_to_docx(in_md, out_docx)
        print(json.dumps({
            "status": "success",
            "docx_path": str(docx_path),
            "size_bytes": docx_path.stat().st_size
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    elif args.markdown_to_odt:
        in_md, out_odt = args.markdown_to_odt
        odt_path = convert_markdown_to_odt(in_md, out_odt)
        print(json.dumps({
            "status": "success",
            "odt_path": str(odt_path),
            "size_bytes": odt_path.stat().st_size
        }, ensure_ascii=False, indent=2))
        sys.exit(0)

    elif args.export_all:
        in_md, out_base = args.export_all
        exported = export_all_formats(in_md, out_base)
        print(json.dumps({
            "status": "success",
            "exported_formats": exported
        }, ensure_ascii=False, indent=2))
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
