' Запуск.vbs
' -----------
' Запускает SysUtil без открытия окна консоли (ни на старте,
' ни при последующем перезапросе прав администратора).
' Достаточно дважды кликнуть по этому файлу вместо набора команд
' в командной строке.

Set objShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.Run "pythonw.exe " & Chr(34) & strPath & "\main.py" & Chr(34), 0, False
