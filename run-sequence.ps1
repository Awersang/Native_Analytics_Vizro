<#
.SYNOPSIS
    Runs three prompts in sequence, each in its own fresh Claude Code session.

.PARAMETER Prompt1
    First prompt to run.

.PARAMETER Prompt2
    Second prompt to run (started only after the first finishes).

.PARAMETER Prompt3
    Third prompt to run (started only after the second finishes).

.PARAMETER Model
    Model to use for all three runs. E.g. "sonnet", "opus", "haiku",
    or a full model id like "claude-opus-4-8".

.PARAMETER Effort
    Thinking/reasoning budget in tokens (maps to MAX_THINKING_TOKENS).
    Higher = more reasoning effort. Omit for default behavior.

.PARAMETER PermissionMode
    Permission mode for unattended runs. Default: acceptEdits.
    Other options: dontAsk, bypassPermissions, default.

.EXAMPLE
    .\run-sequence.ps1 `
        -Prompt1 "Audit the data_campaigns.py module for bugs" `
        -Prompt2 "Fix the bugs found in the previous step" `
        -Prompt3 "Run the test suite and report results" `
        -Model "sonnet" -Effort 16000
#>

param(
    [Parameter(Mandatory = $true)] [string]$Prompt1,
    [Parameter(Mandatory = $true)] [string]$Prompt2,
    [Parameter(Mandatory = $true)] [string]$Prompt3,
    [string]$Model = "sonnet",
    [int]$Effort = 0,
    [string]$PermissionMode = "acceptEdits"
)

if ($Effort -gt 0) {
    $env:MAX_THINKING_TOKENS = $Effort
}

$prompts = @($Prompt1, $Prompt2, $Prompt3)

for ($i = 0; $i -lt $prompts.Length; $i++) {
    $n = $i + 1
    Write-Host "`n=== Running prompt $n of 3 (model: $Model) ===" -ForegroundColor Cyan
    Write-Host $prompts[$i] -ForegroundColor DarkGray

    claude -p $prompts[$i] --model $Model --permission-mode $PermissionMode

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Prompt $n failed with exit code $LASTEXITCODE. Stopping sequence." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "`nAll 3 prompts completed." -ForegroundColor Green
