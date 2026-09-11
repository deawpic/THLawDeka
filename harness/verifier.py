import re
from typing import List, Dict, Any, Optional

# Regular expressions for detecting any variant of Supreme Court case number citations
DEKA_CITATION_PATTERNS = [
    re.compile(r"(?:คำพิพากษาศาลฎีกาที่|คำพิพากษาฎีกาที่|ฎีกาที่|ฎีกาเลขที่)\s*(\d+/\d{2,4})", re.IGNORECASE),
    re.compile(r"(?:ฎ\.)\s*(\d+/\d{2,4})", re.IGNORECASE),
    re.compile(r"ศาลฎีกาแผนกคดี[^\s]+\s*ที่\s*(\d+/\d{2,4})", re.IGNORECASE),
]

# Prohibited absolute judicial guarantee phrases (Violates Judicial Discretion Gate)
ABSOLUTE_GUARANTEE_PATTERNS = [
    re.compile(r"ชนะ(?:คดี)?(?:อย่าง)?แน่นอน\s*(?:100%|ร้อยเปอร์เซ็นต์)?"),
    re.compile(r"ศาลต้อง(?:ตัดสิน|พิพากษา|ยกฟ้อง)(?:ให้(?:ท่าน)?ชนะ)?(?:อย่าง)?แน่นอน"),
    re.compile(r"การันตีผล(?:คดี)?"),
    re.compile(r"รับรองผล(?:คดี|แพ้ชนะ)?"),
]

# Recognized Thai Legal Codes and Acts
KNOWN_STATUTES = {
    "ป.พ.พ.": "ประมวลกฎหมายแพ่งและพาณิชย์",
    "ป.อ.": "ประมวลกฎหมายอาญา",
    "ป.วิ.พ.": "ประมวลกฎหมายวิธีพิจารณาความแพ่ง",
    "ป.วิ.อ.": "ประมวลกฎหมายวิธีพิจารณาความอาญา",
    "ป.ที่ดิน": "ประมวลกฎหมายที่ดิน",
    "พระธรรมนูญศาลยุติธรรม": "พระธรรมนูญศาลยุติธรรม",
    "พ.ร.บ.คุ้มครองแรงงาน": "พระราชบัญญัติคุ้มครองแรงงาน พ.ศ. 2541",
    "พ.ร.บ.คอมพิวเตอร์": "พระราชบัญญัติว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์",
    "พ.ร.บ.ข้อสัญญาที่ไม่เป็นธรรม": "พระราชบัญญัติว่าด้วยข้อสัญญาที่ไม่เป็นธรรม พ.ศ. 2540",
    "พ.ร.บ.วิธีพิจารณาคดีผู้บริโภค": "พระราชบัญญัติวิธีพิจารณาคดีผู้บริโภค พ.ศ. 2551",
    "พ.ร.บ.ธุรกรรมทางอิเล็กทรอนิกส์": "พระราชบัญญัติว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์",
    "พ.ร.บ.ล้มละลาย": "พระราชบัญญัติล้มละลาย พ.ศ. 2483",
    "พ.ร.บ.จัดตั้งศาลปกครอง": "พระราชบัญญัติจัดตั้งศาลปกครองและวิธีพิจารณาคดีปกครอง พ.ศ. 2542",
}

STATUTE_CITATION_PATTERNS = [
    re.compile(r"(?:ประมวลกฎหมาย(?:แพ่งและพาณิชย์|อาญา|วิธีพิจารณาความแพ่ง|วิธีพิจารณาความอาญา|ที่ดิน)|ป\.(?:พ\.พ\.|อ\.|วิ\.พ\.|วิ\.อ\.|ที่ดิน))", re.IGNORECASE),
    re.compile(r"(?:พระราชบัญญัติ|พ\.ร\.บ\.)\s*[\u0E00-\u0E7F\w\s]+?(?=(?:พ\.ศ\.|มาตรา|ม\.|\s{2,}|$|\n|,|\())", re.IGNORECASE)
]

def extract_all_deka_numbers(text: str) -> List[str]:
    found = []
    for pattern in DEKA_CITATION_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            if m not in found:
                found.append(m)
    return found

def extract_all_statute_citations(text: str) -> List[str]:
    """สกัดชื่อกฎหมายและตัวบทที่ถูกอ้างอิงในข้อความ"""
    found = set()
    for pattern in STATUTE_CITATION_PATTERNS:
        for m in pattern.findall(text):
            cleaned = m.strip()
            if len(cleaned) >= 3 and not cleaned.endswith(("และ", "หรือ", "ตาม")):
                found.add(cleaned)
    return sorted(list(found))

def detect_unverified_deka_citations(
    text: str, 
    verified_payloads: Optional[List[str]] = None,
    cache: Optional[Any] = None
) -> List[str]:
    verified_set = set(verified_payloads or [])
    if cache is not None and hasattr(cache, "get_all_verified_dekas"):
        verified_set.update(cache.get_all_verified_dekas())
    found_citations = extract_all_deka_numbers(text)
    unverified = [cite for cite in found_citations if cite not in verified_set]
    return unverified

def sanitize_hallucinated_deka_numbers(
    text: str, 
    verified_payloads: Optional[List[str]] = None,
    cache: Optional[Any] = None
) -> str:
    unverified = detect_unverified_deka_citations(text, verified_payloads, cache=cache)
    if not unverified:
        return text
    
    sanitized = text
    for cite in unverified:
        for pattern in DEKA_CITATION_PATTERNS:
            sanitized = pattern.sub("แนวคำพิพากษาศาลฎีกาที่พึงเทียบเคียง", sanitized)
    
    return sanitized

def detect_absolute_guarantees(text: str) -> List[str]:
    violations = []
    for pattern in ABSOLUTE_GUARANTEE_PATTERNS:
        match = pattern.search(text)
        if match:
            violations.append(match.group(0))
    return violations

def validate_mermaid_syntax(text: str) -> Dict[str, Any]:
    """
    ตรวจสอบความถูกต้องของบล็อก Mermaid เพื่อป้องกัน Lexical Error จากภาษาไทยและอักขระพิเศษ
    ตามข้อกำหนด Mermaid Unicode & Diagram Guardrail ใน AGENTS.md
    """
    mermaid_blocks = re.findall(r"```mermaid\s*([\s\S]*?)```", text)
    issues = []
    
    for idx, block in enumerate(mermaid_blocks, 1):
        lines = block.strip().split("\n")
        if not lines:
            continue
        first_line = lines[0].strip().split()[0] if lines[0].strip() else ""
        
        # 1. ตรวจจับ classDiagram, stateDiagram, erDiagram ที่มีภาษาไทย
        if any(dt in lines[0] for dt in ["classDiagram", "stateDiagram", "erDiagram"]):
            has_thai = bool(re.search(r"[\u0E00-\u0E7F]", block))
            if has_thai:
                for line_no, line in enumerate(lines, 1):
                    if re.search(r"[\u0E00-\u0E7F]", line):
                        issues.append({
                            "block": idx,
                            "line": line_no,
                            "diagram_type": first_line,
                            "error": f"ห้ามใช้ภาษาไทยใน {first_line} โดยตรง (ทำให้เกิด Lexical Error)",
                            "content": line.strip(),
                            "fix": "เปลี่ยนไปใช้ 'flowchart TD' หรือ 'graph TD' พร้อมครอบข้อความด้วย double quotes [\"...\"]"
                        })
                        
        # 2. ตรวจจับ Node ใน flowchart / graph ที่มีภาษาไทยหรือวงเล็บ แต่ลืมครอบ double quotes ["..."]
        if any(dt in lines[0] for dt in ["flowchart", "graph"]):
            for line_no, line in enumerate(lines, 1):
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("%%"):
                    continue
                # ตรวจจับ Node label เช่น id[...] ที่ข้างในมีภาษาไทยหรือวงเล็บ แต่ไม่ได้ครอบด้วย "
                unquoted_bracket = re.search(r'\b[A-Za-z0-9_]+\s*\[\s*([^"\[\]]*?[\u0E00-\u0E7F()]+[^"\[\]]*?)\s*\]', clean_line)
                if unquoted_bracket:
                    issues.append({
                        "block": idx,
                        "line": line_no,
                        "diagram_type": "flowchart",
                        "error": "Unquoted label with Thai or special characters",
                        "content": clean_line,
                        "fix": 'ครอบข้อความด้วย double quotes เช่น ID["..."]'
                    })
                
                # ตรวจจับ Node label เช่น id(...) ที่ข้างในมีภาษาไทย แต่ไม่ได้ครอบด้วย "
                unquoted_paren = re.search(r'\b[A-Za-z0-9_]+\s*\(\s*([^"()]*?[\u0E00-\u0E7F]+[^"()]*?)\s*\)', clean_line)
                if unquoted_paren:
                    issues.append({
                        "block": idx,
                        "line": line_no,
                        "diagram_type": "flowchart",
                        "error": "Unquoted label with Thai or special characters in parenthesis node",
                        "content": clean_line,
                        "fix": 'ครอบข้อความด้วย double quotes เช่น ID("...")'
                    })
                    
    return {
        "passed": len(issues) == 0,
        "total_diagrams": len(mermaid_blocks),
        "issues": issues
    }

def validate_markdown_tables(text: str) -> Dict[str, Any]:
    """
    ตรวจสอบความถูกต้องของโครงสร้าง Markdown Table ตามมาตรฐาน GFM และกฎข้อ 8 ใน AGENTS.md:
    1. ต้องมี Header Row และ Separator Row (เช่น | :--- | :---: |)
    2. ทุกแถวต้องเริ่มต้นและลงท้ายด้วยเครื่องหมายไปป์ '|'
    3. จำนวนคอลัมน์ในทุกแถว (Header, Separator, Data rows) ต้องเท่ากัน
    4. Separator row ต้องเป็นรูปแบบ ':?-+:?' (เช่น | :--- | :---: | ---: |)
    """
    lines = text.split("\n")
    filtered = []
    in_code = False
    for l in lines:
        if l.strip().startswith("```"):
            in_code = not in_code
            filtered.append("")
        elif in_code:
            filtered.append("")
        else:
            filtered.append(l)

    tables = []
    current_table = []
    start_line = 0
    
    for i, line in enumerate(filtered, 1):
        sline = line.strip()
        if "|" in sline:
            if not current_table:
                start_line = i
            current_table.append((i, sline))
        else:
            if current_table:
                if len(current_table) >= 2:
                    tables.append((start_line, current_table))
                current_table = []
    if current_table and len(current_table) >= 2:
        tables.append((start_line, current_table))

    issues = []
    sep_cell_pattern = re.compile(r"^:?-{2,}:?$")

    for start_l, rows in tables:
        sep_index = -1
        for idx, (l_no, row_text) in enumerate(rows):
            raw_cells = row_text.split("|")
            if row_text.startswith("|"):
                raw_cells = raw_cells[1:]
            if row_text.endswith("|"):
                raw_cells = raw_cells[:-1]
            cells = [c.strip() for c in raw_cells]
            if cells and all(sep_cell_pattern.match(c) for c in cells):
                sep_index = idx
                break

        if sep_index == -1:
            issues.append({
                "line": start_l,
                "error": "ไม่พบแถวเส้นแบ่ง (Separator Row เช่น | :--- | :---: |) ในตาราง Markdown",
                "content": rows[0][1]
            })
            continue

        if sep_index == 0:
            issues.append({
                "line": rows[0][0],
                "error": "พบแถวเส้นแบ่งแต่ไม่มีแถวหัวตาราง (Header Row) ด้านบน",
                "content": rows[0][1]
            })
            continue

        header_l, header_text = rows[sep_index - 1]
        sep_l, sep_text = rows[sep_index]

        if not (header_text.startswith("|") and header_text.endswith("|")):
            issues.append({
                "line": header_l,
                "error": "แถวหัวตาราง (Header Row) ต้องเริ่มต้นและปิดท้ายด้วยเครื่องหมายไปป์ '|'",
                "content": header_text
            })

        header_cells = [c.strip() for c in header_text.strip("|").split("|")]
        expected_cols = len(header_cells)

        if not (sep_text.startswith("|") and sep_text.endswith("|")):
            issues.append({
                "line": sep_l,
                "error": "แถวเส้นแบ่ง (Separator Row) ต้องเริ่มต้นและปิดท้ายด้วยเครื่องหมายไปป์ '|'",
                "content": sep_text
            })

        sep_cells = [c.strip() for c in sep_text.strip("|").split("|")]
        if len(sep_cells) != expected_cols:
            issues.append({
                "line": sep_l,
                "error": f"จำนวนคอลัมน์ของแถวเส้นแบ่ง ({len(sep_cells)}) ไม่ตรงกับหัวตาราง ({expected_cols})",
                "content": sep_text
            })

        for l_no, row_text in rows[sep_index + 1:]:
            if not (row_text.startswith("|") and row_text.endswith("|")):
                issues.append({
                    "line": l_no,
                    "error": "แถวข้อมูลตารางต้องเริ่มต้นและปิดท้ายด้วยเครื่องหมายไปป์ '|'",
                    "content": row_text
                })
            row_cells = [c.strip() for c in row_text.strip("|").split("|")]
            if len(row_cells) != expected_cols:
                issues.append({
                    "line": l_no,
                    "error": f"จำนวนคอลัมน์ของแถวข้อมูล ({len(row_cells)}) ไม่ตรงกับหัวตาราง ({expected_cols})",
                    "content": row_text
                })

    passed = len(issues) == 0
    return {
        "passed": passed,
        "total_tables": len(tables),
        "issues": issues
    }

def detect_prohibited_ascii(text: str) -> Dict[str, Any]:
    """
    ตรวจจับการใช้อักขระหรือโครงสร้าง ASCII Art / ASCII Diagram / ASCII Text Table
    ตามกฎเหล็กข้อ 8 ใน AGENTS.md (Strict Prohibition of ASCII Diagrams & Tables)
    - ตรวจจับเส้นกรอบกล่อง ASCII เช่น +---+, +===+
    - ตรวจจับผังกล่องข้อความ ASCII เช่น [กล่อง A] --> [กล่อง B]
    - ตรวจจับลูกศร ASCII ขนาดยาว เช่น -----> หรือ =====>
    - ตรวจจับ Unicode Box Drawing เช่น ┌─┐, │, └─┘, ║, ╔═╗
    (ยกเว้นภายในบล็อกโค้ด Mermaid หรือ inline backticks)
    """
    lines = text.split("\n")
    filtered = []
    in_code = False
    code_lang = ""
    for l in lines:
        s = l.strip()
        if s.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = s[3:].strip().lower()
                filtered.append("")
            else:
                in_code = False
                code_lang = ""
                filtered.append("")
            continue
        if in_code:
            if code_lang in ["mermaid", "python", "json", "bash", "sh", "sql"]:
                filtered.append("")
            else:
                filtered.append(l)
        else:
            # Mask inline code backticks e.g. `...`
            masked = re.sub(r"`[^`]+`", "", l)
            filtered.append(masked)

    issues = []
    
    # 1. Box drawing unicode corners / verticals
    box_unicode_pattern = re.compile(r"[\u250C\u2510\u2514\u2518\u251C\u2524\u252C\u2534\u253C\u2502\u2550\u2551\u2554\u2557\u255A\u255D\u2560\u2563\u2566\u2569\u256C]")
    
    # 2. ASCII box borders e.g. +---+ or +===+
    ascii_box_pattern = re.compile(r"\+[-=]{3,}\+")
    
    # 3. Pseudo-flowchart arrows e.g. [A] --> [B] or [A] -> [B]
    pseudo_flow_pattern = re.compile(r"\[[^\]\n]+\]\s*(?:-->|->|==>|<--|<-|<==)\s*\[[^\]\n]+\]")
    
    # 4. Long ASCII arrows e.g. -----> or =====>
    long_arrow_pattern = re.compile(r"(?:-{4,}>|={4,}>|<-{4,}|<={4,})")

    for idx, line in enumerate(filtered, 1):
        if not line.strip():
            continue
        
        # Check box unicode
        if box_unicode_pattern.search(line):
            issues.append({
                "line": idx,
                "error": "ตรวจพบ Unicode Box Drawing (ห้ามใช้วาดแผนภาพหรือตาราง ให้ใช้ Mermaid หรือ Markdown Table แทน)",
                "content": line.strip()
            })
            continue

        # Check ASCII box borders
        if ascii_box_pattern.search(line):
            issues.append({
                "line": idx,
                "error": "ตรวจพบเส้นกรอบกล่อง ASCII (เช่น +---+) ห้ามใช้ ให้ใช้ Mermaid หรือ Markdown Table แทน",
                "content": line.strip()
            })
            continue

        # Check pseudo flow
        if pseudo_flow_pattern.search(line):
            issues.append({
                "line": idx,
                "error": "ตรวจพบผังกล่อง ASCII (เช่น [กล่อง A] --> [กล่อง B]) ห้ามใช้ ให้ใช้ Mermaid flowchart TD แทน",
                "content": line.strip()
            })
            continue

        # Check long arrows
        if long_arrow_pattern.search(line):
            issues.append({
                "line": idx,
                "error": "ตรวจพบเส้นลูกศร ASCII ยาว (เช่น ----->) ห้ามใช้ ให้ใช้ Mermaid แทน",
                "content": line.strip()
            })
            continue

    return {
        "passed": len(issues) == 0,
        "issues": issues
    }

def audit_response_for_hallucinations(
    text: str, 
    verified_payloads: Optional[List[str]] = None,
    allow_unverified_citations: bool = False,
    cache: Optional[Any] = None
) -> Dict[str, Any]:
    violations = []
    
    # 1. Check Deka Grounding Gate (Auto-Grounding from Cache if provided)
    unverified_deka = detect_unverified_deka_citations(text, verified_payloads, cache=cache)
    if not allow_unverified_citations:
        if unverified_deka:
            violations.append({
                "gate": "Deka Grounding Gate",
                "severity": "CRITICAL",
                "message": f"Found unverified deka numbers: {unverified_deka}"
            })
            
    # 2. Check Judicial Discretion Gate
    guarantee_violations = detect_absolute_guarantees(text)
    if guarantee_violations:
        violations.append({
            "gate": "Judicial Discretion Gate",
            "severity": "HIGH",
            "message": f"Found absolute outcome guarantees: {guarantee_violations}"
        })
        
    # 3. Check Mermaid Diagram Gate
    mermaid_audit = validate_mermaid_syntax(text)
    if not mermaid_audit["passed"]:
        for issue in mermaid_audit["issues"]:
            violations.append({
                "gate": "Mermaid Diagram Gate",
                "severity": "MEDIUM",
                "message": f"[Block {issue['block']} Line {issue['line']}] {issue['error']}: {issue['content']} -> Fix: {issue['fix']}"
            })

    # 4. Check Markdown Table Gate
    table_audit = validate_markdown_tables(text)
    if not table_audit["passed"]:
        for issue in table_audit["issues"]:
            violations.append({
                "gate": "Markdown Table Gate",
                "severity": "MEDIUM",
                "message": f"[Line {issue['line']}] {issue['error']}: {issue['content']}"
            })

    # 5. Check Prohibited ASCII Gate
    ascii_audit = detect_prohibited_ascii(text)
    if not ascii_audit["passed"]:
        for issue in ascii_audit["issues"]:
            violations.append({
                "gate": "Prohibited ASCII Gate",
                "severity": "MEDIUM",
                "message": f"[Line {issue['line']}] {issue['error']}: {issue['content']}"
            })
            
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "detected_deka_numbers": extract_all_deka_numbers(text),
        "unverified_deka_numbers": unverified_deka,
        "detected_statutes": extract_all_statute_citations(text),
        "mermaid_audit": mermaid_audit,
        "table_audit": table_audit,
        "ascii_audit": ascii_audit
    }

