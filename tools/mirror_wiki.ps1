# Mirror HY MHFZ wiki to local. ASCII-only for PS 5.1 compatibility.
$ErrorActionPreference = "Stop"

$Base   = "https://mhwiki.axibug.com/HY_MHFZ_WIKI/"
$Root   = Join-Path (Split-Path $PSScriptRoot -Parent) "tools\mhf-wiki-mirror"
$Curl   = "C:\Windows\System32\curl.exe"

New-Item -ItemType Directory -Force -Path $Root | Out-Null

$queue = New-Object System.Collections.Generic.Queue[string]
$done  = New-Object System.Collections.Generic.HashSet[string]
$failed = New-Object System.Collections.Generic.List[string]
$count = 0

function Normalize-Url([string]$u, [string]$basePath) {
    $u = $u -replace '\?.*$', '' -replace '#.*$', ''
    $u = $u -replace '@[0-9A-Fa-f]+$', ''
    if ($u -match '[<>:"|*\x00-\x1f]') { return $null }
    if ($u -match '^https?://') {
        if ($u -notmatch '^https?://mhwiki\.axibug\.com/HY_MHFZ_WIKI/') { return $null }
        return $u -replace '^https?://mhwiki\.axibug\.com', ''
    }
    if ($u -eq '' -or $u -match '^(javascript:|mailto:|data:)') { return $null }
    $combined = if ($u.StartsWith('/')) { $u } else { "$basePath$u" }
    $parts = New-Object System.Collections.Generic.List[string]
    foreach ($seg in ($combined -split '/')) {
        if ($seg -eq '..') {
            if ($parts.Count -gt 0) { $parts.RemoveAt($parts.Count - 1) }
        } elseif ($seg -ne '.' -and $seg -ne '') {
            $parts.Add($seg)
        }
    }
    if ($parts.Count -eq 0) { return $null }
    return ($parts -join '/')
}

# Extract URLs from HTML (href/src attributes)
function Get-HtmlLinks([string]$html) {
    $links = New-Object System.Collections.Generic.HashSet[string]
    foreach ($m in [regex]::Matches($html, '(?:href|src)\s*=\s*["'']([^"'']+)["'']', 'IgnoreCase')) {
        $u = $m.Groups[1].Value
        if ($u -match '^(https?:)?//' -and $u -notmatch 'mhwiki\.axibug\.com/HY_MHFZ_WIKI') { continue }
        $null = $links.Add($u)
    }
    return $links
}

# Extract paths from JS (getLink("...") calls and bare relative paths)
function Get-JsLinks([string]$js) {
    $links = New-Object System.Collections.Generic.HashSet[string]
    foreach ($m in [regex]::Matches($js, 'getLink\(\s*["'']([^"'']+)["'']\s*\)', 'IgnoreCase')) {
        $null = $links.Add($m.Groups[1].Value)
    }
    foreach ($m in [regex]::Matches($js, '["'']([a-zA-Z0-9_\-/]+\.(?:html?|js|css|png|jpe?g|gif|webp|ico))["'']')) {
        $null = $links.Add($m.Groups[1].Value)
    }
    return $links
}

function Save-Page([string]$relUrl) {
    if ($relUrl -eq '') { $relUrl = 'index.html' }
    $relUrl = $relUrl.TrimEnd('/')
    $path = Join-Path $Root ($relUrl -replace '/', '\')
    $dir = Split-Path $path -Parent
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    & $Curl -s --fail -o $path "$Base$relUrl" 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return $path
}

function Enqueue-Links($links, [string]$basePath) {
    foreach ($raw in $links) {
        $norm = Normalize-Url $raw $basePath
        if ($null -eq $norm) { continue }
        if ($done.Contains($norm)) { continue }
        $null = $done.Add($norm)
        $queue.Enqueue($norm)
    }
}

$queue.Enqueue("")
$null = $done.Add("")

$count = 0
while ($queue.Count -gt 0) {
    $rel = $queue.Dequeue()
    $path = Save-Page $rel
    if ($null -eq $path) {
        $failed.Add($rel)
        continue
    }
    $count++
    if ($count % 25 -eq 0) {
        Write-Host "fetched $count ..."
    }
    $ext = [System.IO.Path]::GetExtension($path).ToLower()
    $basePath = if ($rel.Contains('/')) { ($rel -replace '[^/]*$', '') } else { '' }
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $content = [System.Text.Encoding]::UTF8.GetString($bytes)

    if ($ext -eq '.js') {
        # getLink() URLs are site-root-relative; bare paths also root-relative here
        Enqueue-Links (Get-JsLinks $content) ''
    } elseif ($ext -in @('.html', '.htm')) {
        Enqueue-Links (Get-HtmlLinks $content) $basePath
        Enqueue-Links (Get-JsLinks $content) ''
    }
}

Write-Host "=== done: $count files, $($failed.Count) failed ==="
if ($failed.Count -gt 0) {
    Write-Host "failed:"
    $failed | ForEach-Object { Write-Host "  $_" }
}
