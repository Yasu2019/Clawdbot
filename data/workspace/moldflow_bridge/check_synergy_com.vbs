' check_synergy_com.vbs
' Moldflow Insight 2010 Synergy COM 接続の最小検証(Dynabook上で実行)
' 実行方法(どちらかで成功すればOK):
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
        WScript.Echo "[OK] CreateObject 成功: " & pid
        ok = True
        Exit For
    Else
        WScript.Echo "[NG] " & pid & " -> Err " & Hex(Err.Number) & " : " & Err.Description
    End If
    On Error GoTo 0
Next

If Not ok Then
    WScript.Echo ""
    WScript.Echo "全ProgIDで失敗。対処:"
    WScript.Echo " 1. SysWOW64版cscriptで再実行(32bit COMの可能性)"
    WScript.Echo " 2. Synergyを一度GUIで起動したまま再実行"
    WScript.Echo " 3. reg query HKCR\synergy.Synergy で登録確認"
    WScript.Quit 1
End If

' バージョン情報の取得(プロパティ名は版により異なるため個別トライ)
On Error Resume Next
Err.Clear
Dim v
v = synergy.Version
If Err.Number = 0 Then WScript.Echo "Version      : " & v Else WScript.Echo "Version      : (取得不可 " & Err.Description & ")"
Err.Clear
v = synergy.BuildNumber
If Err.Number = 0 Then WScript.Echo "BuildNumber  : " & v
Err.Clear
v = synergy.EditionType
If Err.Number = 0 Then WScript.Echo "EditionType  : " & v
On Error GoTo 0

WScript.Echo ""
WScript.Echo "[RESULT] Synergy COM は制御可能です。MCPサーバー化に進めます。"
