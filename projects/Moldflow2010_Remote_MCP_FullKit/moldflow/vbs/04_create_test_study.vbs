Option Explicit
Dim sourceFile, projectDir, projectName, studyName
Dim fso, synergy, project, opts, ok
If WScript.Arguments.Count <> 4 Then
  WScript.Echo "USAGE: 04_create_test_study.vbs source.step project_dir project_name study_name"
  WScript.Quit 64
End If
sourceFile = WScript.Arguments(0)
projectDir = WScript.Arguments(1)
projectName = WScript.Arguments(2)
studyName = WScript.Arguments(3)
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(sourceFile) Then WScript.Echo "SOURCE_NOT_FOUND " & sourceFile : WScript.Quit 2
If Not fso.FolderExists(projectDir) Then fso.CreateFolder(projectDir)
Set synergy = CreateObject("synergy.Synergy")
ok = synergy.NewProject(projectName, projectDir)
If Not ok Then WScript.Echo "NEW_PROJECT_FAILED" : WScript.Quit 3
Set project = synergy.Project()
ok = project.NewStudy(studyName)
If Not ok Then WScript.Echo "NEW_STUDY_FAILED" : WScript.Quit 4
Set opts = synergy.ImportOptions()
opts.MeshType = "Fusion"
opts.Units = "mm"
If LCase(fso.GetExtensionName(sourceFile)) = "stl" Then
  opts.UseMDL = False
Else
  opts.UseMDL = True
  opts.MDLSurfaces = True
  opts.MDLMesh = False
End If
ok = synergy.ImportFile2(sourceFile, opts, False, False)
If Not ok Then WScript.Echo "IMPORT_FAILED" : WScript.Quit 5
synergy.StudyDoc().Save
project.SaveAll
WScript.Echo "OK project=" & projectName & " study=" & studyName
