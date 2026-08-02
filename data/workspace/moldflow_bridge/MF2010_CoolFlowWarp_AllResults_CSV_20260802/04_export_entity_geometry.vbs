'%RunPerInstance
Option Explicit
' 04_export_entity_geometry.vbs -- Play Macro only (MF2010)
' Export node positions plus TRI3/1DET centroids and connectivity.
' This resolves the mixed entity IDs returned by PlotManager.Get*Data.
' Read-only for the Study. A temporary UDM is exported and deleted.

Dim Synergy, SynergyGetter, StudyDoc, Project, FS, sh
Dim outDir, logPath, csvPath, partPath, udmPath, fLog, fCsv, fUdm
Dim wmi, procs, p, nSyn, sa, msg, line, tok, kind
Dim nodes, nodeID, xyz, x, y, z, refEnt, refCoord, refID
Dim scaleToMm, axisRaw, axisCom, scaleCandidate, scaleErr
Dim expectedNodes, expectedTri3, expected1D, nNodes, nTri3, n1D
Dim nMissing, nBad, nOut, flushN, elemID, n1, n2, n3
Dim c1, c2, c3, cx, cy, cz

Const EXPECT_STUDY = "mf_strip_cool_v12_20260720_1"

On Error Resume Next
Set FS = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
outDir = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\MF_CoolFlowWarp_AllResults_Export_20260802"
If Not FS.FolderExists(outDir) Then FS.CreateFolder outDir
logPath = outDir & "\export_entity_geometry_log.txt"
csvPath = outDir & "\" & EXPECT_STUDY & "_entity_geometry.csv"
partPath = csvPath & ".part"
udmPath = outDir & "\" & EXPECT_STUDY & "_entity_geometry_source.part.udm"
Set fLog = FS.CreateTextFile(logPath, True)

Sub L(ByVal s)
  On Error Resume Next
  fLog.WriteLine s
  fLog.Close
  Set fLog = FS.OpenTextFile(logPath, 8, True)
End Sub

Function CsvNumber(ByVal v)
  CsvNumber = Replace(CStr(CDbl(v)), ",", ".")
End Function

Function Tokens(ByVal sourceLine)
  Dim s
  s = Trim(sourceLine)
  s = Replace(s, "{", " ")
  s = Replace(s, "}", " ")
  s = Replace(s, Chr(34), "")
  s = Replace(s, vbTab, " ")
  Do While InStr(s, "  ") > 0
    s = Replace(s, "  ", " ")
  Loop
  Tokens = Split(Trim(s), " ")
End Function

Sub CleanupTemporary()
  On Error Resume Next
  If Not fCsv Is Nothing Then fCsv.Close
  If Not fUdm Is Nothing Then fUdm.Close
  If FS.FileExists(partPath) Then FS.DeleteFile partPath, True
  If FS.FileExists(udmPath) Then FS.DeleteFile udmPath, True
End Sub

Sub AbortExport(ByVal code, ByVal reason)
  On Error Resume Next
  L "ABORT code=" & code & " reason=" & reason
  CleanupTemporary
  fLog.Close
  MsgBox reason, 16, "MF Entity Geometry Export"
  WScript.Quit code
End Sub

Sub WriteRow(ByVal eid, ByVal etype, ByVal px, ByVal py, ByVal pz, ByVal conn)
  fCsv.WriteLine CStr(eid) & "," & etype & "," & CsvNumber(px) & "," & CsvNumber(py) & "," & CsvNumber(pz) & "," & conn
  nOut = nOut + 1
  flushN = flushN + 1
  If flushN >= 500 Then
    fCsv.Close
    Set fCsv = FS.OpenTextFile(partPath, 8, True)
    flushN = 0
    L "FLUSH rows=" & nOut
  End If
End Sub

L "ENTITY_GEOMETRY START " & Now
L "RULE=Play_Macro; READ_ONLY_STUDY=true; TEMP_UDM=true; OUTPUT_UNIT=mm"

nSyn = 0
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT ProcessId,CommandLine FROM Win32_Process WHERE Name='synergy.exe'")
For Each p In procs
  nSyn = nSyn + 1
  L "SYN pid=" & p.ProcessId & " cmd=" & p.CommandLine
Next
L "SYNERGY_COUNT=" & nSyn
If nSyn <> 1 Then AbortExport 2, "Entity export aborted: synergy.exe count=" & nSyn & " (need exactly 1)."

Err.Clear
Set SynergyGetter = Nothing
Set Synergy = Nothing
sa = sh.ExpandEnvironmentStrings("%SAInstance%")
L "SAInstance=[" & sa & "]"
If sa <> "%SAInstance%" And Len(Trim(sa)) > 0 Then
  Set SynergyGetter = GetObject(sa)
  If (Not IsEmpty(SynergyGetter)) And (Not SynergyGetter Is Nothing) Then Set Synergy = SynergyGetter.GetSASynergy
End If
If Synergy Is Nothing Then Set Synergy = GetObject(, "synergy.Synergy")
If Synergy Is Nothing Then Set Synergy = CreateObject("synergy.Synergy")
If Synergy Is Nothing Then AbortExport 3, "Entity export aborted: cannot bind Synergy."

Synergy.SetUnits "Metric"
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then AbortExport 4, "Entity export aborted: StudyDoc is Nothing."
L "ACTIVE=" & StudyDoc.StudyName
L "SEQ=" & StudyDoc.AnalysisSequence
If InStr(1, LCase(CStr(StudyDoc.StudyName)), LCase(EXPECT_STUDY), 1) = 0 Then
  AbortExport 5, "Entity export aborted: wrong study (need " & EXPECT_STUDY & ")."
End If

' Reference one COM node in displayed Metric units to verify UDM unit scale.
Set refEnt = StudyDoc.GetFirstNode()
If refEnt Is Nothing Then AbortExport 6, "Entity export aborted: no reference node."
refID = CLng(StudyDoc.GetEntityID(refEnt))
Set refCoord = StudyDoc.GetNodeCoord(refEnt)
If refCoord Is Nothing Then AbortExport 7, "Entity export aborted: no reference coordinate."
L "REFERENCE id=" & refID & " metric_xyz=" & CsvNumber(refCoord.X) & "," & CsvNumber(refCoord.Y) & "," & CsvNumber(refCoord.Z)

Set Project = Synergy.Project()
If Project Is Nothing Then AbortExport 8, "Entity export aborted: Project is Nothing."
If FS.FileExists(udmPath) Then FS.DeleteFile udmPath, True
Err.Clear
Project.ExportModel udmPath
L "EXPORT_UDM err=" & Err.Number & " exists=" & FS.FileExists(udmPath)
If Err.Number <> 0 Or Not FS.FileExists(udmPath) Then AbortExport 9, "Entity export aborted: temporary UDM export failed."

' Pass 1: load UDM nodes and declared entity counts.
Set nodes = CreateObject("Scripting.Dictionary")
expectedNodes = -1: expectedTri3 = -1: expected1D = -1
nNodes = 0: nBad = 0
Set fUdm = FS.OpenTextFile(udmPath, 1, False)
Do While Not fUdm.AtEndOfStream
  line = Trim(fUdm.ReadLine)
  If Left(line, 5) = "NOND{" Then
    tok = Tokens(line): expectedNodes = CLng(tok(1))
  ElseIf Left(line, 5) = "NOT3{" Then
    tok = Tokens(line): expectedTri3 = CLng(tok(1))
  ElseIf Left(line, 5) = "NO1D{" Then
    tok = Tokens(line): expected1D = CLng(tok(1))
  ElseIf Left(line, 5) = "NODE{" Then
    tok = Tokens(line)
    If UBound(tok) >= 8 Then
      Err.Clear
      nodeID = CLng(tok(1))
      x = CDbl(tok(UBound(tok) - 2))
      y = CDbl(tok(UBound(tok) - 1))
      z = CDbl(tok(UBound(tok)))
      If Err.Number = 0 And Not nodes.Exists(CStr(nodeID)) Then
        nodes.Add CStr(nodeID), Array(x, y, z)
        nNodes = nNodes + 1
      Else
        nBad = nBad + 1
      End If
    Else
      nBad = nBad + 1
    End If
  End If
Loop
fUdm.Close
Set fUdm = Nothing
L "PASS1 nodes=" & nNodes & " expected=" & expectedNodes & " bad=" & nBad & " tri_expected=" & expectedTri3 & " one_d_expected=" & expected1D
If nBad > 0 Or nNodes < 1 Then AbortExport 10, "Entity export aborted: invalid UDM node records."
If expectedNodes >= 0 And nNodes <> expectedNodes Then AbortExport 11, "Entity export aborted: UDM node count mismatch."
If Not nodes.Exists(CStr(refID)) Then AbortExport 12, "Entity export aborted: reference node missing from UDM."

' Determine whether UDM coordinates are m or mm by comparison with COM Metric.
xyz = nodes(CStr(refID))
axisRaw = CDbl(xyz(0)): axisCom = CDbl(refCoord.X)
If Abs(CDbl(xyz(1))) > Abs(axisRaw) Then axisRaw = CDbl(xyz(1)): axisCom = CDbl(refCoord.Y)
If Abs(CDbl(xyz(2))) > Abs(axisRaw) Then axisRaw = CDbl(xyz(2)): axisCom = CDbl(refCoord.Z)
If Abs(axisRaw) < 1E-12 Then AbortExport 13, "Entity export aborted: reference node cannot determine UDM scale."
scaleCandidate = Abs(axisCom / axisRaw)
If Abs(scaleCandidate - 1000) < 1 Then
  scaleToMm = 1000
ElseIf Abs(scaleCandidate - 1) < 0.001 Then
  scaleToMm = 1
Else
  AbortExport 14, "Entity export aborted: unsupported UDM-to-mm scale=" & CsvNumber(scaleCandidate)
End If
scaleErr = Abs(axisCom - axisRaw * scaleToMm)
L "UDM_TO_MM_SCALE=" & scaleToMm & " reference_error_mm=" & CsvNumber(scaleErr)
If scaleErr > 0.001 Then AbortExport 15, "Entity export aborted: UDM/COM coordinate scale verification failed."

' Pass 2: write nodes and element centroids with connectivity.
If FS.FileExists(partPath) Then FS.DeleteFile partPath, True
Set fCsv = FS.CreateTextFile(partPath, True)
fCsv.WriteLine "entity_id,entity_type,centroid_x_mm,centroid_y_mm,centroid_z_mm,node_connectivity"
nOut = 0: flushN = 0: nTri3 = 0: n1D = 0: nMissing = 0: nBad = 0

For Each nodeID In nodes.Keys
  xyz = nodes(nodeID)
  WriteRow CLng(nodeID), "NODE", CDbl(xyz(0)) * scaleToMm, CDbl(xyz(1)) * scaleToMm, CDbl(xyz(2)) * scaleToMm, CStr(nodeID)
Next

Set fUdm = FS.OpenTextFile(udmPath, 1, False)
Do While Not fUdm.AtEndOfStream
  line = Trim(fUdm.ReadLine)
  kind = ""
  If Left(line, 5) = "TRI3{" Then
    kind = "TRI3"
    tok = Tokens(line)
    If UBound(tok) >= 11 Then
      elemID = CLng(tok(1))
      n1 = CStr(tok(UBound(tok) - 2)): n2 = CStr(tok(UBound(tok) - 1)): n3 = CStr(tok(UBound(tok)))
      If nodes.Exists(n1) And nodes.Exists(n2) And nodes.Exists(n3) Then
        c1 = nodes(n1): c2 = nodes(n2): c3 = nodes(n3)
        cx = (CDbl(c1(0)) + CDbl(c2(0)) + CDbl(c3(0))) / 3 * scaleToMm
        cy = (CDbl(c1(1)) + CDbl(c2(1)) + CDbl(c3(1))) / 3 * scaleToMm
        cz = (CDbl(c1(2)) + CDbl(c2(2)) + CDbl(c3(2))) / 3 * scaleToMm
        WriteRow elemID, kind, cx, cy, cz, n1 & ";" & n2 & ";" & n3
        nTri3 = nTri3 + 1
      Else
        nMissing = nMissing + 1
      End If
    Else
      nBad = nBad + 1
    End If
  ElseIf Left(line, 5) = "1DET{" Then
    kind = "1DET"
    tok = Tokens(line)
    If UBound(tok) >= 10 Then
      elemID = CLng(tok(1))
      n1 = CStr(tok(UBound(tok) - 1)): n2 = CStr(tok(UBound(tok)))
      If nodes.Exists(n1) And nodes.Exists(n2) Then
        c1 = nodes(n1): c2 = nodes(n2)
        cx = (CDbl(c1(0)) + CDbl(c2(0))) / 2 * scaleToMm
        cy = (CDbl(c1(1)) + CDbl(c2(1))) / 2 * scaleToMm
        cz = (CDbl(c1(2)) + CDbl(c2(2))) / 2 * scaleToMm
        WriteRow elemID, kind, cx, cy, cz, n1 & ";" & n2
        n1D = n1D + 1
      Else
        nMissing = nMissing + 1
      End If
    Else
      nBad = nBad + 1
    End If
  End If
Loop
fUdm.Close
Set fUdm = Nothing
fCsv.Close
Set fCsv = Nothing
L "PASS2 nodes=" & nNodes & " tri3=" & nTri3 & " one_d=" & n1D & " missing=" & nMissing & " bad=" & nBad & " rows=" & nOut

If nMissing > 0 Or nBad > 0 Then AbortExport 16, "Entity export incomplete: missing connectivity or malformed records."
If expectedTri3 >= 0 And nTri3 <> expectedTri3 Then AbortExport 17, "Entity export aborted: TRI3 count mismatch."
If expected1D >= 0 And n1D <> expected1D Then AbortExport 18, "Entity export aborted: 1DET count mismatch."

If FS.FileExists(csvPath) Then FS.DeleteFile csvPath, True
FS.MoveFile partPath, csvPath
If FS.FileExists(udmPath) Then FS.DeleteFile udmPath, True
L "DONE nodes=" & nNodes & " tri3=" & nTri3 & " one_d=" & n1D & " rows=" & nOut & " path=" & csvPath
fLog.Close

msg = "Entity geometry export completed." & vbCrLf & _
      "nodes=" & nNodes & " tri3=" & nTri3 & " 1D=" & n1D & vbCrLf & _
      csvPath
MsgBox msg, 64, "MF Entity Geometry Export"
WScript.Quit 0
