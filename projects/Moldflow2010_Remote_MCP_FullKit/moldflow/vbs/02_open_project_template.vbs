Option Explicit
If WScript.Arguments.Count < 1 Then
  WScript.Echo "Usage: cscript //nologo 02_open_project_template.vbs <project-or-study-path>"
  WScript.Quit 1
End If
Dim target, Synergy
target = WScript.Arguments(0)
Set Synergy = CreateObject("synergy.Synergy")
WScript.Echo "Connected to Synergy. Requested target=" & target
WScript.Echo "Replace calls using the API examples installed on the Moldflow PC."
