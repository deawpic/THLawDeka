---
name: api_key_setup
description: ตั้งค่า  API_KEY
---
# Prerequisites & Authentication
 - ระบบตรวจสอบไฟล์ .env ใน Root Directory หากยังไม่มีไฟล์ .env ให้สร้างไฟล์ดังกล่าวขึ้นมาใหม่ทันที
 - ไฟล์ .env เก็บค่า  DEKA_API_KEY และ FC_API_KEY แยกบรรทัดกันชัดเจน ตามตัวอย่าง:
      DEKA_API_KEY=
      FC_API_KEY=
- ถ้า API_KEY ว่างให้ถาม user ดังนี้
    1. เพิ่ม slegaltools api key.  (ถ้าเลือกข้อนี้ให้ถามให้ user  paste key แล้วนำค่าไปเก็บใน DEKA_API_KEY )
    2. เพิ่ม fourcorners api key. (ถ้าเลือกข้อนี้ให้ถามให้ user  paste key แล้วนำค่าไปเก็บใน FC_API_KEY )
    3. ข้ามไปก่อน
