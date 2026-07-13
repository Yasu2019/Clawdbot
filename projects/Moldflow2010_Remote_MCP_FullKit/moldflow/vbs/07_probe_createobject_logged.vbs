Option Explicit
Dim logPath, fso, logFile, synergy
If WScript.Arguments.Count <> 1 Then WScript.Quit 64
logPath = WScript.Arguments(0)
Set fso = CreateObject("Scripting.FileSystemObject")
Set logFile = fso.OpenTextFile(logPath, 8, True)
logFile.WriteLine Now & " BEFORE_CREATEOBJECT"
logFile.Close
On Error Resume Next
Set synergy = CreateObject("synergy.Synergy")
Set logFile = fso.OpenTextFile(logPath, 8, True)
If Err.Number <> 0 Then
  logFile.WriteLine Now & " CREATEOBJECT_ERROR " & Err.Number & " " & Err.Description
  logFile.Close
  WScript.Quit 2
End If
logFile.WriteLine Now & " AFTER_CREATEOBJECT"
logFile.Close
Set synergy = Nothing
