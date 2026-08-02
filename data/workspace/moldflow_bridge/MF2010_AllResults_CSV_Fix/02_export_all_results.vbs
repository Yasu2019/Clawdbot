'%RunPerInstance
Option Explicit
' 02_export_all_results.vbs -- Play Macro only (MF2010)
' Exports all export=1 rows from export_manifest.csv (written by 00_inventory).
' 1 Get*Data call per (field, indp_frame). fill_and_last => max 2 frames.
' Skips already_have (8 eval + warp). DO NOT schtasks.
' Bind: inline S023.

Dim Synergy, SynergyGetter, StudyDoc, PlotManager, Plot, FS, sh
Dim outDir, logPath, fLog, fCsv, fManOut, sa, msg, nSyn
Dim wmi, procs, p
Dim manPath, fMan, raw, parts
Dim safe, dsid, kind, indpPol, exportFlag
Dim nOk, nFail, nSkip, t0
Dim Indp, NodeIDs, Values, Vx, Vy, Vz
Dim P11, P22, P33, P12, P13, P23
Dim dict, keys, kk, indpVal, tag, nKeys, fillLike

Const EXPECT_STUDY = "mf_fc_warp_v2_20260720"
Const FILL_TARGET = 1.05

On Error Resume Next
Set FS = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
outDir = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\MF_AllResults_Export"
If Not FS.FolderExists(outDir) Then FS.CreateFolder outDir
logPath = outDir & "\export_all_results_log.txt"
manPath = outDir & "\export_manifest.csv"
Set fLog = FS.CreateTextFile(logPath, True)

Sub L(ByVal s)
  On Error Resume Next
  fLog.WriteLine s
  fLog.Close
  Set fLog = FS.OpenTextFile(logPath, 8, True)
End Sub

Function CollectIndps(ByVal rid, ByVal mode)
  ' Returns Scripting.Dictionary of indp values to export (1 or 2 keys)
  Dim iv, nn, jj, best, bd, d, vv, dict, lastV, fillV
  Set dict = CreateObject("Scripting.Dictionary")
  Set iv = Synergy.CreateDoubleArray()
  Err.Clear
  PlotManager.GetIndpValues CLng(rid), iv
  If Err.Number <> 0 Or iv Is Nothing Or iv.Size() < 1 Then
    L "INDP rid=" & rid & " n=0 FALLBACK_INDP=0"
    dict.Add "0", 0
    Set CollectIndps = dict
    Exit Function
  End If
  nn = iv.Size()
  lastV = iv.Val(nn - 1)
  L "INDP rid=" & rid & " n=" & nn & " first=" & iv.Val(0) & " last=" & lastV
  If mode = "last" Or nn = 1 Then
    dict.Add CStr(lastV), lastV
  ElseIf mode = "fill" Then
    best = iv.Val(0)
    bd = Abs(best - FILL_TARGET)
    For jj = 0 To nn - 1
      vv = iv.Val(jj)
      d = Abs(vv - FILL_TARGET)
      If d < bd Then bd = d: best = vv
    Next
    L "PICK_FILL_INDP=" & best & " target=" & FILL_TARGET
    dict.Add CStr(best), best
  ElseIf mode = "fill_and_last" Then
    best = iv.Val(0)
    bd = Abs(best - FILL_TARGET)
    For jj = 0 To nn - 1
      vv = iv.Val(jj)
      d = Abs(vv - FILL_TARGET)
      If d < bd Then bd = d: best = vv
    Next
    fillV = best
    L "PICK_FILL_INDP=" & fillV & " target=" & FILL_TARGET
    dict.Add CStr(fillV), fillV
    If Abs(fillV - lastV) > 1E-12 Then
      dict.Add CStr(lastV), lastV
    End If
  Else
    dict.Add CStr(lastV), lastV
  End If
  Set CollectIndps = dict
End Function

Sub ExportFrame(ByVal safe, ByVal rid, ByVal kind, ByVal indpVal, ByVal tag)
  Dim pathFinal, pathPart, useVec, useTen, nNodes, k, flushN, absMax
  Dim mx, my, mz, mag, v, line
  L "=== EXPORT " & safe & " rid=" & rid & " kind=" & kind & " indp=" & indpVal & " tag=" & tag & " ==="
  Err.Clear
  Set Plot = Nothing
  Set Plot = PlotManager.CreatePlotByDsID2(CLng(rid), False)

  Set Indp = Synergy.CreateDoubleArray()
  Indp.AddDouble CDbl(indpVal)
  Set NodeIDs = Synergy.CreateIntegerArray()
  Set Values = Synergy.CreateDoubleArray()
  Set Vx = Synergy.CreateDoubleArray()
  Set Vy = Synergy.CreateDoubleArray()
  Set Vz = Synergy.CreateDoubleArray()
  Set P11 = Synergy.CreateDoubleArray()
  Set P22 = Synergy.CreateDoubleArray()
  Set P33 = Synergy.CreateDoubleArray()
  Set P12 = Synergy.CreateDoubleArray()
  Set P13 = Synergy.CreateDoubleArray()
  Set P23 = Synergy.CreateDoubleArray()
  useVec = False
  useTen = False

  If kind = "tensor" Then
    L "BEFORE GetTensorData " & safe
    Err.Clear
    PlotManager.GetTensorData CLng(rid), Indp, NodeIDs, P11, P22, P33, P12, P13, P23
    L "AFTER GetTensorData err=" & Err.Number & " n=" & NodeIDs.Size()
    useTen = True
  ElseIf kind = "vector" Then
    L "BEFORE GetVectorData " & safe
    Err.Clear
    PlotManager.GetVectorData CLng(rid), Indp, NodeIDs, Vx, Vy, Vz
    L "AFTER GetVectorData err=" & Err.Number & " n=" & NodeIDs.Size()
    useVec = True
  Else
    L "BEFORE GetScalarData " & safe
    Err.Clear
    PlotManager.GetScalarData CLng(rid), Indp, NodeIDs, Values
    L "AFTER GetScalarData err=" & Err.Number & " n=" & NodeIDs.Size()
    If Err.Number <> 0 Or NodeIDs Is Nothing Or NodeIDs.Size() < 1 Then
      L "SCALAR empty -> try GetVectorData"
      Err.Clear
      Set NodeIDs = Synergy.CreateIntegerArray()
      PlotManager.GetVectorData CLng(rid), Indp, NodeIDs, Vx, Vy, Vz
      L "AFTER GetVectorData err=" & Err.Number & " n=" & NodeIDs.Size()
      useVec = True
    End If
  End If

  If Err.Number <> 0 Or NodeIDs Is Nothing Or NodeIDs.Size() < 1 Then
    L "SKIP no_data " & safe & " tag=" & tag
    nFail = nFail + 1
    Exit Sub
  End If
  nNodes = NodeIDs.Size()

  pathFinal = outDir & "\" & EXPECT_STUDY & "_" & safe
  If tag <> "" Then pathFinal = pathFinal & "_" & tag
  pathFinal = pathFinal & ".csv"
  pathPart = pathFinal & ".part"
  If FS.FileExists(pathPart) Then FS.DeleteFile pathPart, True
  Set fCsv = FS.CreateTextFile(pathPart, True)
  If useTen Then
    fCsv.WriteLine "NodeID,p11,p22,p33,p12,p13,p23,indp,data_id,field"
  ElseIf useVec Then
    fCsv.WriteLine "NodeID,vx,vy,vz,mag,indp,data_id,field"
  Else
    fCsv.WriteLine "NodeID,value,indp,data_id,field"
  End If
  absMax = 0
  flushN = 0
  For k = 0 To nNodes - 1
    If useTen Then
      fCsv.WriteLine NodeIDs.Val(k) & "," & P11.Val(k) & "," & P22.Val(k) & "," & P33.Val(k) & "," & P12.Val(k) & "," & P13.Val(k) & "," & P23.Val(k) & "," & indpVal & "," & rid & "," & safe
    ElseIf useVec Then
      mx = Vx.Val(k): my = Vy.Val(k): mz = Vz.Val(k)
      mag = Sqr(mx * mx + my * my + mz * mz)
      If mag > absMax Then absMax = mag
      fCsv.WriteLine NodeIDs.Val(k) & "," & mx & "," & my & "," & mz & "," & mag & "," & indpVal & "," & rid & "," & safe
    Else
      v = Values.Val(k)
      If Abs(v) < 1E30 Then
        If Abs(v) > absMax Then absMax = Abs(v)
      End If
      fCsv.WriteLine NodeIDs.Val(k) & "," & v & "," & indpVal & "," & rid & "," & safe
    End If
    flushN = flushN + 1
    If flushN >= 500 Then
      fCsv.Close
      Set fCsv = FS.OpenTextFile(pathPart, 8, True)
      flushN = 0
      L "FLUSH " & safe & " k=" & k
    End If
  Next
  fCsv.Close
  If FS.FileExists(pathFinal) Then FS.DeleteFile pathFinal, True
  FS.MoveFile pathPart, pathFinal
  L "OK " & safe & " tag=" & tag & " n=" & nNodes & " absmax=" & absMax & " -> " & pathFinal
  nOk = nOk + 1
  Set fCsv = FS.OpenTextFile(outDir & "\manifest_all_results_export.csv", 8, True)
  fCsv.WriteLine safe & "," & rid & "," & kind & "," & indpVal & "," & tag & "," & nNodes & "," & absMax & "," & pathFinal
  fCsv.Close
End Sub

L "EXPORT_ALL START " & Now
L "RULE=Play_Macro; BIND=inline_S023; NO_6x_full_mesh_indp_scans"

If Not FS.FileExists(manPath) Then
  msg = "Export aborted: run 00_inventory first. Missing " & manPath
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Export"
  WScript.Quit 7
End If

nSyn = 0
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT ProcessId,CommandLine FROM Win32_Process WHERE Name='synergy.exe'")
For Each p In procs
  nSyn = nSyn + 1
  L "SYN pid=" & p.ProcessId & " cmd=" & p.CommandLine
Next
L "SYNERGY_COUNT=" & nSyn
If nSyn <> 1 Then
  msg = "Export aborted: synergy.exe count=" & nSyn & " (need exactly 1)."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Export"
  WScript.Quit 2
End If

Err.Clear
Set SynergyGetter = Nothing
Set Synergy = Nothing
sa = sh.ExpandEnvironmentStrings("%SAInstance%")
L "SAInstance=[" & sa & "]"
If sa <> "%SAInstance%" And Len(Trim(sa)) > 0 Then
  Err.Clear
  Set SynergyGetter = GetObject(sa)
  L "GetObject(SAInstance) nothing=" & (SynergyGetter Is Nothing) & " empty=" & IsEmpty(SynergyGetter) & " err=" & Err.Number
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
If Synergy Is Nothing Then
  msg = "Export aborted: cannot bind Synergy."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Export"
  WScript.Quit 3
End If

Synergy.SetUnits "Metric"
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then
  msg = "Export aborted: StudyDoc is Nothing."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Export"
  WScript.Quit 4
End If
L "ACTIVE=" & StudyDoc.StudyName
If InStr(1, LCase(CStr(StudyDoc.StudyName)), LCase(EXPECT_STUDY), 1) = 0 Then
  msg = "Export aborted: wrong study (need " & EXPECT_STUDY & ")"
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Export"
  WScript.Quit 5
End If

Set PlotManager = Synergy.PlotManager()
Set fManOut = FS.CreateTextFile(outDir & "\manifest_all_results_export.csv", True)
fManOut.WriteLine "safe,data_id,kind,indp,tag,n,absmax,path"
fManOut.Close

nOk = 0
nFail = 0
nSkip = 0
t0 = Timer

Set fMan = FS.OpenTextFile(manPath, 1, False)
If Not fMan.AtEndOfStream Then fMan.ReadLine
Do While Not fMan.AtEndOfStream
  raw = Trim(fMan.ReadLine)
  If raw <> "" Then
    parts = Split(raw, ",")
    If UBound(parts) >= 4 Then
      safe = parts(0)
      dsid = parts(1)
      kind = parts(2)
      indpPol = parts(3)
      exportFlag = "0"
      If UBound(parts) >= 4 Then exportFlag = parts(4)
      If exportFlag <> "1" Then
        nSkip = nSkip + 1
        L "SKIP_MANIFEST " & safe & " export=" & exportFlag
      ElseIf kind = "none" Or kind = "warp" Then
        nSkip = nSkip + 1
        L "SKIP_KIND " & safe & " kind=" & kind
      Else
        Set dict = CollectIndps(CLng(dsid), indpPol)
        keys = dict.Keys
        nKeys = dict.Count
        For Each kk In keys
          indpVal = dict(kk)
          tag = ""
          If nKeys > 1 Then
            fillLike = False
            If Abs(CDbl(indpVal) - FILL_TARGET) < 0.2 Then fillLike = True
            If fillLike Then
              tag = "fill"
            Else
              tag = "last"
            End If
          End If
          Call ExportFrame(safe, CLng(dsid), kind, indpVal, tag)
        Next
      End If
    End If
  End If
Loop
fMan.Close

L "DONE ok=" & nOk & " fail=" & nFail & " skip=" & nSkip & " sec=" & FormatNumber(Timer - t0, 1)
fLog.Close
msg = "AllResults export done" & vbCrLf & "ok=" & nOk & " fail=" & nFail & " skip=" & nSkip & vbCrLf & outDir
MsgBox msg, 64, "MF AllResults Export"
WScript.Quit 0
