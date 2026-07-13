Option Explicit
Dim studyPath, outputPath, fso, projectPath, studyName, outputDir
Dim synergy, project, ok
If WScript.Arguments.Count <> 2 Then
  WScript.Echo "USAGE: 05_export_study_logs.vbs study.sdy output.log"
  WScript.Quit 64
End If
studyPath = WScript.Arguments(0)
outputPath = WScript.Arguments(1)
Set fso = CreateObject("Scripting.FileSystemObject")
If Not fso.FileExists(studyPath) Then WScript.Echo "STUDY_NOT_FOUND " & studyPath : WScript.Quit 2
projectPath = fso.BuildPath(fso.GetParentFolderName(fso.GetParentFolderName(studyPath)), fso.GetBaseName(fso.GetParentFolderName(studyPath)) & ".mpi")
studyName = fso.GetBaseName(studyPath)
outputDir = fso.GetParentFolderName(outputPath)
If Not fso.FolderExists(outputDir) Then fso.CreateFolder(outputDir)
Set synergy = CreateObject("synergy.Synergy")
ok = synergy.OpenProject(projectPath)
If Not ok Then WScript.Echo "OPEN_PROJECT_FAILED " & projectPath : WScript.Quit 3
Set project = synergy.Project()
ok = project.OpenItemByName(studyName, "Study")
If Not ok Then WScript.Echo "OPEN_STUDY_FAILED " & studyName : WScript.Quit 4
synergy.StudyDoc().ExportAnalysisLog outputPath
synergy.StudyDoc().ExportMeshLog outputPath & ".mesh.log"
WScript.Echo "OK output=" & outputPath
