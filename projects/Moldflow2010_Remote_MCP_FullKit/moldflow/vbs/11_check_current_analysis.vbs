Option Explicit
Dim logPath, fso, logFile, synergy, study, ok
If WScript.Arguments.Count <> 1 Then WScript.Quit 64
logPath = WScript.Arguments(0)
Set fso = CreateObject("Scripting.FileSystemObject")
Sub Mark(message)
  Set logFile = fso.OpenTextFile(logPath, 8, True)
  logFile.WriteLine Now & " " & message
  logFile.Close
End Sub
On Error Resume Next
Set synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then Mark "CREATEOBJECT_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 2
Set study = synergy.StudyDoc()
Mark "BEFORE_CHECK"
ok = study.AnalyzeNow2(True, False, False)
If Err.Number <> 0 Then Mark "CHECK_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 3
Mark "AFTER_CHECK result=" & CStr(ok)
If Not ok Then WScript.Quit 4
