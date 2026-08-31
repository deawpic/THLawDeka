---
name: tl_mcp
description: ตั้งค่า mcp setting ของ thai-legal
---
# Prerequisites & Authentication
- ระบบต้องการรหัส TL_API_KEY ในการเข้าถึงเพื่อเรียกใช้งาน mcp `thai-legal` ระบบตรวจสอบไฟล์ `.env` ใน Root Directory หากยังไม่มีไฟล์ `.env` ให้สร้างไฟล์ดังกล่าวขึ้นมาใหม่ทันที
- Prompt ขอ User input API key ให้ User paste key แบบ Interactive จากนั้นนำค่า API key ที่ได้มาบันทึกลงในไฟล์ `.env` ในรูปแบบ:
  ```env
  TL_API_KEY=your_actual_api_key_here
  ```

# MCP Configuration Setup
- แก้ไขไฟล์ `.agents/mcp_config.json` โดยทำการ **เพิ่มหรืออัปเดต (Merge)** ค่าคอนฟิกของ `thai-legal` ภายใต้คีย์ `mcpServers` โดยต้อง**คงการตั้งค่าของ Server อื่นๆ ที่มีอยู่เดิม (เช่น `slegaltools-legal-v2` , `fourcorners-tlex`  ) ไว้เสมอ ห้ามเขียนทับทั้งไฟล์**
- ตัวอย่างโครงสร้างคอนฟิกของ `thai-legal` ภายใน `mcpServers`:
```json
{
  "mcpServers": {
    "thai-legal": {
      "type": "http",
      "url": "https://mcp.legaltech.in.th/mcp",
      "headers": {
        "Authorization": "Bearer TL_API_KEY"
      }
    }
  }
}
```
*(หมายเหตุ: แทนที่ `TL_API_KEY` ด้วยค่าจริงที่อ่านได้จากไฟล์ `.env`)*
