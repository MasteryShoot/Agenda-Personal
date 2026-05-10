@echo off
title Agenda Personal - Instalador
chcp 65001 >nul 2>&1

echo.
echo  ============================================
echo       AGENDA PERSONAL - Instalador
echo  ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [!] Python no esta instalado o no esta en el PATH.
    echo.
    echo  Instala Python desde: https://www.python.org/downloads/
    echo  IMPORTANTE: Marca 'Add Python to PATH' durante la instalacion.
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b 1
)

for /f "delims=" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  OK: %PYVER% detectado
echo.

set APPDIR=%APPDATA%\AgendaPersonal
if not exist "%APPDIR%" mkdir "%APPDIR%"

echo  Copiando archivos...
copy /Y "%~dp0agenda.py" "%APPDIR%\agenda.py" >nul
if errorlevel 1 (
    echo  [!] Error: asegurate de que agenda.py este en la misma carpeta que este .bat
    pause
    exit /b 1
)
echo  OK: agenda.py copiado a %APPDIR%

REM Copiar el icono si existe
if exist "%~dp0agenda.ico" (
    copy /Y "%~dp0agenda.ico" "%APPDIR%\agenda.ico" >nul
    echo  OK: Icono copiado a %APPDIR%
    set ICOFILE=%APPDIR%\agenda.ico
) else (
    echo  AVISO: agenda.ico no encontrado, el acceso directo usara icono por defecto
    set ICOFILE=
)
echo.

echo  Creando acceso directo en el Escritorio...
set SHORTCUT=%USERPROFILE%\Desktop\Agenda Personal.lnk
set VBSFILE=%TEMP%\create_shortcut_agenda.vbs

echo Set oWS = WScript.CreateObject("WScript.Shell") > "%VBSFILE%"
echo sLinkFile = "%SHORTCUT%" >> "%VBSFILE%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%VBSFILE%"
echo oLink.TargetPath = "pythonw.exe" >> "%VBSFILE%"
echo oLink.Arguments = chr(34) ^& "%APPDIR%\agenda.py" ^& chr(34) >> "%VBSFILE%"
echo oLink.WorkingDirectory = "%APPDIR%" >> "%VBSFILE%"
echo oLink.Description = "Agenda Personal de Recordatorios" >> "%VBSFILE%"
if not "%ICOFILE%"=="" (
    echo oLink.IconLocation = "%ICOFILE%, 0" >> "%VBSFILE%"
)
echo oLink.WindowStyle = 1 >> "%VBSFILE%"
echo oLink.Save >> "%VBSFILE%"
cscript //nologo "%VBSFILE%"
del "%VBSFILE%" >nul 2>&1

if exist "%SHORTCUT%" (
    echo  OK: Acceso directo creado en el Escritorio
) else (
    echo  AVISO: No se pudo crear el acceso directo
)
echo.

echo  Configurando inicio automatico con Windows...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AgendaPersonal" /t REG_SZ /d "pythonw.exe \"%APPDIR%\agenda.py\"" /f >nul 2>&1
if errorlevel 1 (
    echo  AVISO: No se pudo configurar inicio automatico
    echo         Puedes activarlo desde: Configuracion > Iniciar con Windows
) else (
    echo  OK: Inicio automatico con Windows configurado
)
echo.

echo  ============================================
echo   Instalacion completada exitosamente!
echo.
echo   App en: %APPDIR%
echo   Acceso directo en tu Escritorio
echo   Se iniciara con Windows automaticamente
echo  ============================================
echo.
echo  Iniciando Agenda Personal...
echo.

start "" pythonw.exe "%APPDIR%\agenda.py"

timeout /t 3 >nul
echo  Listo. Puedes cerrar esta ventana.
pause
