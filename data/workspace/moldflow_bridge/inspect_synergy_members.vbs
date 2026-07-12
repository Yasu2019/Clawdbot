' ASCII-only read-only type information inspection for Synergy COM.
Option Explicit
SetLocale("en-us")

Dim synergy, tli, info, member, nameUpper, includeMember, paramCount
On Error Resume Next
Err.Clear
Set synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Or (synergy Is Nothing) Then
    WScript.Echo "[NG] Synergy CreateObject: Err " & Hex(Err.Number) & ": " & Err.Description
    WScript.Quit 1
End If

Err.Clear
Set tli = CreateObject("TLI.TLIApplication")
If Err.Number <> 0 Or (tli Is Nothing) Then
    WScript.Echo "[NG] TLI.TLIApplication unavailable: Err " & Hex(Err.Number) & ": " & Err.Description
    WScript.Quit 2
End If

Err.Clear
Set info = tli.InterfaceInfoFromObject(synergy)
If Err.Number <> 0 Or (info Is Nothing) Then
    WScript.Echo "[NG] InterfaceInfoFromObject: Err " & Hex(Err.Number) & ": " & Err.Description
    WScript.Quit 3
End If
On Error GoTo 0

WScript.Echo "[OK] interface=" & info.Name
For Each member In info.Members
    nameUpper = UCase(member.Name)
    includeMember = _
        InStr(nameUpper, "IMPORT") > 0 Or _
        InStr(nameUpper, "ADD") > 0 Or _
        InStr(nameUpper, "NEW") > 0 Or _
        InStr(nameUpper, "OPEN") > 0 Or _
        InStr(nameUpper, "STUDY") > 0 Or _
        InStr(nameUpper, "PROJECT") > 0 Or _
        InStr(nameUpper, "MESH") > 0 Or _
        InStr(nameUpper, "MATERIAL") > 0 Or _
        InStr(nameUpper, "ANALYSIS") > 0 Or _
        InStr(nameUpper, "RUN") > 0
    If includeMember Then
        paramCount = -1
        On Error Resume Next
        Err.Clear
        paramCount = member.Parameters.Count
        Err.Clear
        On Error GoTo 0
        WScript.Echo member.Name & "|invoke=" & member.InvokeKind & "|params=" & paramCount
    End If
Next
