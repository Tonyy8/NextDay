# ตั้งค่า PostgreSQL สำหรับ NEXTDAY
# รันหลังติดตั้ง PostgreSQL แล้ว: .\database\scripts\setup_postgresql.ps1

$ErrorActionPreference = "Stop"
$RootDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $RootDir

# หา psql
$psqlPaths = @(
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "C:\Program Files\PostgreSQL\15\bin\psql.exe"
)
$psql = $psqlPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $psql) {
    Write-Host "ไม่พบ PostgreSQL (psql)" -ForegroundColor Red
    Write-Host ""
    Write-Host "วิธีติดตั้ง (เลือก 1 วิธี):" -ForegroundColor Yellow
    Write-Host "  1. ดาวน์โหลดจาก https://www.postgresql.org/download/windows/"
    Write-Host "     ติดตั้งแล้วตั้งรหัส postgres user = postgres"
    Write-Host "  2. ใช้ Docker: docker compose up -d"
    Write-Host ""
    exit 1
}

Write-Host "พบ PostgreSQL: $psql" -ForegroundColor Green

$env:PGPASSWORD = "postgres"
& $psql -U postgres -h localhost -p 5432 -tc "SELECT 1 FROM pg_database WHERE datname = 'nextday_db'" | Out-Null
$dbExists = & $psql -U postgres -h localhost -p 5432 -tAc "SELECT 1 FROM pg_database WHERE datname = 'nextday_db'"

if ($dbExists -ne "1") {
    Write-Host "กำลังสร้างฐานข้อมูล nextday_db..."
    & $psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE nextday_db ENCODING 'UTF8';"
    Write-Host "สร้างฐานข้อมูลสำเร็จ" -ForegroundColor Green
} else {
    Write-Host "ฐานข้อมูล nextday_db มีอยู่แล้ว" -ForegroundColor Cyan
}

# อัปเดต .env
$envFile = Join-Path $RootDir ".env"
$content = Get-Content $envFile -Raw
$content = $content -replace "DB_ENGINE=sqlite", "DB_ENGINE=postgresql"
$content = $content -replace "DB_PASSWORD=your_password", "DB_PASSWORD=postgres"
Set-Content $envFile $content -NoNewline

Write-Host "อัปเดต .env เป็น PostgreSQL แล้ว" -ForegroundColor Green
Write-Host "กำลังรัน migrate..."
& ".\venv\Scripts\python.exe" manage.py migrate
Write-Host ""
Write-Host "เสร็จสิ้น! PostgreSQL พร้อมใช้งาน" -ForegroundColor Green
