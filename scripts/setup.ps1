# THE WAY OUT Agent — تجهيز البيئة على Windows (يُشغَّل مرة واحدة)
# الاستخدام:  .\scripts\setup.ps1
$ErrorActionPreference = "Stop"

Write-Host "🔍 فحص Python..." -ForegroundColor Cyan
try {
    $py = python --version 2>&1
    Write-Host "  ✅ $py" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python غير مثبت — ثبّته من https://www.python.org/downloads/ ثم أعد المحاولة." -ForegroundColor Red
    exit 1
}

Write-Host "🔍 فحص Ollama..." -ForegroundColor Cyan
try {
    $ol = ollama --version 2>&1
    Write-Host "  ✅ $ol" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Ollama غير مثبت — ثبّته من https://ollama.com/download ثم نفّذ: ollama run qwen2.5-coder:1.5b" -ForegroundColor Red
    exit 1
}

Write-Host "📦 تثبيت مكتبات Python..." -ForegroundColor Cyan
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Write-Host "⚙️ إنشاء ملف .env من المثال..." -ForegroundColor Cyan
    Copy-Item ".env.example" ".env"
    Write-Host "  ✅ تم إنشاء .env (عدّله لو احتجت)" -ForegroundColor Green
} else {
    Write-Host "  ℹ️ ملف .env موجود — لم نمسه." -ForegroundColor Yellow
}

Write-Host "🧪 فحص ذاتي سريع..." -ForegroundColor Cyan
python agent.py --check

Write-Host ""
Write-Host "🎉 التجهيز اكتمل! شغّل الإيجنت بـ:  python agent.py" -ForegroundColor Green
