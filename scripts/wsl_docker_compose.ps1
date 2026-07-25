[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

& (Join-Path $PSScriptRoot "clawstack_compose.ps1") @Args
exit $LASTEXITCODE
