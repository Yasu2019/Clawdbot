'%RunPerInstance
Option Explicit
' 03_export_node_coordinates.vbs -- Play Macro only (MF2010)
' Export every mesh node as NodeID,X_mm,Y_mm,Z_mm for OpenFOAM mapping.
' Read-only: does not modify or save the active Study.
' DO NOT run via schtasks /IT or remote cscript.

Dim Synergy, SynergyGetter, StudyDoc, FS, sh
Dim outDir, logPath, csvPath, partPath, fLog, fCsv
Dim wmi, procs, p, nSyn, sa, msg
Dim Ent, Coord, nodeID, nOk, nMiss, nDup, flushN
Dim seen, x, y, z, minX, minY, minZ, maxX, maxY, maxZ, firstOK

Const EXPECT_STUDY = "mf_strip_cool_v12_20260720_1"

On Error Resume Next
Set FS = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
outDir = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\MF_CoolFlowWarp_AllResults_Export_20260802"
If Not FS.FolderExists(outDir) Then FS.CreateFolder outDir

logPath = outDir & "\export_node_coordinates_log.txt"
csvPath = outDir & "\" & EXPECT_STUDY & "_node_coordinates.csv"
partPath = csvPath & ".part"
Set fLog = FS.CreateTextFile(logPath, True)

Sub L(ByVal s)
  On Error Resume Next
  fLog.WriteLine s
  fLog.Close
  Set fLog = FS.OpenTextFile(logPath, 8, True)
End Sub

Function CsvNumber(ByVal v)
  ' CStr has no thousands separators. Normalize a comma decimal locale to dot.
  CsvNumber = Replace(CStr(CDbl(v)), ",", ".")
End Function

Sub AbortExport(ByVal code, ByVal reason)
  On Error Resume Next
  L "ABORT code=" & code & " reason=" & reason
  If Not fCsv Is Nothing Then fCsv.Close
  If FS.FileExists(partPath) Then FS.DeleteFile partPath, True
  fLog.Close
  MsgBox reason, 16, "MF Node Coordinate Export"
  WScript.Quit code
End Sub

L "NODE_COORDINATES START " & Now
L "RULE=Play_Macro; READ_ONLY=true; UNIT=mm; ATOMIC_PART=true"

' Require one interactive Synergy instance, matching 00-02 safety behavior.
nSyn = 0
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT ProcessId,CommandLine FROM Win32_Process WHERE Name='synergy.exe'")
For Each p In procs
  nSyn = nSyn + 1
  L "SYN pid=" & p.ProcessId & " cmd=" & p.CommandLine
Next
L "SYNERGY_COUNT=" & nSyn
If nSyn <> 1 Then AbortExport 2, "Coordinate export aborted: synergy.exe count=" & nSyn & " (need exactly 1)."

' Bind in the same order proven by the 00-02 macro set.
Err.Clear
Set SynergyGetter = Nothing
Set Synergy = Nothing
sa = sh.ExpandEnvironmentStrings("%SAInstance%")
L "SAInstance=[" & sa & "]"
If sa <> "%SAInstance%" And Len(Trim(sa)) > 0 Then
  Err.Clear
  Set SynergyGetter = GetObject(sa)
  L "GetObject(SAInstance) err=" & Err.Number & " nothing=" & (SynergyGetter Is Nothing)
  If (Not IsEmpty(SynergyGetter)) And (Not SynergyGetter Is Nothing) Then
    Err.Clear
    Set Synergy = SynergyGetter.GetSASynergy
    L "BIND=GetSASynergy err=" & Err.Number & " nothing=" & (Synergy Is Nothing)
  End If
End If
If Synergy Is Nothing Then
  Err.Clear
  Set Synergy = GetObject(, "synergy.Synergy")
  L "BIND=GetObject_ROT err=" & Err.Number & " nothing=" & (Synergy Is Nothing)
End If
If Synergy Is Nothing Then
  Err.Clear
  Set Synergy = CreateObject("synergy.Synergy")
  L "BIND=CreateObject_host_fallback err=" & Err.Number & " nothing=" & (Synergy Is Nothing)
End If
If Synergy Is Nothing Then AbortExport 3, "Coordinate export aborted: cannot bind Synergy."

Synergy.SetUnits "Metric"
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then AbortExport 4, "Coordinate export aborted: StudyDoc is Nothing."
L "ACTIVE=" & StudyDoc.StudyName
L "SEQ=" & StudyDoc.AnalysisSequence
If InStr(1, LCase(CStr(StudyDoc.StudyName)), LCase(EXPECT_STUDY), 1) = 0 Then
  AbortExport 5, "Coordinate export aborted: wrong study (need " & EXPECT_STUDY & ")."
End If

If FS.FileExists(partPath) Then FS.DeleteFile partPath, True
Set fCsv = FS.CreateTextFile(partPath, True)
fCsv.WriteLine "NodeID,X_mm,Y_mm,Z_mm"
Set seen = CreateObject("Scripting.Dictionary")
nOk = 0
nMiss = 0
nDup = 0
flushN = 0
firstOK = False

Err.Clear
Set Ent = StudyDoc.GetFirstNode()
If Err.Number <> 0 Or Ent Is Nothing Then
  AbortExport 6, "Coordinate export aborted: GetFirstNode returned no mesh node."
End If

Do While Not Ent Is Nothing
  Err.Clear
  nodeID = StudyDoc.GetEntityID(Ent)
  Set Coord = Nothing
  Set Coord = StudyDoc.GetNodeCoord(Ent)
  If Err.Number <> 0 Or Coord Is Nothing Then
    nMiss = nMiss + 1
    L "MISS node=" & nodeID & " err=" & Err.Number
  ElseIf seen.Exists(CStr(nodeID)) Then
    nDup = nDup + 1
    L "DUP node=" & nodeID
  Else
    x = CDbl(Coord.X)
    y = CDbl(Coord.Y)
    z = CDbl(Coord.Z)
    seen.Add CStr(nodeID), True
    fCsv.WriteLine CStr(nodeID) & "," & CsvNumber(x) & "," & CsvNumber(y) & "," & CsvNumber(z)
    nOk = nOk + 1
    If Not firstOK Then
      minX = x: maxX = x
      minY = y: maxY = y
      minZ = z: maxZ = z
      firstOK = True
    Else
      If x < minX Then minX = x
      If x > maxX Then maxX = x
      If y < minY Then minY = y
      If y > maxY Then maxY = y
      If z < minZ Then minZ = z
      If z > maxZ Then maxZ = z
    End If
    flushN = flushN + 1
    If flushN >= 500 Then
      fCsv.Close
      Set fCsv = FS.OpenTextFile(partPath, 8, True)
      flushN = 0
      L "FLUSH n=" & nOk
    End If
  End If
  Err.Clear
  Set Ent = StudyDoc.GetNextNode(Ent)
  If Err.Number <> 0 Then AbortExport 7, "Coordinate export aborted: GetNextNode failed after n=" & nOk & "."
Loop
fCsv.Close
Set fCsv = Nothing

If nOk < 1 Then AbortExport 8, "Coordinate export aborted: zero valid coordinates."
If nMiss > 0 Or nDup > 0 Then
  AbortExport 9, "Coordinate export incomplete: ok=" & nOk & " missing=" & nMiss & " duplicate=" & nDup & "."
End If

' Promote only a complete file. Existing completed CSV is replaced only here.
If FS.FileExists(csvPath) Then FS.DeleteFile csvPath, True
FS.MoveFile partPath, csvPath
L "BBOX_MM min=(" & CsvNumber(minX) & "," & CsvNumber(minY) & "," & CsvNumber(minZ) & ") max=(" & CsvNumber(maxX) & "," & CsvNumber(maxY) & "," & CsvNumber(maxZ) & ")"
L "DONE ok=" & nOk & " missing=" & nMiss & " duplicate=" & nDup & " path=" & csvPath
fLog.Close

msg = "Node coordinate export completed." & vbCrLf & _
      "nodes=" & nOk & " unit=mm" & vbCrLf & _
      csvPath
MsgBox msg, 64, "MF Node Coordinate Export"
WScript.Quit 0
