Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

strPath = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

pyExe = "C:\Users\Gani\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
If Not FSO.FileExists(pyExe) Then
    localAppData = WshShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")
    If FSO.FileExists(localAppData & "\hermes\hermes-agent\venv\Scripts\pythonw.exe") Then
        pyExe = localAppData & "\hermes\hermes-agent\venv\Scripts\pythonw.exe"
    Else
        pyExe = "pythonw.exe"
    End If
End If

cmd = """" & pyExe & """ """ & strPath & "\run_gui.py"""
WshShell.Run cmd, 0, False
