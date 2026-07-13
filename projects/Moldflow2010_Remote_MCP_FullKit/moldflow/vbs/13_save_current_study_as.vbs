Option Explicit

Dim args, newName, logPath, fso, logFile, syn, study, result
Set args = WScript.Arguments
If args.Count < 2 Then WScript.Quit 2

newName = args(0)
logPath = args(1)
Set fso = CreateObject("Scripting.FileSystemObject")
Set logFile = fso.OpenTextFile(logPath, 2, True)

On Error Resume Next
Set syn = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then
  logFile.WriteLine "ERROR CreateObject number=" & Err.Number & " description=" & Err.Description
  logFile.Close
  WScript.Quit 3
End If

Set study = syn.StudyDoc()
If Err.Number <> 0 Or study Is Nothing Then
  logFile.WriteLine "ERROR no current study"
  logFile.Close
  WScript.Quit 4
End If

Err.Clear
result = study.SaveAs(newName)
If Err.Number <> 0 Then
  logFile.WriteLine "ERROR SaveAs number=" & Err.Number & " description=" & Err.Description
  logFile.Close
  WScript.Quit 5
End If
On Error GoTo 0

logFile.WriteLine "SAVE_AS name=" & newName & " result=" & CStr(result)
logFile.WriteLine "DONE"
logFile.Close
If Not result Then WScript.Quit 6
WScript.Quit 0
