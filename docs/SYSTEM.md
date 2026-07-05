# NEXTDAY System Overview

เอกสารต้นฉบับ: `nextday_system_overview.md`

## สถาปัตยกรรม

- **Django MVT** — backend + templates + database
- **Matrix A** (`DressRule`) — เกณฑ์มาตรฐานตามสถานที่ + อุณหภูมิ
- **Matrix B** (`Clothing`) — ตู้เสื้อผ้าจริงของผู้ใช้
- **ML Part 1** — `outfit/ml/pipeline.py` (YOLOv8 + OpenCV K-Means)
- **Recommend Part 2** — `outfit/services/recommendation.py`

## สูตร

```
S(t,b) = 0.6 × Outfit_CBF(t,b) + 0.4 × Score_Color(t,b)
```

## รัน

```powershell
cd "d:\next day-app"
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python manage.py migrate
.\venv\Scripts\python manage.py seed_rules
.\venv\Scripts\python manage.py runserver
```

## OpenWeather (optional)

```powershell
$env:OPENWEATHER_API_KEY = "your-key"
```
