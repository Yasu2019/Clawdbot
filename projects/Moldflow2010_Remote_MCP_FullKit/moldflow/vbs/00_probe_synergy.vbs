Option Explicit
On Error Resume Next
Dim progIds, id, app
progIds = Array("synergy.Synergy", "Synergy.Synergy", "moldflow.Synergy")
For Each id In progIds
  Err.Clear
  Set app = CreateObject(id)
  If Err.Number = 0 Then
    WScript.Echo "SUCCESS ProgID=" & id
    WScript.Echo "Object=" & TypeName(app)
    WScript.Quit 0
  Else
    WScript.Echo "FAILED ProgID=" & id & " Error=" & Err.Description
  End If
Next
WScript.Quit 2
