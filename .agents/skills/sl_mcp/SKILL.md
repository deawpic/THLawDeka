---
name: sl_mcp
description: ตั้งค่า mcp setting ของ slegaltools-legal-v2
---
# Prerequisites & Authentication
- ระบบต้องการรหัส DEKA_API_KEY  ในการเข้าถึงเพื่อเรียกใช้งาน mcp  slegaltools-legal-v2 ระบบตรวจสอบไฟล์ .env ใน Root Directory หากยังไม่มีไฟล์ .env ให้สร้างไฟล์ดังกล่าวขึ้นมาใหม่ทันที
- prompt  user input api key , ใหั user paste key แบบ interactive จากนั้น เพิ่มค่า API key ที่ได้ นำมาบันทึกเพิ่มลงในไฟล์ .env ในรูปแบบดังนี้  DEKA_API_KEY =your_actual_api_key_here

# install mcp options files and setup mcp config
- MCP bridge file: https://api.slegaltools.digital/install/slegaltools_deka_mcp_bridge.py
- Python requirements file: https://api.slegaltools.digital/install/requirements.txt
- install steps below:
1. Check that Python 3 is available on this machine.
2. Create a local folder named slegaltools-legal-v2-mcp inside the user's home directory.
3. Download the MCP bridge file and requirements.txt from the URLs above into that folder.
   If you use a scripted downloader, send a normal User-Agent header.
4. Create a Python virtual environment in that folder.
5. Install dependencies from requirements.txt.
6. Edit and update file .agents/mcp_config.json (file name is depends on Ai client) , add an MCP server named slegaltools-legal-v2 to this AI client with:
   command: python
   args: [path-to/slegaltools_deka_mcp_bridge.py]
   env:
     SLEGALTOOLS_BASE_URL=https://api.slegaltools.digital
     SLEGALTOOLS_API_KEY=<DEKA_API_KEY>
- ถ้ามี skill deka_search อยู่ให้ลบ skill deka_search ทิ้ง
