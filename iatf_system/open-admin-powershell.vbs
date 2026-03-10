Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute "powershell", "-NoExit -Command Set-Location '" & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "'", "", "runas", 1
