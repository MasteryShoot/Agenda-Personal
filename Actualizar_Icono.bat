@echo off
title Agenda Personal - Actualizar Icono del Acceso Directo
chcp 65001 >nul 2>&1

echo.
echo  ============================================
echo    AGENDA PERSONAL - Actualizar Icono
echo  ============================================
echo.

set APPDIR=%APPDATA%\AgendaPersonal
set SHORTCUT=%USERPROFILE%\Desktop\Agenda Personal.lnk
set VBSFILE=%TEMP%\fix_shortcut_agenda.vbs
set ICOFILE=%APPDIR%\agenda.ico

REM Copiar el .ico al directorio de la app si existe junto al .bat
if exist "%~dp0agenda.ico" (
    copy /Y "%~dp0agenda.ico" "%APPDIR%\agenda.ico" >nul
    echo  OK: Icono copiado a %APPDIR%
) else (
    echo  AVISO: No se encontro agenda.ico junto a este .bat
    echo         Asegurate de tener agenda.ico en la misma carpeta.
    pause
    exit /b 1
)

echo  Regenerando acceso directo con icono...

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBSFILE%"
echo sLinkFile = "%SHORTCUT%" >> "%VBSFILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBSFILE%"
echo oLink.TargetPath = "pythonw.exe" >> "%VBSFILE%"
echo oLink.Arguments = chr(34) ^& "%APPDIR%\agenda.py" ^& chr(34) >> "%VBSFILE%"
echo oLink.WorkingDirectory = "%APPDIR%" >> "%VBSFILE%"
echo oLink.Description = "Agenda Personal de Recordatorios" >> "%VBSFILE%"
echo oLink.IconLocation = "%ICOFILE%, 0" >> "%VBSFILE%"
echo oLink.WindowStyle = 1 >> "%VBSFILE%"
echo oLink.Save >> "%VBSFILE%"
cscript //nologo "%VBSFILE%"
del "%VBSFILE%" >nul 2>&1

if exist "%SHORTCUT%" (
    echo  OK: Acceso directo actualizado con el nuevo icono
    echo.
    echo  Si el icono no cambia de inmediato, haz clic derecho
    echo  en el Escritorio y elige "Actualizar".
) else (
    echo  ERROR: No se pudo crear el acceso directo
)

echo.
pause
