<#
Start a scheduled Burn Rate run, if one is due. For the Claude Code CLI and Codex on Windows.
(Claude Desktop uses its own scheduled tasks and doesn't need this.)

Schedule this every hour. Each time it asks `usage.py gate` whether a burn slot is due.
Most hours the answer is no, and it exits without starting an agent, so it costs nothing.

  run_burn.ps1            check the gate, run if due
  run_burn.ps1 -Force     skip the gate and run now

Environment (all optional):
  BURN_RATE_HOME   burn home (default ~\.burn-rate)
  BURN_CLAUDE_BIN  path to claude (default: found on PATH)
  BURN_CODEX_BIN   path to codex (default: found on PATH)

Output goes to <burn home>\logs\YYYY-MM-DD.log.

Register it with Task Scheduler (burn-setup shows you this and asks first):
  $a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File "<path>\run_burn.ps1"'
  $t = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1)
  Register-ScheduledTask -TaskName 'BurnRate\gate' -Action $a -Trigger $t -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun)
#>
param([switch]$Force)

$ErrorActionPreference = 'Stop'
$home_ = if ($env:BURN_RATE_HOME) { $env:BURN_RATE_HOME } else { Join-Path $HOME '.burn-rate' }
$env:BURN_RATE_HOME = $home_
$scripts = $PSScriptRoot
$prompt = 'Use the burn skill to do a scheduled Burn Rate run.'

New-Item -ItemType Directory -Force -Path (Join-Path $home_ 'logs') | Out-Null
$log = Join-Path $home_ ("logs\" + (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd') + '.log')
function Say($msg) { Add-Content -Path $log -Value ((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ') + ' ' + $msg) }

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { Say 'no python found; cannot check the gate'; exit 1 }
$config = Join-Path $home_ 'config.toml'
if (-not (Test-Path $config)) { Say "no config.toml in $home_; run burn-setup first"; exit 1 }

# No double quotes inside the code: Windows PowerShell 5.1 strips them from native arguments.
$platform = & $py.Source -c 'import sys,tomllib;print(tomllib.load(open(sys.argv[1],''rb'')).get(''platform'',''''))' $config

if (-not $Force) {
    $verdict = (& $py.Source (Join-Path $scripts 'usage.py') gate) -join ' '
    Say ('gate: ' + ($verdict -replace '\s+', ' '))
    if ($verdict -notmatch '"run": true') { exit 0 }
}

Set-Location -LiteralPath $home_
switch ($platform) {
    'codex' {
        $bin = if ($env:BURN_CODEX_BIN) { $env:BURN_CODEX_BIN } else { (Get-Command codex).Source }
        Say 'starting codex run'
        $null | & $bin --search exec --skip-git-repo-check --approve-for-me `
            -c sandbox_workspace_write.network_access=true -C $home_ $prompt *>> $log
        if ($LASTEXITCODE -ne 0) { Say "codex exited with $LASTEXITCODE" }
    }
    'claude-cli' {
        $bin = if ($env:BURN_CLAUDE_BIN) { $env:BURN_CLAUDE_BIN } else { (Get-Command claude).Source }
        Say 'starting claude run'
        $null | & $bin -p $prompt --permission-mode acceptEdits *>> $log
        if ($LASTEXITCODE -ne 0) { Say "claude exited with $LASTEXITCODE" }
    }
    'claude-desktop' { Say 'platform is claude-desktop: use Desktop scheduled tasks, not this script'; exit 1 }
    default { Say "unknown platform '$platform' in config.toml"; exit 1 }
}
Say 'run finished'
