---
name: fc_mcp
description: ตั้งค่า mcp setting ของ fourcorners-tlex
---
# Prerequisites & Authentication
- ระบบต้องการรหัส FC_API_KEY ในการเข้าถึงเพื่อเรียกใช้งาน mcp `fourcorners-tlex` ระบบตรวจสอบไฟล์ `.env` ใน Root Directory หากยังไม่มีไฟล์ `.env` ให้สร้างไฟล์ดังกล่าวขึ้นมาใหม่ทันที
- Prompt ขอ User input API key ให้ User paste key แบบ Interactive จากนั้นนำค่า API key ที่ได้มาบันทึกลงในไฟล์ `.env` ในรูปแบบ:
  ```env
  FC_API_KEY=your_actual_api_key_here
  ```

# MCP Configuration Setup
- แก้ไขไฟล์ `.agents/mcp_config.json` โดยทำการ **เพิ่มหรืออัปเดต (Merge)** ค่าคอนฟิกของ `fourcorners-tlex` ภายใต้คีย์ `mcpServers` โดยต้อง**คงการตั้งค่าของ Server อื่นๆ ที่มีอยู่เดิม (เช่น `slegaltools-legal-v2`) ไว้เสมอ ห้ามเขียนทับทั้งไฟล์**
- ตัวอย่างโครงสร้างคอนฟิกของ `fourcorners-tlex` ภายใน `mcpServers`:
```json
{
  "mcpServers": {
    "fourcorners-tlex": {
      "type": "http",
      "url": "https://app.fourcorners.law/api/mcp",
      "headers": {
        "Authorization": "Bearer FC_API_KEY",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      }
    }
  }
}
```
*(หมายเหตุ: แทนที่ `FC_API_KEY` ด้วยค่าจริงที่อ่านได้จากไฟล์ `.env`)*
