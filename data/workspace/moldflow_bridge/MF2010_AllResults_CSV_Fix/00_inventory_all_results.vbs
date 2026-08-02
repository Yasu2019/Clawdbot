'%RunPerInstance
Option Explicit
' 00_inventory_all_results.vbs -- Play Macro only (MF2010)
' Enumerate available result datasets for mf_fc_warp_v2_20260720.
' Writes inventory_all_results.csv + export_manifest.csv (02 reads the latter).
' DO NOT run via schtasks /IT or remote cscript.
' Bind: SAInstance -> GetObject -> CreateObject (inline S023; NOT Function return).

Dim Synergy, SynergyGetter, StudyDoc, PlotManager, Plot, Viewer, FS, sh
Dim outDir, packDir, logPath, fLog, fInv, fMan, fPlot, sa, msg, nSyn
Dim wmi, procs, p, nameOk, name, rid, dtype, iv, nIndp, firstI, lastI
Dim line, parts, safe, dsid, kindHint, indpPol, prio, already, notes
Dim kindFound, avail, exportFlag, skipReason, smokeN, indpProbe
Dim Indp, NodeIDs, Values, Vx, Vy, Vz
Dim P11, P22, P33, P12, P13, P23
Dim nEnum, nSeed, nAvail, nExport, seedPath, catPath

Const EXPECT_STUDY = "mf_fc_warp_v2_20260720"
Const FILL_TARGET = 1.05

On Error Resume Next
Set FS = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
outDir = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\MF_AllResults_Export"
If Not FS.FolderExists(outDir) Then FS.CreateFolder outDir
packDir = sh.ExpandEnvironmentStrings("%USERPROFILE%") & "\Desktop\MF2010_AllResults_CSV_Fix"
seedPath = packDir & "\seed_catalog.csv"
If Not FS.FileExists(seedPath) Then
  ' Fallback: same folder as this macro if deployed flat
  seedPath = FS.GetParentFolderName(WScript.ScriptFullName) & "\seed_catalog.csv"
End If
logPath = outDir & "\inventory_all_results_log.txt"
Set fLog = FS.CreateTextFile(logPath, True)

Sub L(ByVal s)
  On Error Resume Next
  fLog.WriteLine s
  fLog.Close
  Set fLog = FS.OpenTextFile(logPath, 8, True)
End Sub

Function MakeSafe(ByVal nm)
  Dim s, ch, j, out
  s = LCase(nm)
  out = ""
  For j = 1 To Len(s)
    ch = Mid(s, j, 1)
    If (ch >= "a" And ch <= "z") Or (ch >= "0" And ch <= "9") Then
      out = out & ch
    Else
      out = out & "_"
    End If
  Next
  Do While InStr(out, "__") > 0
    out = Replace(out, "__", "_")
  Loop
  If Len(out) > 50 Then out = Left(out, 50)
  If out = "" Then out = "unnamed"
  MakeSafe = out
End Function

Function ProbeKind(ByVal rid, ByVal indpVal, ByVal hint)
  ' Returns scalar|vector|tensor|none; sets smokeN
  Dim n
  smokeN = 0
  ProbeKind = "none"
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

  If hint = "vector" Then
    Err.Clear
    PlotManager.GetVectorData CLng(rid), Indp, NodeIDs, Vx, Vy, Vz
    If Err.Number = 0 And Not NodeIDs Is Nothing Then
      n = NodeIDs.Size()
      If n > 0 Then smokeN = n: ProbeKind = "vector": Exit Function
    End If
  End If
  If hint = "tensor" Then
    Err.Clear
    PlotManager.GetTensorData CLng(rid), Indp, NodeIDs, P11, P22, P33, P12, P13, P23
    If Err.Number = 0 And Not NodeIDs Is Nothing Then
      n = NodeIDs.Size()
      If n > 0 Then smokeN = n: ProbeKind = "tensor": Exit Function
    End If
  End If

  Err.Clear
  Set NodeIDs = Synergy.CreateIntegerArray()
  PlotManager.GetScalarData CLng(rid), Indp, NodeIDs, Values
  If Err.Number = 0 And Not NodeIDs Is Nothing Then
    n = NodeIDs.Size()
    If n > 0 Then smokeN = n: ProbeKind = "scalar": Exit Function
  End If

  Err.Clear
  Set NodeIDs = Synergy.CreateIntegerArray()
  PlotManager.GetVectorData CLng(rid), Indp, NodeIDs, Vx, Vy, Vz
  If Err.Number = 0 And Not NodeIDs Is Nothing Then
    n = NodeIDs.Size()
    If n > 0 Then smokeN = n: ProbeKind = "vector": Exit Function
  End If

  Err.Clear
  Set NodeIDs = Synergy.CreateIntegerArray()
  PlotManager.GetTensorData CLng(rid), Indp, NodeIDs, P11, P22, P33, P12, P13, P23
  If Err.Number = 0 And Not NodeIDs Is Nothing Then
    n = NodeIDs.Size()
    If n > 0 Then smokeN = n: ProbeKind = "tensor": Exit Function
  End If
End Function

Function PickIndpProbe(ByVal rid, ByVal mode)
  Dim iv2, nn, jj, best, bd, d, vv
  Set iv2 = Synergy.CreateDoubleArray()
  Err.Clear
  PlotManager.GetIndpValues CLng(rid), iv2
  If Err.Number <> 0 Or iv2 Is Nothing Or iv2.Size() < 1 Then
    PickIndpProbe = 0
    Exit Function
  End If
  nn = iv2.Size()
  If mode = "fill" Or mode = "fill_and_last" Then
    best = iv2.Val(0)
    bd = Abs(best - FILL_TARGET)
    For jj = 0 To nn - 1
      vv = iv2.Val(jj)
      d = Abs(vv - FILL_TARGET)
      If d < bd Then bd = d: best = vv
    Next
    PickIndpProbe = best
  Else
    PickIndpProbe = iv2.Val(nn - 1)
  End If
End Function

L "INVENTORY START " & Now
L "RULE=Play_Macro; BIND=inline_S023; CreateObject_OK_as_MF2010_host_fallback"
L "SEED=" & seedPath

nSyn = 0
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT ProcessId,CommandLine FROM Win32_Process WHERE Name='synergy.exe'")
For Each p In procs
  nSyn = nSyn + 1
  L "SYN pid=" & p.ProcessId & " cmd=" & p.CommandLine
Next
L "SYNERGY_COUNT=" & nSyn
If nSyn <> 1 Then
  msg = "Inventory aborted: synergy.exe count=" & nSyn & " (need exactly 1)."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Inventory"
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
  msg = "Inventory aborted: cannot bind Synergy."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Inventory"
  WScript.Quit 3
End If

Synergy.SetUnits "Metric"
Set StudyDoc = Synergy.StudyDoc()
If StudyDoc Is Nothing Then
  msg = "Inventory aborted: StudyDoc is Nothing."
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Inventory"
  WScript.Quit 4
End If
L "ACTIVE=" & StudyDoc.StudyName
L "SEQ=" & StudyDoc.AnalysisSequence
If InStr(1, LCase(CStr(StudyDoc.StudyName)), LCase(EXPECT_STUDY), 1) = 0 Then
  msg = "Inventory aborted: wrong study (need " & EXPECT_STUDY & ")"
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Inventory"
  WScript.Quit 5
End If

Set PlotManager = Synergy.PlotManager()
Set Viewer = Synergy.Viewer()

' --- Enumerate currently registered plots ---
Set fPlot = FS.CreateTextFile(outDir & "\inventory_plots.csv", True)
fPlot.WriteLine "plot_name,data_id,data_type,max,min,frames,indp_n,indp_first,indp_last"
nEnum = 0
name = PlotManager.GetFirstPlotName()
Do While name <> ""
  Set Plot = Nothing
  Err.Clear
  Set Plot = PlotManager.FindPlotByName2(CStr(name), CStr(name))
  If Plot Is Nothing Then Set Plot = PlotManager.FindPlotByName(CStr(name))
  rid = "": dtype = "": nIndp = 0: firstI = "": lastI = ""
  Dim mx, mn, fr
  mx = "": mn = "": fr = ""
  If Not Plot Is Nothing Then
    Err.Clear: rid = Plot.GetDataID
    Err.Clear: dtype = Plot.GetDataType & ""
    Err.Clear: mx = Plot.GetMaxValue
    Err.Clear: mn = Plot.GetMinValue
    Err.Clear: fr = Plot.GetNumberOfFrames
    Set iv = Synergy.CreateDoubleArray()
    Err.Clear
    PlotManager.GetIndpValues CLng(rid), iv
    If Err.Number = 0 And Not iv Is Nothing And iv.Size() > 0 Then
      nIndp = iv.Size()
      firstI = iv.Val(0)
      lastI = iv.Val(nIndp - 1)
    End If
  End If
  fPlot.WriteLine Replace(name, ",", ";") & "," & rid & "," & dtype & "," & mx & "," & mn & "," & fr & "," & nIndp & "," & firstI & "," & lastI
  L "ENUM name=[" & name & "] rid=" & rid & " type=" & dtype & " indp_n=" & nIndp
  nEnum = nEnum + 1
  name = PlotManager.GetNextPlotName(name)
Loop
fPlot.Close
L "ENUM_COUNT=" & nEnum

If Not FS.FileExists(seedPath) Then
  msg = "Inventory aborted: seed_catalog.csv missing at " & seedPath
  L msg
  fLog.Close
  MsgBox msg, 16, "MF AllResults Inventory"
  WScript.Quit 6
End If

Set fInv = FS.CreateTextFile(outDir & "\inventory_all_results.csv", True)
fInv.WriteLine "safe,dsid,kind_hint,kind_found,indp_policy,indp_n,indp_first,indp_last,available,smoke_n,priority,already_have,skip_reason,notes"
Set fMan = FS.CreateTextFile(outDir & "\export_manifest.csv", True)
fMan.WriteLine "safe,dsid,kind,indp_policy,export,already_have,skip_reason,smoke_n,indp_n"

nSeed = 0
nAvail = 0
nExport = 0

Dim fSeed, raw, doRow
Set fSeed = FS.OpenTextFile(seedPath, 1, False)
If Not fSeed.AtEndOfStream Then fSeed.ReadLine ' header
Do While Not fSeed.AtEndOfStream
  raw = Trim(fSeed.ReadLine)
  doRow = False
  If raw <> "" Then
    parts = Split(raw, ",")
    If UBound(parts) >= 6 Then doRow = True
  End If
  If doRow Then
    safe = parts(0)
    dsid = parts(1)
    kindHint = parts(2)
    indpPol = parts(3)
    prio = parts(4)
    already = parts(5)
    notes = ""
    If UBound(parts) >= 6 Then notes = parts(6)
    nSeed = nSeed + 1

    avail = 0
    kindFound = "none"
    smokeN = 0
    nIndp = 0
    firstI = ""
    lastI = ""
    skipReason = ""
    exportFlag = 0

    Err.Clear
    Set Plot = Nothing
    Set Plot = PlotManager.CreatePlotByDsID2(CLng(dsid), False)
    L "PROBE safe=" & safe & " dsid=" & dsid & " create_err=" & Err.Number & " nothing=" & (Plot Is Nothing)

    Set iv = Synergy.CreateDoubleArray()
    Err.Clear
    PlotManager.GetIndpValues CLng(dsid), iv
    If Err.Number = 0 And Not iv Is Nothing And iv.Size() > 0 Then
      nIndp = iv.Size()
      firstI = iv.Val(0)
      lastI = iv.Val(nIndp - 1)
    End If

    indpProbe = PickIndpProbe(CLng(dsid), indpPol)
    kindFound = ProbeKind(CLng(dsid), indpProbe, kindHint)

    If kindFound <> "none" And smokeN > 0 Then
      avail = 1
      nAvail = nAvail + 1
    Else
      skipReason = "unavailable_on_study"
    End If

    If already = "1" Then
      skipReason = "already_have"
      exportFlag = 0
    ElseIf prio = "skip_warp" Then
      skipReason = "skip_warp_have_all_effects"
      exportFlag = 0
    ElseIf avail = 1 Then
      exportFlag = 1
      nExport = nExport + 1
      skipReason = ""
    End If

    ' Single-indp: collapse fill_and_last -> last
    If avail = 1 And nIndp <= 1 And indpPol = "fill_and_last" Then
      indpPol = "last"
    End If

    fInv.WriteLine safe & "," & dsid & "," & kindHint & "," & kindFound & "," & indpPol & "," & nIndp & "," & firstI & "," & lastI & "," & avail & "," & smokeN & "," & prio & "," & already & "," & skipReason & "," & Replace(notes, ",", ";")
    fMan.WriteLine safe & "," & dsid & "," & kindFound & "," & indpPol & "," & exportFlag & "," & already & "," & skipReason & "," & smokeN & "," & nIndp
    L "RESULT safe=" & safe & " avail=" & avail & " kind=" & kindFound & " smoke_n=" & smokeN & " export=" & exportFlag & " skip=" & skipReason
  End If
Loop
fSeed.Close
fInv.Close
fMan.Close

L "DONE seed=" & nSeed & " avail=" & nAvail & " exportable=" & nExport & " enum_plots=" & nEnum
fLog.Close
msg = "Inventory done (FULL catalog seed)" & vbCrLf & _
      "enum_plots=" & nEnum & vbCrLf & _
      "seed=" & nSeed & " available=" & nAvail & " exportable_new=" & nExport & vbCrLf & _
      "Next: 01_preflight then 02_export" & vbCrLf & _
      "(Full NDDT+ELDT seed may take 30-90 min)" & vbCrLf & outDir
MsgBox msg, 64, "MF AllResults Inventory"
WScript.Quit 0
