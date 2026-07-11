' check_synergy_com.vbs
' Minimal Moldflow Insight 2010 Synergy COM probe for Dynabook.
' Either command may succeed:
'   64bit: cscript //nologo check_synergy_com.vbs
'   32bit: C:\Windows\SysWOW64\cscript.exe //nologo check_synergy_com.vbs
Option Explicit

Dim progIds, pid, synergy, ok
progIds = Array("synergy.Synergy", "Synergy.Synergy", "synergy.Synergy.2010")
ok = False

For Each pid In progIds
    On Error Resume Next
    Err.Clear
    Set synergy = CreateObject(pid)
    If Err.Number = 0 And Not (synergy Is Nothing) Then
        WScript.Echo "[OK] CreateObject succeeded: " & pid
        ok = True
        Exit For
    Else
        WScript.Echo "[NG] " & pid & " -> Err " & Hex(Err.Number) & " : " & Err.Description
    End If
    On Error GoTo 0
Next

If Not ok Then
    WScript.Echo ""
    WScript.Echo "All ProgIDs failed. Next checks:"
    WScript.Echo " 1. Retry with SysWOW64 cscript for 32-bit COM."
    WScript.Echo " 2. Keep the Synergy GUI open and retry."
    WScript.Echo " 3. Run: reg query HKCR\synergy.Synergy"
    WScript.Quit 1
End If

' Probe optional version properties; names vary by release.
On Error Resume Next
Err.Clear
Dim v
v = synergy.Version
If Err.Number = 0 Then WScript.Echo "Version      : " & v Else WScript.Echo "Version      : (unavailable: " & Err.Description & ")"
Err.Clear
v = synergy.BuildNumber
If Err.Number = 0 Then WScript.Echo "BuildNumber  : " & v
Err.Clear
v = synergy.EditionType
If Err.Number = 0 Then WScript.Echo "EditionType  : " & v
On Error GoTo 0

WScript.Echo ""
WScript.Echo "[RESULT] Synergy COM is available for MCP integration."
