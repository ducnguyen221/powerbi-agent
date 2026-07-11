<#
.SYNOPSIS
  Đóng gói thư mục này thành 1 file .zip SẠCH để copy sang máy khác cài ngay.
.DESCRIPTION
  Loại bỏ phần không nên mang đi: .venv (máy nào tự dựng), .env (secrets), .git,
  __pycache__, *.bak.*, *.pyc, và chính các file .zip cũ.
  Bên máy mới: giải nén -> chạy install.ps1 (xem INSTALL.html).
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\pack.ps1
.EXAMPLE
  .\pack.ps1 -OutDir "D:\share" -IncludeEnv   # kèm .env (chỉ khi sang MÁY CỦA CHÍNH BẠN)
.PARAMETER OutDir
  Thư mục xuất file zip. Mặc định: Desktop.
.PARAMETER IncludeEnv
  Kèm cả file .env thật (mặc định KHÔNG — tránh lộ secrets khi chia sẻ).
#>
[CmdletBinding()]
param(
    [string] $OutDir = [Environment]::GetFolderPath('Desktop'),
    [switch] $IncludeEnv
)
$ErrorActionPreference = "Stop"
$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stamp = Get-Date -Format "yyyyMMdd"
$stage = Join-Path $env:TEMP ("pbimcp-pack-" + (Get-Date -Format "yyyyMMddHHmmss"))
$zip   = Join-Path $OutDir "powerbi-mcp-setup-$Stamp.zip"

New-Item -ItemType Directory -Path $stage -Force | Out-Null
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }

$exclDir  = @('.venv', '.git', '__pycache__')
$exclFile = @()
if (-not $IncludeEnv) { $exclFile += '.env' }

Write-Host "[i] Đóng gói từ: $Root" -ForegroundColor Cyan
Get-ChildItem $Root -Force | ForEach-Object {
    if ($_.PSIsContainer) {
        if ($exclDir -contains $_.Name) { return }
        Copy-Item $_.FullName (Join-Path $stage $_.Name) -Recurse -Force
    } else {
        if ($exclFile -contains $_.Name) { return }
        if ($_.Name -like '*.bak.*' -or $_.Name -like '*.pyc' -or $_.Extension -eq '.zip') { return }
        Copy-Item $_.FullName (Join-Path $stage $_.Name) -Force
    }
}
# Dọn __pycache__ lỡ nằm trong thư mục con (vd skill/)
Get-ChildItem $stage -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -Force
Remove-Item $stage -Recurse -Force

$size = "{0:N0} KB" -f ((Get-Item $zip).Length / 1KB)
Write-Host "[OK] Đã tạo gói: $zip  ($size)" -ForegroundColor Green
if (-not $IncludeEnv) { Write-Host "[i] (.env KHÔNG được đóng gói — an toàn để chia sẻ. Dùng -IncludeEnv nếu sang máy của chính bạn.)" -ForegroundColor DarkGray }
Write-Host "[i] Máy mới: giải nén -> mở PowerShell tại thư mục -> .\install.ps1" -ForegroundColor Gray
