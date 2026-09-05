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
    re.compile(r"ชนะคดีแน่นอน\s*(?:100%|ร้อยเปอร์เซ็นต์)?"),
    re.compile(r"ศาลต้องตัดสินให้ชนะอย่างแน่นอน"),
    re.compile(r"การันตีผลคดี"),
    re.compile(r"รับรองผลแพ้ชนะ"),
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
            
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "detected_deka_numbers": extract_all_deka_numbers(text),
        "unverified_deka_numbers": unverified_deka,
        "detected_statutes": extract_all_statute_citations(text),
        "mermaid_audit": mermaid_audit
    }

