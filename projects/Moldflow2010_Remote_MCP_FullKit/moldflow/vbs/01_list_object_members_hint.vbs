Option Explicit
Dim Synergy
On Error Resume Next
Set Synergy = CreateObject("synergy.Synergy")
If Err.Number <> 0 Then
  WScript.Echo "CreateObject failed: " & Err.Description
  WScript.Quit 2
End If
WScript.Echo "Synergy OLE connection succeeded."
WScript.Echo "TypeName=" & TypeName(Synergy)
WScript.Echo "Inspect installed API examples under data\commands."
