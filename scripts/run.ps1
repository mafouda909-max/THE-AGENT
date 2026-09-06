# THE WAY OUT Agent — تشغيل سريع على Windows
# الاستخدام:
#   .\scripts\run.ps1            # وضع تفاعلي
#   .\scripts\run.ps1 -Once "..." # أمر واحد
#   .\scripts\run.ps1 -Check      # فحص ذاتي
param(
    [string]$Once = "",
    [switch]$Check
)

if ($Check) {
    python agent.py --check
} elseif ($Once -ne "") {
    python agent.py --once $Once
} else {
    python agent.py
}
