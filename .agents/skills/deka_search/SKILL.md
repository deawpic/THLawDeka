---
name: deka_search
description: ความสามารถในการค้นหาเลขที่คำพิพากษาศาลฎีกา สรุปย่อเนื้อหา และมาตรากฎหมายที่เกี่ยวข้องผ่าน SLegalTools เพื่อให้ AI Agent สามารถนำข้อมูลคำพิพากษา (คดีบรรทัดฐาน) ไปใช้วิเคราะห์ข้อกฎหมายต่อได้อย่างแม่นยำ
---
# Prerequisites & Authentication
- ระบบต้องการรหัส DEKA_API_KEY ในการเข้าถึงเพื่อเรียกใช้งาน APIKey Verification Workflowระบบตรวจสอบไฟล์ .env ใน Root Directoryหากยังไม่มีไฟล์ .env ให้สร้างไฟล์ดังกล่าวขึ้นมาใหม่ทันที
- open web browser Dashboard for API key creation:  https://api.slegaltools.digital/dashboard เพื่อเข้าสู่ระบบด้วย Google account และกดสร้างคีย์ร้องขอให้ผู้ใช้งานคัดลอกค่า API key ที่ได้ นำมาบันทึกลงในไฟล์ .env ในรูปแบบดังนี้:envDEKA_API_KEY=your_actual_api_key_here
- prompt  user input api key , ใหั user paste key แบบ interactive จากนั้น save ลง .env ให้ automatic

# API Endpoint Spec
- Method: POST
- URL:  https://api.slegaltools.digital/api/search/ai
- Headers: 
        Authorization: Bearer <DEKA_API_KEY>
        Content-Type: application/json
- Payload Structure: json
        {
        "question": " string (คำค้นหา คำหลัก หรือประเด็นข้อกฎหมายที่ต้องการค้น)",
        "top_k": 5
        }

# Example Request
  curl -X POST https://api.slegaltools.digital/api/search/ai \
  -H "Authorization: Bearer DEKA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question":"ตัวแทนโบรคเกอร์ พรก กู้ยืมเงิน","top_k":5}'
        
# Output Handling & Analysis
เมื่อได้รับผลลัพธ์กลับมาในรูปแบบ JSON Object ให้ทำการเข้าถึงออบเจกต์ในส่วนข้อมูล "results" เท่านั้น เพื่อสกัดแยกอาร์เรย์ของคำพิพากษาศาลฎีกาที่ค้นพบ จากนั้นส่งต่ออาเรย์ชุดนี้เข้าสู่กระบวนการวิเคราะห์พิจารณาประเด็นทางกฎหมายในส่วนถัดไป
