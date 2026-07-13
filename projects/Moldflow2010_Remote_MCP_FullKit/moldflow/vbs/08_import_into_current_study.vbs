Option Explicit
Dim sourceFile, logPath, fso, logFile, synergy, opts, ok
If WScript.Arguments.Count <> 2 Then WScript.Quit 64
sourceFile = WScript.Arguments(0)
logPath = WScript.Arguments(1)
Set fso = CreateObject("Scripting.FileSystemObject")

Sub Mark(message)
  Set logFile = fso.OpenTextFile(logPath, 8, True)
  logFile.WriteLine Now & " " & message
  logFile.Close
End Sub

On Error Resume Next
Mark "BEFORE_CREATEOBJECT"
Set synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then Mark "CREATEOBJECT_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 2
Mark "AFTER_CREATEOBJECT"
Set opts = synergy.ImportOptions()
opts.MeshType = "Fusion"
opts.Units = "mm"
opts.UseMDL = False
Mark "BEFORE_IMPORT"
ok = synergy.ImportFile2(sourceFile, opts, False, False)
If Err.Number <> 0 Then Mark "IMPORT_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 3
Mark "AFTER_IMPORT result=" & CStr(ok)
If Not ok Then WScript.Quit 4
synergy.StudyDoc().Save
Mark "AFTER_SAVE"
synergy.Project().SaveAll
Mark "DONE"
