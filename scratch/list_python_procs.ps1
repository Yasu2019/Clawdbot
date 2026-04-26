Get-WmiObject Win32_Process -Filter "Name like 'python%'" | Select-Object ProcessId, Name, CommandLine | Format-List
