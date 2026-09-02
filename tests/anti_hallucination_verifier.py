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
    "พ.ร.บ.คุ้มครองแรงงาน": "พระราชบัญญัติคุ้มครองแรงงาน พ.ศ. 2541",
    "พ.ร.บ.คอมพิวเตอร์": "พระราชบัญญัติว่าด้วยการกระทำความผิดเกี่ยวกับคอมพิวเตอร์",
    "พ.ร.บ.ข้อสัญญาที่ไม่เป็นธรรม": "พระราชบัญญัติว่าด้วยข้อสัญญาที่ไม่เป็นธรรม พ.ศ. 2540",
    "พ.ร.บ.วิธีพิจารณาคดีผู้บริโภค": "พระราชบัญญัติวิธีพิจารณาคดีผู้บริโภค พ.ศ. 2551",
    "พ.ร.บ.ธุรกรรมทางอิเล็กทรอนิกส์": "พระราชบัญญัติว่าด้วยธุรกรรมทางอิเล็กทรอนิกส์"
}

def extract_all_deka_numbers(text: str) -> List[str]:
    found = []
    for pattern in DEKA_CITATION_PATTERNS:
        matches = pattern.findall(text)
        for m in matches:
            if m not in found:
                found.append(m)
    return found

def detect_unverified_deka_citations(text: str, verified_payloads: Optional[List[str]] = None) -> List[str]:
    verified_set = set(verified_payloads or [])
    found_citations = extract_all_deka_numbers(text)
    unverified = [cite for cite in found_citations if cite not in verified_set]
    return unverified

def sanitize_hallucinated_deka_numbers(text: str, verified_payloads: Optional[List[str]] = None) -> str:
    unverified = detect_unverified_deka_citations(text, verified_payloads)
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

def audit_response_for_hallucinations(
    text: str, 
    verified_payloads: Optional[List[str]] = None,
    allow_unverified_citations: bool = False
) -> Dict[str, Any]:
    violations = []
    
    # 1. Check Deka Grounding Gate
    if not allow_unverified_citations:
        unverified_deka = detect_unverified_deka_citations(text, verified_payloads)
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
        
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "detected_deka_numbers": extract_all_deka_numbers(text),
        "unverified_deka_numbers": detect_unverified_deka_citations(text, verified_payloads)
    }
