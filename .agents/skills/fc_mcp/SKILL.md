---
name: fc_mcp
description: ตั้งค่า mcp stting ของ fourcorners-tlex
---
# Prerequisites & Authentication
- ระบบต้องการรหัส FC_API_KEY ในการเข้าถึงเพื่อเรียกใช้งาน mcp  fourcorners-tlex ระบบตรวจสอบไฟล์ .env ใน Root Directoryหากยังไม่มีไฟล์ .env ให้สร้างไฟล์ดังกล่าวขึ้นมาใหม่ทันที
- prompt  user input api key , ใหั user paste key แบบ interactive จากนั้น เพิ่มค่า API key ที่ได้ นำมาบันทึกเพิ่มลงในไฟล์ .env ในรูปแบบดังนี้  FC_API_KEY=your_actual_api_key_here

# mcp setting
- แก้ไขไฟล์ .agents/mcp_config.json (ถ้ายังไม่มีไฟล์ ให้สร้างขึ้นใหม่) โดยนำค่า FC_API_KEY จากไฟล์  .env  ไปแทนที่ค่า FC_API_KEY ข้างล่าง  แล้วบันทึก
{
  "mcpServers": {
    "fourcorners-tlex": {
      "type": "http",
      "url": "https://app.fourcorners.law/api/mcp",
      "headers": {
        "Authorization": "Bearer FC_API_KEY"
      }
    }
  }
}
