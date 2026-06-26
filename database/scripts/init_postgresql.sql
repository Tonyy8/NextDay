-- สร้างฐานข้อมูล PostgreSQL สำหรับ Next Day App
-- รันคำสั่งนี้ใน psql หรือ pgAdmin

CREATE DATABASE nextday_db
    WITH ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- หมายเหตุ: Django ORM จะสร้างตารางอัตโนมัติผ่าน migrate
-- ตารางหลัก: clothing_analysis
