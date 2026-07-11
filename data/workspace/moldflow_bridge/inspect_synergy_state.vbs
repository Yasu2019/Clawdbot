' ASCII-only read-only state inspection for Moldflow Insight 2010 Synergy.
Option Explicit
SetLocale("en-us")

Dim progIds, pid, synergy, ok, versionValue
Dim studyDoc, projectObj, plotManagerObj
Dim hasStudy, hasProject, hasPlotManager, unitsOk
Dim createError, studyError, projectError, plotError, unitsError

progIds = Array("synergy.Synergy", "Synergy.Synergy", "synergy.Synergy.2010")
ok = False
pid = ""
createError = ""

Dim candidate
For Each candidate In progIds
    On Error Resume Next
    Err.Clear
    Set synergy = CreateObject(candidate)
    If Err.Number = 0 And Not (synergy Is Nothing) Then
        ok = True
        pid = candidate
        Exit For
    End If
    createError = "Err " & Hex(Err.Number) & ": " & Err.Description
    On Error GoTo 0
Next

If Not ok Then
    WScript.Echo "{""ok"":false,""error"":""" & JsonEscape(createError) & """}"
    WScript.Quit 1
End If

versionValue = ""
On Error Resume Next
Err.Clear
versionValue = CStr(synergy.Version)
If Err.Number <> 0 Then versionValue = ""
On Error GoTo 0

hasStudy = False
studyError = ""
On Error Resume Next
Err.Clear
Set studyDoc = synergy.StudyDoc
If Err.Number = 0 And Not (studyDoc Is Nothing) Then
    hasStudy = True
Else
    studyError = "Err " & Hex(Err.Number) & ": " & Err.Description
End If
On Error GoTo 0

hasProject = False
projectError = ""
On Error Resume Next
Err.Clear
Set projectObj = synergy.Project
If Err.Number = 0 And Not (projectObj Is Nothing) Then
    hasProject = True
Else
    projectError = "Err " & Hex(Err.Number) & ": " & Err.Description
End If
On Error GoTo 0

hasPlotManager = False
plotError = ""
On Error Resume Next
Err.Clear
Set plotManagerObj = synergy.PlotManager
If Err.Number = 0 And Not (plotManagerObj Is Nothing) Then
    hasPlotManager = True
Else
    plotError = "Err " & Hex(Err.Number) & ": " & Err.Description
End If
On Error GoTo 0

unitsOk = False
unitsError = ""
On Error Resume Next
Err.Clear
synergy.SetUnits "METRIC"
If Err.Number = 0 Then
    unitsOk = True
Else
    unitsError = "Err " & Hex(Err.Number) & ": " & Err.Description
End If
On Error GoTo 0

WScript.Echo "{" & _
    """ok"":true," & _
    """prog_id"":""" & JsonEscape(pid) & """," & _
    """version"":""" & JsonEscape(versionValue) & """," & _
    """has_active_study"":" & JsonBool(hasStudy) & "," & _
    """study_error"":""" & JsonEscape(studyError) & """," & _
    """has_project"":" & JsonBool(hasProject) & "," & _
    """project_error"":""" & JsonEscape(projectError) & """," & _
    """has_plot_manager"":" & JsonBool(hasPlotManager) & "," & _
    """plot_error"":""" & JsonEscape(plotError) & """," & _
    """metric_units_ok"":" & JsonBool(unitsOk) & "," & _
    """units_error"":""" & JsonEscape(unitsError) & """," & _
    """read_only"":true}"

Function JsonBool(value)
    If value Then
        JsonBool = "true"
    Else
        JsonBool = "false"
    End If
End Function

Function JsonEscape(value)
    Dim text
    text = CStr(value)
    text = Replace(text, "\", "\\")
    text = Replace(text, Chr(34), "\" & Chr(34))
    text = Replace(text, vbCr, "\r")
    text = Replace(text, vbLf, "\n")
    JsonEscape = text
End Function
