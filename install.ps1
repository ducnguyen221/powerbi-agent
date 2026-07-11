<#
.SYNOPSIS
  Bộ cài "một phát chạy ngay" cho Power BI MCP Bridge — IN-PLACE.
  Thư mục này VỪA là bản đang chạy, VỪA là bộ cài mang sang máy khác.

.DESCRIPTION
  Cài đặt NGAY TẠI thư mục chứa file này (không sao chép đi đâu khác):
    - Tạo / kiểm tra venv Python + cài dependencies.
    - Dò ADOMD.NET (đa phiên bản).
    - Đăng ký MCP vào Claude Code / Codex / Antigravity, trỏ về CHÍNH thư mục này
      (merge vào cấu hình có sẵn, có backup .bak, không xoá server khác).
    - Copy skill cho từng host.
  KHÔNG bao giờ đụng .env (secrets). Chạy lại nhiều lần an toàn (idempotent).

.EXAMPLE
  # Cách dùng chuẩn — mở PowerShell tại thư mục này rồi chạy:
  powershell -ExecutionPolicy Bypass -File .\install.ps1

.EXAMPLE
  # Mang sang máy mới: copy CẢ thư mục (bỏ .venv và .env) tới
  # %USERPROFILE%\.mcp\powerbi-mcp rồi chạy lại lệnh trên. venv tự dựng lại.

.PARAMETER Hosts
  Host cần đăng ký: claude, codex, antigravity. Mặc định cả ba.
.PARAMETER SkipVenv
  Bỏ qua tạo venv / cài pip (chỉ cập nhật cấu hình host).
.PARAMETER SkipHosts
  Chỉ dựng venv, không đụng cấu hình host nào.
#>
[CmdletBinding()]
param(
    [string[]] $Hosts = @("claude", "codex", "antigravity"),
    [switch]   $SkipVenv,
    [switch]   $SkipHosts
)

$ErrorActionPreference = "Stop"
$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"

function Info($m)  { Write-Host "[i] $m" -ForegroundColor Cyan }
function Ok($m)    { Write-Host "[OK] $m" -ForegroundColor Green }
function Warn($m)  { Write-Host "[!] $m" -ForegroundColor Yellow }
function Err($m)   { Write-Host "[X] $m" -ForegroundColor Red }
function Step($m)  { Write-Host "`n=== $m ===" -ForegroundColor Magenta }

# Ghi file UTF-8 KHÔNG BOM (an toàn cho JSON/TOML)
function Write-Utf8NoBom([string]$Path, [string]$Text) {
    [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false)))
}
function Backup-File([string]$Path) {
    if (Test-Path $Path) { Copy-Item $Path "$Path.bak.$Stamp" -Force; Info "Đã sao lưu: $Path.bak.$Stamp" }
}

Write-Host @"

  ____                        ____ ___   __  __  ____ ____
 |  _ \ _____      _____ _ __| __ )_ _| |  \/  |/ ___|  _ \
 | |_) / _ \ \ /\ / / _ \ '__|  _ \| |  | |\/| | |   | |_) |
 |  __/ (_) \ V  V /  __/ |  | |_) | |  | |  | | |___|  __/
 |_|   \___/ \_/\_/ \___|_|  |____/___| |_|  |_|\____|_|

  Power BI MCP Bridge - Installer (in-place)
"@ -ForegroundColor Blue

Info "Thư mục cài (= vị trí MCP server): $Root"
Info "Host đăng ký: $($Hosts -join ', ')"

$serverPath = Join-Path $Root "mcp_server_powerbi.py"
if (-not (Test-Path $serverPath)) { Err "Không thấy mcp_server_powerbi.py cạnh install.ps1. Dừng."; exit 1 }

# ---- .env: tạo từ mẫu nếu chưa có, KHÔNG ghi đè (giữ secrets) ----
$envFile = Join-Path $Root ".env"
$envEx   = Join-Path $Root ".env.example"
if ((-not (Test-Path $envFile)) -and (Test-Path $envEx)) {
    Copy-Item $envEx $envFile -Force
    Warn ".env chưa có -> tạo từ mẫu. Điền vào nếu cần Power BI Service (Cloud): $envFile"
}

# ============================================================
# 1) PYTHON VENV + DEPENDENCIES
# ============================================================
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"

if ($SkipVenv) {
    Warn "Bỏ qua venv/pip (-SkipVenv)."
} else {
    Step "1/3 Python venv + dependencies"

    function Get-Python {
        foreach ($c in @(@("py",@("-3.12")),@("py",@("-3.11")),@("py",@("-3")),@("python",@()),@("python3",@()))) {
            $exe=$c[0]; $pre=$c[1]
            if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
            try {
                $ver = & $exe @pre -c "import sys;print('%d.%d'%sys.version_info[:2])" 2>$null
                if ($ver -match '^(\d+)\.(\d+)$' -and [int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 11) {
                    return ,@($exe,$pre,$ver)
                }
            } catch {}
        }
        return $null
    }

    # venv có sẵn nhưng HỎNG (copy từ máy khác) -> dựng lại
    $needBuild = $true
    if (Test-Path $venvPy) {
        & $venvPy --version *> $null
        if ($LASTEXITCODE -eq 0) { $needBuild = $false; Info "venv hợp lệ -> tái sử dụng." }
        else { Warn "venv không chạy được (có thể copy từ máy khác) -> dựng lại."; Remove-Item (Join-Path $Root ".venv") -Recurse -Force }
    }

    if ($needBuild) {
        $py = Get-Python
        if (-not $py) { Err "Không thấy Python >= 3.11. Cài từ https://www.python.org/downloads/ (tick 'Add to PATH') rồi chạy lại."; exit 1 }
        Ok "Dùng Python $($py[2])"
        & $py[0] @($py[1]) -m venv (Join-Path $Root ".venv")
        if ($LASTEXITCODE -ne 0) { Err "Tạo venv thất bại."; exit 1 }
    }

    Info "Nâng cấp pip..."
    & $venvPy -m pip install --upgrade pip --quiet

    $req   = Join-Path $Root "requirements.txt"
    $loose = Join-Path $Root "requirements.loose.txt"
    Info "Cài dependencies (requirements.txt)..."
    & $venvPy -m pip install -r $req --quiet
    if ($LASTEXITCODE -ne 0 -and (Test-Path $loose)) {
        Warn "Bản pin lỗi -> thử requirements.loose.txt."
        & $venvPy -m pip install -r $loose --quiet
    }
    if ($LASTEXITCODE -ne 0) { Err "Cài dependencies thất bại."; exit 1 }
    Ok "Dependencies sẵn sàng."
}

# ============================================================
# 2) KIỂM TRA ADOMD.NET
# ============================================================
Step "2/3 Kiểm tra ADOMD.NET"
$adomdDll = "Microsoft.AnalysisServices.AdomdClient.dll"
$pf = ${env:ProgramFiles}; if (-not $pf) { $pf="C:\Program Files" }
$pf86 = ${env:ProgramFiles(x86)}; if (-not $pf86) { $pf86="C:\Program Files (x86)" }
$globs = @(
    (Join-Path $pf   "Microsoft SQL Server Management Studio*\*\Common7\IDE"),
    (Join-Path $pf   "Microsoft SQL Server Management Studio*\Common7\IDE"),
    (Join-Path $pf86 "Microsoft SQL Server Management Studio*\Common7\IDE"),
    (Join-Path $pf   "Microsoft.NET\ADOMD.NET\*"),
    (Join-Path $pf86 "Microsoft.NET\ADOMD.NET\*"),
    (Join-Path $pf   "Microsoft SQL Server\*\SDK\Assemblies")
)
$found = $null
foreach ($g in $globs) {
    $hit = Get-ChildItem -Path $g -Filter $adomdDll -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($hit) { $found = $hit.FullName; break }
}
if ($found) { Ok "Tìm thấy ADOMD.NET: $found" }
else {
    Warn "KHÔNG thấy ADOMD.NET. Tool Cloud vẫn chạy; tool LOCAL sẽ lỗi tới khi cài."
    Warn "  Cài 'Analysis Services client libraries': https://learn.microsoft.com/analysis-services/client-libraries"
    Warn "  Hoặc đặt ADOMD_LIB_DIR trong $envFile tới thư mục chứa $adomdDll."
}

# ============================================================
# 3) ĐĂNG KÝ MCP VÀO HOST (trỏ về CHÍNH thư mục này)
# ============================================================
$pyJson  = $venvPy.Replace('\','/')
$srvJson = $serverPath.Replace('\','/')

function Merge-McpJson([string]$Path) {
    if (-not (Test-Path $Path)) {
        $dir = Split-Path -Parent $Path
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Write-Utf8NoBom $Path "{`n  `"mcpServers`": {}`n}"
        Info "Tạo mới $Path"
    }
    Backup-File $Path
    try {
        $raw = Get-Content $Path -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) { $raw = "{}" }
        $json = $raw | ConvertFrom-Json
    } catch { Err "Đọc JSON $Path lỗi ($($_.Exception.Message)). Có .bak, bỏ qua."; return }
    if (-not $json) { $json = [PSCustomObject]@{} }
    if (-not ($json.PSObject.Properties.Name -contains "mcpServers")) {
        $json | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([PSCustomObject]@{})
    }
    $entry = [PSCustomObject]@{
        type="stdio"; command=$pyJson; args=@("-u",$srvJson); env=[PSCustomObject]@{ PYTHONUNBUFFERED="1" }
    }
    if ($json.mcpServers.PSObject.Properties.Name -contains "powerbi-mcp-bridge") {
        $json.mcpServers."powerbi-mcp-bridge" = $entry
    } else {
        $json.mcpServers | Add-Member -NotePropertyName "powerbi-mcp-bridge" -NotePropertyValue $entry
    }
    Write-Utf8NoBom $Path ($json | ConvertTo-Json -Depth 40)
    Ok "Đã ghi cấu hình MCP vào $Path"
}

function Register-Claude {
    Info "Claude Code..."
    if (Get-Command claude -ErrorAction SilentlyContinue) {
        & claude mcp remove powerbi-mcp-bridge -s user 2>$null | Out-Null
        & claude mcp add powerbi-mcp-bridge -s user -e PYTHONUNBUFFERED=1 -- $venvPy -u $serverPath
        if ($LASTEXITCODE -eq 0) { Ok "Claude: đăng ký qua 'claude mcp add' (scope user)."; return }
        Warn "claude CLI lỗi -> sửa .claude.json trực tiếp."
    } else { Warn "Không thấy 'claude' CLI -> sửa .claude.json trực tiếp." }
    Merge-McpJson (Join-Path $env:USERPROFILE ".claude.json")
}
function Register-Antigravity { Info "Antigravity..."; Merge-McpJson (Join-Path $env:USERPROFILE ".gemini\antigravity\mcp_config.json") }
function Register-Codex {
    Info "Codex..."
    $cfg = Join-Path $env:USERPROFILE ".codex\config.toml"
    $dir = Split-Path -Parent $cfg
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $block = @"
[mcp_servers.powerbi-mcp-bridge]
command = "$pyJson"
args = ["-u", "$srvJson"]
env = { PYTHONUNBUFFERED = "1" }
"@
    if (-not (Test-Path $cfg)) { Write-Utf8NoBom $cfg $block; Ok "Tạo mới $cfg + block MCP."; return }
    Backup-File $cfg
    $text = Get-Content $cfg -Raw -Encoding UTF8
    if ($text -match '(?m)^\[mcp_servers\.powerbi-mcp-bridge\]') {
        # Cập nhật block cũ (đường dẫn có thể đổi khi sang máy mới)
        $pattern = '(?ms)^\[mcp_servers\.powerbi-mcp-bridge\].*?(?=^\[|\z)'
        $text = [regex]::Replace($text, $pattern, ($block.TrimEnd() + "`n`n"))
        Write-Utf8NoBom $cfg ($text.TrimEnd() + "`n")
        Ok "Cập nhật block MCP trong $cfg"
    } else {
        if ($text -notmatch "`n$") { $text += "`n" }
        Write-Utf8NoBom $cfg ($text + "`n" + $block)
        Ok "Đã thêm block MCP vào $cfg"
    }
}
function Install-Skill([string]$SkillRoot) {
    $src = Join-Path $Root "skill\powerbi-mcp\SKILL.md"
    if (-not (Test-Path $src)) { return }
    $dst = Join-Path $SkillRoot "powerbi-mcp"
    if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
    Copy-Item $src (Join-Path $dst "SKILL.md") -Force
    Info "Skill -> $dst"
}

if ($SkipHosts) {
    Step "3/3 Đăng ký host"; Warn "Bỏ qua đăng ký host (-SkipHosts)."
} else {
    Step "3/3 Đăng ký MCP vào host"
    if ($Hosts -contains "claude")      { Register-Claude;      Install-Skill (Join-Path $env:USERPROFILE ".claude\skills") }
    if ($Hosts -contains "codex")       { Register-Codex;       Install-Skill (Join-Path $env:USERPROFILE ".codex\skills") }
    if ($Hosts -contains "antigravity") { Register-Antigravity; Install-Skill (Join-Path $env:USERPROFILE ".gemini\antigravity\skills") }
}

# ---- Smoke test ----
if ((-not $SkipVenv) -and (Test-Path $venvPy)) {
    Step "Kiểm thử nhanh (import)"
    $probe = "import importlib;[importlib.import_module(m) for m in ('mcp.server.fastmcp','pyadomd','pandas','msal','dotenv','tabulate')];print('IMPORTS_OK')"
    $out = & $venvPy -c $probe 2>&1
    if ($out -match "IMPORTS_OK") { Ok "Thư viện import OK. Server sẵn sàng." } else { Warn "Import có vấn đề:"; Write-Host $out }
}

Write-Host "`n=============================================" -ForegroundColor Green
Ok "HOÀN TẤT."
Write-Host @"

Bước cuối: KHỞI ĐỘNG LẠI host để nạp MCP (Claude: 'claude mcp list' để kiểm).
Server tại : $Root
Gỡ cài     : .\uninstall.ps1
"@ -ForegroundColor Gray
