<#
.SYNOPSIS
  Gỡ Power BI MCP Bridge khỏi các host. (Chạy ngay trong thư mục cài.)
.EXAMPLE
  .\uninstall.ps1                # gỡ khỏi 3 host + xoá skill đã copy. GIỮ file & .venv & .env.
  .\uninstall.ps1 -RemoveVenv    # gỡ như trên + xoá .venv (giải phóng dung lượng).
#>
[CmdletBinding()]
param(
    [string[]] $Hosts = @("claude", "codex", "antigravity"),
    [switch]   $RemoveVenv
)
$ErrorActionPreference = "Stop"
$Root  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
function Info($m){Write-Host "[i] $m" -ForegroundColor Cyan}
function Ok($m){Write-Host "[OK] $m" -ForegroundColor Green}
function Warn($m){Write-Host "[!] $m" -ForegroundColor Yellow}
function Backup-File($p){ if(Test-Path $p){ Copy-Item $p "$p.bak.$Stamp" -Force; Info "Backup: $p.bak.$Stamp" } }
function Write-Utf8NoBom($Path,$Text){ [System.IO.File]::WriteAllText($Path,$Text,(New-Object System.Text.UTF8Encoding($false))) }
$name = "powerbi-mcp-bridge"

function Remove-FromJson($Path){
    if (-not (Test-Path $Path)) { return }
    Backup-File $Path
    try { $json = (Get-Content $Path -Raw -Encoding UTF8) | ConvertFrom-Json } catch { Warn "Bỏ qua $Path (JSON lỗi)."; return }
    if ($json.mcpServers -and ($json.mcpServers.PSObject.Properties.Name -contains $name)) {
        $json.mcpServers.PSObject.Properties.Remove($name)
        Write-Utf8NoBom $Path ($json | ConvertTo-Json -Depth 40)
        Ok "Đã gỡ '$name' khỏi $Path"
    } else { Info "$Path không chứa '$name'." }
}

if ($Hosts -contains "claude") {
    if (Get-Command claude -ErrorAction SilentlyContinue) { & claude mcp remove $name -s user 2>$null | Out-Null; Ok "Claude: remove qua CLI." }
    else { Remove-FromJson (Join-Path $env:USERPROFILE ".claude.json") }
}
if ($Hosts -contains "antigravity") { Remove-FromJson (Join-Path $env:USERPROFILE ".gemini\antigravity\mcp_config.json") }
if ($Hosts -contains "codex") {
    $cfg = Join-Path $env:USERPROFILE ".codex\config.toml"
    if (Test-Path $cfg) {
        Backup-File $cfg
        $text = Get-Content $cfg -Raw -Encoding UTF8
        $new = [regex]::Replace($text, '(?ms)^\[mcp_servers\.powerbi-mcp-bridge\].*?(?=^\[|\z)', '')
        Write-Utf8NoBom $cfg ($new.TrimEnd() + "`n")
        Ok "Đã gỡ block khỏi $cfg"
    }
}
foreach ($sr in @(".claude\skills\powerbi-mcp", ".codex\skills\powerbi-mcp", ".gemini\antigravity\skills\powerbi-mcp")) {
    $p = Join-Path $env:USERPROFILE $sr
    if (Test-Path $p) { Remove-Item $p -Recurse -Force; Info "Xoá skill: $p" }
}
if ($RemoveVenv) {
    $venv = Join-Path $Root ".venv"
    if (Test-Path $venv) { Remove-Item $venv -Recurse -Force; Ok "Đã xoá .venv" }
}
Ok "Gỡ cài hoàn tất. Khởi động lại host để áp dụng. (Thư mục mã nguồn giữ nguyên.)"
