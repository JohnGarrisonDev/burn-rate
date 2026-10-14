<#
Install the Burn Rate skills for Claude Code or Codex on Windows.

  .\install.ps1 -Platform claude                 # user-wide: ~\.claude\skills
  .\install.ps1 -Platform codex                  # user-wide: ~\.codex\skills
  .\install.ps1 -Platform claude -Scope project -Project C:\path\to\folder
  .\install.ps1 -Platform codex -Link            # junction instead of copy

Use user scope. Scheduled runs start in the burn home (~\.burn-rate), so project scope
only works if that project folder is your burn home.

Running it again updates the skills in place. It only touches folders named burn*.
#>
param(
    [Parameter(Mandatory = $true)][ValidateSet('claude', 'codex')][string]$Platform,
    [ValidateSet('user', 'project')][string]$Scope = 'user',
    [string]$Project = (Get-Location).Path,
    [switch]$Link
)

$ErrorActionPreference = 'Stop'

if ($Platform -eq 'claude') {
    if ($Scope -eq 'user') { $dest = Join-Path $HOME '.claude\skills' } else { $dest = Join-Path $Project '.claude\skills' }
} else {
    $codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    if ($Scope -eq 'user') { $dest = Join-Path $codexHome 'skills' } else { $dest = Join-Path $Project '.agents\skills' }
}

$src = Join-Path $PSScriptRoot 'skills'
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Get-ChildItem -Path $src -Directory -Filter 'burn*' | ForEach-Object {
    $target = Join-Path $dest $_.Name
    if (Test-Path $target) {
        # Remove a junction without touching its source; remove a copy recursively.
        $item = Get-Item $target -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { $item.Delete() }
        else { Remove-Item -Recurse -Force -Confirm:$false $target }
    }
    if ($Link) {
        New-Item -ItemType Junction -Path $target -Target $_.FullName | Out-Null
        Write-Output "linked  $($_.Name) -> $target"
    } else {
        Copy-Item -Recurse -Path $_.FullName -Destination $target
        Write-Output "copied  $($_.Name) -> $target"
    }
}

Write-Output ''
Write-Output "Done. Open $Platform and run the burn-setup skill to get started."
