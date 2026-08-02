'%RunPerInstance
Option Explicit
' 01_preflight_all_results.vbs -- Play Macro only (MF2010)
' After 00_inventory. Requires export_manifest.csv from inventory.
' Smokes bind + study + up to 3 exportable fields from manifest.
' DO NOT run via schtasks /IT or remote cscript.

Dim Synergy, SynergyGetter, StudyDoc, PlotManager, Plot, FS, sh
Dim outDir, logPath, fLog, sa, msg, nSyn, nameOk
Dim wmi, procs, p
Dim Indp, NodeIDs, Values, Vx, Vy, Vz
Dim manPath, fMan, raw, parts, safe, dsid, kind, indpPol, exportFlag
Dim nSmokeOk, nSmokeTry, nExportable, ok

Const EXPECT_STUDY = "mf_strip_cool_v12_20260720_1"
Const FILL_TARGET = 1.05
Const NEED_SMOKE = 1

On Error Resume Next
Set FS = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
outDir = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\MF_CoolFlowWarp_AllResults_Export_20260802"
If Not FS.FolderExists(outDir) Then FS.CreateFolder outDir
logPath = outDir & "\preflight_all_results_log.txt"
manPath = outDir & "\export_manifest.csv"
Set fLog = FS.CreateTextFile(logPath, True)

Sub L(ByVal s)
  On Error Resume Next
  fLog.WriteLine s
  fLog.Close
  Set fLog = FS.OpenTextFile(logPath, 8, True)
End Sub

Function PickIndp(ByVal rid, ByVal mode)
  Dim iv, n, j, best, bd, d, v
  Set iv = Synergy.CreateDoubleArray()
  Err.Clear
  PlotManager.GetIndpValues CLng(rid), iv
  If Err.Number <> 0 Or iv Is Nothing Or iv.Size() < 1 Then
    L "INDP rid=" & rid & " n=0 FALLBACK_INDP=0"
    PickIndp = 0
    Exit Function
  End If
  n = iv.Size()
  L "INDP rid=" & rid & " n=" & n & " first=" & iv.Val(0) & " last=" & iv.Val(n - 1)
  If mode = "last" Or n = 1 Or mode = "" Then
    PickIndp = iv.Val(n - 1)
    Exit Function
  End If
  ' fill or fill_and_last -> closest to fill target for smoke
  best = iv.Val(0)
  bd = Abs(best - FILL_TARGET)
  For j = 0 To n - 1
    v = iv.Val(j)
    d = Abs(v - FILL_TARGET)
    If d < bd Then bd = d: best = v
  Next
  PickIndp = best
End Function

Function SmokeOne(ByVal label, ByVal rid, ByVal mode, ByVal kind)
  Dim indpVal, nNodes
  SmokeOne = False
  indpVal = PickIndp(rid, mode)
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
  Err.Clear
  If kind = "vector" Then
    PlotManager.GetVectorData CLng(rid), Indp, NodeIDs, Vx, Vy, Vz
  ElseIf kind = "tensor" Then
    Dim P11, P22, P33, P12, P13, P23
    Set P11 = Synergy.CreateDoubleArray()
    Set P22 = Synergy.CreateDoubleArray()
    Set P33 = Synergy.CreateDoubleArray()
    Set P12 = Synergy.CreateDoubleArray()
    Set P13 = Synergy.CreateDoubleArray()
    Set P23 = Synergy.CreateDoubleArray()
    PlotManager.GetTensorData CLng(rid), Indp, NodeIDs, P11, P22, P33, P12, P13, P23
  Else
    PlotManager.GetScalarData CLng(rid), Indp, NodeIDs, Values
    If Err.Number <> 0 Or NodeIDs Is Nothing Or NodeIDs.Size() < 1 Then
      Err.Clear
      Set NodeIDs = Synergy.CreateIntegerArray()
      PlotManager.GetVectorData CLng(rid), Indp, NodeIDs, Vx, Vy, Vz
    End If
  End If
  nNodes = 0
  If Not NodeIDs Is Nothing Then nNodes = NodeIDs.Size()
  If Err.Number = 0 And nNodes > 100 Then
    L "SMOKE_OK " & label & " rid=" & rid & " n=" & nNodes & " kind=" & kind
    SmokeOne = True
  Else
    L "SMOKE_FAIL " & label & " rid=" & rid & " n=" & nNodes & " err=" & Err.Number & " kind=" & kind
  End If
End Function

L "PREFLIGHT_ALL START " & Now
L "RULE=Play_Macro; BIND=inline_S023"

If Not FS.FileExists(manPath) Then
  msg = "Preflight FAILED: run 00_inventory first. Missing " & manPath
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Preflight"
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
  msg = "Preflight FAILED: synergy.exe count=" & nSyn & " (need exactly 1)."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Preflight"
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
  msg = "Preflight FAILED: cannot bind Synergy."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Preflight"
  WScript.Quit 3
End If

Synergy.SetUnits "Metric"
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then
  msg = "Preflight FAILED: StudyDoc is Nothing."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Preflight"
  WScript.Quit 4
End If
L "ACTIVE=" & StudyDoc.StudyName
If InStr(1, LCase(CStr(StudyDoc.StudyName)), LCase(EXPECT_STUDY), 1) = 0 Then
  msg = "Preflight FAILED: need study " & EXPECT_STUDY
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Preflight"
  WScript.Quit 5
End If

Set PlotManager = Synergy.PlotManager()
nSmokeOk = 0
nSmokeTry = 0
nExportable = 0

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
      If exportFlag = "1" Then
        nExportable = nExportable + 1
        If nSmokeTry < 3 And kind <> "none" And kind <> "warp" Then
          nSmokeTry = nSmokeTry + 1
          If SmokeOne(safe, CLng(dsid), indpPol, kind) Then nSmokeOk = nSmokeOk + 1
        End If
      End If
    End If
  End If
Loop
fMan.Close

L "SUMMARY exportable=" & nExportable & " smoke_try=" & nSmokeTry & " smoke_ok=" & nSmokeOk

If nExportable < 1 Then
  msg = "Preflight FAILED: export_manifest has 0 exportable fields. Re-run 00 or check study results."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Preflight"
  WScript.Quit 8
End If

If nSmokeOk < NEED_SMOKE Then
  msg = "Preflight FAILED: smoke_ok=" & nSmokeOk & " (need >= " & NEED_SMOKE & "). See " & logPath
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Preflight"
  WScript.Quit 9
End If

msg = "Preflight passed" & vbCrLf & _
      "Study=" & StudyDoc.StudyName & vbCrLf & _
      "exportable_new=" & nExportable & " smoke_ok=" & nSmokeOk & "/" & nSmokeTry & vbCrLf & _
      "Next: 02_export_all_results.vbs from THIS Synergy" & vbCrLf & logPath
L "PREFLIGHT PASSED"
fLog.Close
MsgBox msg, 64, "MF AllResults Preflight"
WScript.Quit 0
