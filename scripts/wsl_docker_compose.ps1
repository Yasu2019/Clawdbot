[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
$distro = "Ubuntu"

& wsl -d $distro -- docker compose @Args
exit $LASTEXITCODE
