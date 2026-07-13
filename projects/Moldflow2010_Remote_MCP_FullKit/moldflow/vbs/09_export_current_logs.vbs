Option Explicit
Dim outputPath, fso, synergy
If WScript.Arguments.Count <> 1 Then WScript.Quit 64
outputPath = WScript.Arguments(0)
Set fso = CreateObject("Scripting.FileSystemObject")
On Error Resume Next
Set synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then WScript.Echo "CREATEOBJECT_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 2
synergy.StudyDoc().ExportAnalysisLog outputPath
If Err.Number <> 0 Then WScript.Echo "ANALYSIS_LOG_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 3
synergy.StudyDoc().ExportMeshLog outputPath & ".mesh.log"
If Err.Number <> 0 Then WScript.Echo "MESH_LOG_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 4
WScript.Echo "OK output=" & outputPath
