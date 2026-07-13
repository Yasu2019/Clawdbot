Option Explicit
Dim sourceFile, projectDir, projectName, studyName, logPath
Dim fso, logFile, synergy, project, opts, ok

If WScript.Arguments.Count <> 5 Then WScript.Quit 64
sourceFile = WScript.Arguments(0)
projectDir = WScript.Arguments(1)
projectName = WScript.Arguments(2)
studyName = WScript.Arguments(3)
logPath = WScript.Arguments(4)

Set fso = CreateObject("Scripting.FileSystemObject")
Set logFile = fso.OpenTextFile(logPath, 8, True)

Sub Mark(message)
  logFile.WriteLine Now & " " & message
  logFile.Close
  Set logFile = fso.OpenTextFile(logPath, 8, True)
End Sub

On Error Resume Next
Mark "START"
Mark "BEFORE_CREATEOBJECT"
Set synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then Mark "CREATEOBJECT_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 2
Mark "AFTER_CREATEOBJECT"

If Not fso.FolderExists(projectDir) Then fso.CreateFolder(projectDir)
If Err.Number <> 0 Then Mark "MKDIR_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 3
Mark "BEFORE_NEWPROJECT"
ok = synergy.NewProject(projectName, projectDir)
If Err.Number <> 0 Then Mark "NEWPROJECT_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 4
Mark "AFTER_NEWPROJECT result=" & CStr(ok)

Set project = synergy.Project()
Mark "AFTER_PROJECT_OBJECT"
ok = project.NewStudy(studyName)
If Err.Number <> 0 Then Mark "NEWSTUDY_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 5
Mark "AFTER_NEWSTUDY result=" & CStr(ok)

Set opts = synergy.ImportOptions()
opts.MeshType = "Fusion"
opts.Units = "mm"
opts.UseMDL = True
opts.MDLSurfaces = True
opts.MDLMesh = False
Mark "BEFORE_IMPORT"
ok = synergy.ImportFile2(sourceFile, opts, False, False)
If Err.Number <> 0 Then Mark "IMPORT_ERROR " & Err.Number & " " & Err.Description : WScript.Quit 6
Mark "AFTER_IMPORT result=" & CStr(ok)

synergy.StudyDoc().Save
Mark "AFTER_STUDY_SAVE"
project.SaveAll
Mark "DONE"
logFile.Close
