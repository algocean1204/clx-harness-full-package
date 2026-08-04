<#
  Clean agent harness installer for Windows — FIRST-CLASS (not best-effort).

  Activation is per-OS: this script applies common/ + windows-harness/ only and skips
  macos-harness/. It rewrites the shipped hook wiring so every registered hook is
  Windows-executable: bash hooks are swapped for their cross-platform Python ports
  (windows-harness/hooks/*.py) and every hook command is prefixed with the detected
  Python launcher. If no Python is found, hooks are left UNREGISTERED (never broken)
  and listed as inactive. It configures no git remote and touches no credentials.

  Usage:
    powershell -ExecutionPolicy Bypass -File windows-harness\install.ps1 -Check
    powershell -ExecutionPolicy Bypass -File windows-harness\install.ps1 -Apply [-Force]
#>
[CmdletBinding()]
param([switch]$Check, [switch]$Apply, [switch]$Force)

$ErrorActionPreference = 'Stop'

# Windows-only by design: fail with a clear message elsewhere (macOS/Linux use install.sh).
if (-not [string]::IsNullOrEmpty($env:CLX_FORCE_PROFILE)) {
    $profileDir = $env:CLX_FORCE_PROFILE   # test/CI escape hatch, never set by real installs
} elseif ($IsWindows -ne $false -and -not [string]::IsNullOrEmpty($env:USERPROFILE)) {
    $profileDir = $env:USERPROFILE
} else {
    Write-Host 'install.ps1 is Windows-only. On macOS/Linux run: bash install.sh --check' -ForegroundColor Yellow
    exit 1
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$common   = Join-Path $repoRoot 'common'
$winHooks = Join-Path $PSScriptRoot 'hooks'
$homeFwd  = $profileDir -replace '\\', '/'      # forward slashes: JSON-safe, accepted by the tools

# bash hooks that ship a cross-platform Python port under windows-harness/hooks/
$ported = @('auto-format', 'precompact-guard', 'session-intent-archive', 'statusline')

if (-not ($Check -or $Apply)) { Write-Host 'usage: install.ps1 -Check | -Apply [-Force]'; exit 2 }
foreach ($d in 'claude', 'codex', 'agents', 'grok', 'local-bin') {
  if (-not (Test-Path (Join-Path $common $d))) { Write-Error "common\$d missing - run from repo root"; exit 1 }
}

# "py -3" is two tokens, "python" is one. $a[1..($a.Count-1)] on a one-element array indexes 1..0
# and hands the element back, so the tail is built behind an explicit Count guard everywhere.
function Split-Launcher([string]$launcher) {
  return @($launcher -split '\s+' | Where-Object { $_ })
}

function Launcher-Args($parts) {
  if ($parts.Count -gt 1) { return @($parts[1..($parts.Count - 1)]) }
  return @()
}

function Find-Python {
  foreach ($c in @('py -3', 'python', 'python3')) {
    $parts = Split-Launcher $c
    if (Get-Command $parts[0] -ErrorAction SilentlyContinue) {
      try {
        & $parts[0] @((Launcher-Args $parts) + '--version') 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return $c }
      } catch {}
    }
  }
  return $null
}

$PY = Find-Python
$map = @(
  @{ Src = 'claude'; Dst = (Join-Path $profileDir '.claude') },
  @{ Src = 'codex';  Dst = (Join-Path $profileDir '.codex')  },
  @{ Src = 'agents'; Dst = (Join-Path $profileDir '.agents') },
  @{ Src = 'grok';   Dst = (Join-Path $profileDir '.grok')   },
  @{ Src = 'local-bin'; Dst = (Join-Path $profileDir '.local\bin') }
)
function Test-NonEmpty($p) { (Test-Path $p) -and ((Get-ChildItem -Force $p -EA SilentlyContinue | Measure-Object).Count -gt 0) }

$skipMac = 'macos-harness\ (launchd job, disk-guard.sh, personal push examples) - macOS only'

# What is already on this machine decides what the install must PRESERVE. Printed in both
# modes so nothing about an existing setup changes silently.
function Show-DetectedEnvironment {
  Write-Host 'detected environment:'
  Write-Host ("  os          : Windows {0} {1}" -f [Environment]::OSVersion.Version, $env:PROCESSOR_ARCHITECTURE)
  Write-Host ("  python      : {0}" -f ($(if ($PY) { $PY } else { 'NOT FOUND - hooks stay inactive' })))
  $git = (Get-Command git -EA SilentlyContinue)
  Write-Host ("  git         : {0}" -f ($(if ($git) { $git.Source } else { 'MISSING (required)' })))
  foreach ($cli in @('claude', 'codex', 'grok', 'hermes-call')) {
    $found = (Get-Command $cli -EA SilentlyContinue)
    Write-Host ("  {0,-12}: {1}" -f $cli,
      ($(if ($found) { $found.Source } else { 'not installed - features that need it stay off' })))
  }
  foreach ($m in $map) {
    if (Test-NonEmpty $m.Dst) {
      $n = (Get-ChildItem -Recurse -File -Force $m.Dst -EA SilentlyContinue | Measure-Object).Count
      Write-Host ("  {0,-12}: EXISTING ({1} files) - merged, never wiped" -f (Split-Path $m.Dst -Leaf), $n)
    } else {
      Write-Host ("  {0,-12}: new" -f (Split-Path $m.Dst -Leaf))
    }
  }
  foreach ($f in @("$profileDir\.claude\auth.json", "$profileDir\.claude\.credentials.json", "$profileDir\.codex\auth.json")) {
    if (Test-Path $f) { Write-Host ("  auth        : {0} present - left untouched" -f (Split-Path $f -Leaf)) }
  }
  if (Test-Path "$profileDir\.claude\settings.json") {
    Write-Host '  settings    : existing settings.json - YOUR keys are kept, our hooks are added'
  }
  if (Test-Path "$profileDir\.agents\user") {
    Write-Host '  user context: existing .agents\user - filled files are never overwritten'
  }
}

function Merge-GrokConfig([string]$Target, [string]$Previous) {
  $profileLine = [System.IO.File]::ReadAllLines($Target) |
    Where-Object { $_ -match '^\s*profile\s*=' } | Select-Object -First 1
  if (-not $profileLine) { throw 'common\grok\config.toml is missing [sandbox] profile' }

  $text = [System.IO.File]::ReadAllText($Previous).TrimEnd([char[]]"`r`n")
  $lines = if ($text) { [regex]::Split($text, '\r?\n') } else { @() }
  $output = [System.Collections.Generic.List[string]]::new()
  $inSandbox = $false
  $foundSandbox = $false
  $profileSet = $false
  foreach ($line in $lines) {
    if ($line -match '^\s*\[') {
      if ($inSandbox -and -not $profileSet) { $output.Add($profileLine); $profileSet = $true }
      $inSandbox = $line -match '^\s*\[sandbox\]\s*(?:#.*)?$'
      if ($inSandbox) { $foundSandbox = $true; $profileSet = $false }
      $output.Add($line)
    } elseif ($inSandbox -and $line -match '^\s*profile\s*=') {
      if (-not $profileSet) { $output.Add($profileLine); $profileSet = $true }
    } else {
      $output.Add($line)
    }
  }
  if ($inSandbox -and -not $profileSet) { $output.Add($profileLine) }
  if (-not $foundSandbox) {
    if ($output.Count -gt 0 -and $output[$output.Count - 1]) { $output.Add('') }
    $output.Add('[sandbox]')
    $output.Add($profileLine)
  }
  [System.IO.File]::WriteAllText($Target, [string]::Join([Environment]::NewLine, $output) + [Environment]::NewLine)
  Write-Host 'config.toml: merged - your Grok settings kept, sandbox profile updated'
}

if ($Check) {
  Write-Host 'clx-harness-full-package installer (Windows) - DRY RUN'
  Write-Host "source : $common"
  Write-Host "target : $profileDir"
  Write-Host ''
  Show-DetectedEnvironment
  Write-Host ''
  Write-Host 'Would copy (merge; overwrites matching files, never deletes):'
  $needForce = $false
  foreach ($m in $map) {
    $state = 'new'
    if (Test-NonEmpty $m.Dst) { $state = 'EXISTS/non-empty'; if ($m.Dst -like '*\.claude') { $needForce = $true } }
    Write-Host ("  common\{0}\ -> {1}  [{2}]" -f $m.Src, $m.Dst, $state)
  }
  Write-Host "  windows-harness\hooks\*.py -> $profileDir\.claude\hooks\ (cross-platform ports of the bash hooks)"
  Write-Host ''
  Write-Host "Would materialize __CLX_HOME__ -> $homeFwd (forward slashes)"
  if ($PY) {
    Write-Host "Would register all hooks via '$PY' (bash hooks -> their .py ports; python3 -> '$PY')"
  } else {
    Write-Host 'Would register NO hooks (Python not found) and remove statusLine - install Python 3 and re-run'
  }
  Write-Host "Skipped: $skipMac"
  Write-Host 'Will NOT configure any git remote, push, or touch credentials.'
  if ($needForce -and -not $Force) { Write-Host ''; Write-Host 'NOTE: ~\.claude is non-empty. -Apply refuses without -Force.' }
  exit 0
}

# ---- Apply ----
if ((Test-NonEmpty $map[0].Dst) -and -not $Force) {
  Write-Error "$($map[0].Dst) exists and is non-empty. Re-run with -Force to merge (never deletes)."
  exit 1
}

Show-DetectedEnvironment
Write-Host ''

# An existing settings.json is the user's own configuration — snapshot it so it can be merged
# back after the copy (their permissions/env/model pin survive; our hooks get registered).
$liveSettings = Join-Path $profileDir '.claude\settings.json'
$prevSettings = $null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (Test-Path $liveSettings) {
  $prevSettings = [System.IO.Path]::GetTempFileName()
  Copy-Item $liveSettings $prevSettings -Force
  Copy-Item $liveSettings ("{0}.pre-clx-{1}" -f $liveSettings, $stamp) -Force
}

$liveGrokConfig = Join-Path $profileDir '.grok\config.toml'
$prevGrokConfig = $null
if (Test-Path $liveGrokConfig) {
  $prevGrokConfig = [System.IO.Path]::GetTempFileName()
  Copy-Item $liveGrokConfig $prevGrokConfig -Force
  Copy-Item $liveGrokConfig ("{0}.pre-clx-{1}" -f $liveGrokConfig, $stamp) -Force
}

# Copy-Item carries the ReadOnly attribute across. A source unpacked from a read-only share or
# archive would install read-only copies, and the token materialization below then fails with
# UnauthorizedAccessException half-way. These files are the user's own config now — clear it.
function Clear-ReadOnly([string]$Root) {
  if (-not (Test-Path $Root)) { return }
  Get-ChildItem -Path $Root -Recurse -File -Force -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.IsReadOnly) { try { $_.IsReadOnly = $false } catch { } }
  }
}

foreach ($m in $map) {
  New-Item -ItemType Directory -Force -Path $m.Dst | Out-Null
  if ($m.Src -eq 'agents') {
    # agents\user\ ships as an EMPTY template; once filled in it is the user's. Stage a copy
    # WITHOUT user\ first (same shape as install.sh) so no-clobber never depends on -Exclude
    # semantics under -Recurse, then add the template files one by one, skipping any that exist.
    $stage = Join-Path ([System.IO.Path]::GetTempPath()) ("clx-agents-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    Copy-Item -Path (Join-Path $common 'agents\*') -Destination $stage -Recurse -Force
    $stagedUser = Join-Path $stage 'user'
    if (Test-Path $stagedUser) { Remove-Item -Recurse -Force $stagedUser }
    Copy-Item -Path (Join-Path $stage '*') -Destination $m.Dst -Recurse -Force
    Remove-Item -Recurse -Force $stage

    $userSrc = Join-Path $common 'agents\user'
    $userDst = Join-Path $m.Dst 'user'
    if (Test-Path $userSrc) {
      Get-ChildItem -Path $userSrc -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($userSrc.Length).TrimStart('\')
        $target = Join-Path $userDst $rel
        if (-not (Test-Path $target)) {
          New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
          Copy-Item -Path $_.FullName -Destination $target
        }
      }
    }
    Clear-ReadOnly $m.Dst
    Write-Host "installed: common\agents\ -> $($m.Dst) (user\ template: existing files kept)"
    continue
  }
  Copy-Item -Path (Join-Path $common ($m.Src + '\*')) -Destination $m.Dst -Recurse -Force
  Clear-ReadOnly $m.Dst
  Write-Host "installed: common\$($m.Src)\ -> $($m.Dst)"
}

if ($prevGrokConfig -and (Test-Path $liveGrokConfig)) {
  Merge-GrokConfig $liveGrokConfig $prevGrokConfig
  Remove-Item $prevGrokConfig -Force -EA SilentlyContinue
}

# Fold the user's previous settings back in — before token materialization, so merged hook
# paths still get their __CLX_HOME__ resolved below. Dedup compares the MATERIALIZED form,
# otherwise a re-install would register every hook a second time.
if ($prevSettings -and (Test-Path $liveSettings) -and $PY) {
  $mergeScript = @'
import json, sys
target_path, previous_path, home = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    live = json.load(open(previous_path, encoding="utf-8"))
    shipped = json.load(open(target_path, encoding="utf-8"))
except Exception:
    sys.exit(0)
merged = dict(shipped)
for key_, value in live.items():
    if key_ != "hooks":
        merged[key_] = value
def key(hook):
    norm = {k: (v.replace("__CLX_HOME__", home) if isinstance(v, str) else v)
            for k, v in hook.items()}
    return json.dumps(norm, sort_keys=True)
hooks, seen = {}, {}
for source in (shipped.get("hooks", {}), live.get("hooks", {})):
    for event, entries in source.items():
        for entry in entries:
            fresh = [h for h in entry.get("hooks", []) if key(h) not in seen.setdefault(event, set())]
            for h in fresh:
                seen[event].add(key(h))
            if fresh:
                hooks.setdefault(event, []).append({**entry, "hooks": fresh})
merged["hooks"] = hooks
json.dump(merged, open(target_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open(target_path, "a", encoding="utf-8").write("\n")
print("settings.json: merged - your keys kept, harness hooks added")
'@
  $mergeFile = [System.IO.Path]::GetTempFileName() + '.py'
  Set-Content -Path $mergeFile -Value $mergeScript -Encoding UTF8
  & $PY $mergeFile $liveSettings $prevSettings $homeFwd
  Remove-Item $mergeFile, $prevSettings -Force -EA SilentlyContinue
}

# Cross-platform hook ports land alongside the shipped Python hooks.
$claudeHooks = Join-Path $profileDir '.claude\hooks'
New-Item -ItemType Directory -Force -Path $claudeHooks | Out-Null
Copy-Item -Path (Join-Path $winHooks '*.py') -Destination $claudeHooks -Force
# Same ReadOnly carry-over as the tree copies above, and it matters MORE here: the token
# materialization below walks .claude and rewrites every text file, so a read-only .py hook
# throws UnauthorizedAccessException half-way through the install.
Clear-ReadOnly $claudeHooks
Write-Host "installed: windows-harness\hooks\*.py -> $claudeHooks"

# Materialize __CLX_HOME__ -> profile path (forward slashes) in every installed text file.
$token = '__CLX_HOME__'
foreach ($m in $map) {
  Get-ChildItem -Recurse -File $m.Dst | ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    if ($bytes -contains 0) { return }                       # skip binary
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    if ($text.Contains($token)) {
      [System.IO.File]::WriteAllText($_.FullName, $text.Replace($token, $homeFwd))
    }
  }
}
Write-Host "materialized __CLX_HOME__ -> $homeFwd"

# Rewrite hook command strings so they execute on Windows.
$settings = Join-Path $profileDir '.claude\settings.json'
$codexHooks = Join-Path $profileDir '.codex\hooks.json'

if ($PY) {
  # settings.json: bash hooks -> their .py ports, then wrap every hooks/*.py command with the launcher.
  $t = [System.IO.File]::ReadAllText($settings)
  $t = $t -replace '(/\.claude/hooks/(auto-format|precompact-guard|session-intent-archive|statusline))\.sh', '$1.py'
  # browser-audit-hook.sh is a cheap sh PREFILTER in front of browser-audit.py, which is already
  # cross-platform. There is nothing to port: call the Python directly and let it do its own
  # filtering. Without this the three registrations stayed as raw .sh and errored on every tool
  # call, under a README promising "every registered hook runs on Windows".
  $t = $t -replace '/\.claude/hooks/browser-audit-hook\.sh''?\s+(pre|post)', '/.claude/hooks/browser-audit.py hook-$1'
  # POSIX device redirect: meaningless on Windows, and it also defeated the launcher wrap below,
  # which required the command to END at the .py.
  $t = $t -replace '\s*>\s*/dev/null', ''
  # The shipped commands are single-quoted (POSIX shells need that when $HOME has a space).
  # Windows has no such quoting, and the launcher form below already double-quotes the path,
  # so strip the optional single quotes while capturing — otherwise they end up nested.
  # match BOTH slash styles: a merged-in entry from an earlier install can carry C:\Users\...\x.py,
  # and leaving it unprefixed means Windows never runs that hook
  # (…\.py)(ARGS)? — the old form required the command to end at the .py, so every registration
  # carrying arguments (`browser-audit.py prune --days 10`) was left unwrapped and never ran.
  $t = $t -replace '"command":\s*"''?([^"'']*[/\\]\.claude[/\\]hooks[/\\][^"'']*\.py)''?([^"]*)"', ('"command": "' + $PY + ' \"$1\"$2"')
  [System.IO.File]::WriteAllText($settings, $t)

  # codex hooks.json: $HOME literal -> profile path, python3 -> detected launcher.
  if (Test-Path $codexHooks) {
    $c = [System.IO.File]::ReadAllText($codexHooks)
    $c = $c -replace '\$HOME', $homeFwd
    $c = $c -replace '\bpython3\b', $PY   # \b so a path containing "python3" is not mangled
    [System.IO.File]::WriteAllText($codexHooks, $c)
  }
  Write-Host "hooks: registered via '$PY'"
} else {
  # No Python: never register a hook that cannot run. Strip hooks + statusLine cleanly.
  $j = Get-Content $settings -Raw | ConvertFrom-Json
  $j.PSObject.Properties.Remove('hooks') | Out-Null
  $j.PSObject.Properties.Remove('statusLine') | Out-Null
  [System.IO.File]::WriteAllText($settings, ($j | ConvertTo-Json -Depth 30))
  if (Test-Path $codexHooks) { [System.IO.File]::WriteAllText($codexHooks, '{ "hooks": {} }') }
  Write-Host 'hooks: NONE registered (Python not found). Install Python 3 and re-run to activate them.'
  if ($prevSettings) {
    # merging needs Python; without it the shipped file would replace settings we could not read,
    # so the user's own file is put back and the harness ships hook-free instead
    Write-Host '  your previous settings.json was restored intact (merge needs Python)'
  }
}

# Model registry vs. what the backends actually serve - pins go stale silently, so surface it here.
$mrc = Join-Path $profileDir '.claude\hooks\model-registry-check.py'
if ($PY -and (Test-Path $mrc)) {
  Write-Host ''
  Write-Host 'Model registry (roles whose CLI is absent are skipped):'
  $pyParts = Split-Launcher $PY
  & $pyParts[0] @((Launcher-Args $pyParts) + $mrc) 2>$null | ForEach-Object { Write-Host "  $_" }
}

Write-Host ''
Write-Host 'Skipped (Windows):'
Write-Host "  - $skipMac"
if (-not $PY) { Write-Host '  - ALL hooks (no Python) - settings.json ships hook-free until Python is installed' }
Write-Host ''
Write-Host 'Done. Start Claude Code / Codex; public plugins load from the vendored local marketplace (~/.claude/plugins-vendored) - no network needed.'
Write-Host 'Nothing was pushed and no git remote was configured.'
