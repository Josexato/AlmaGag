@echo off
REM Script para Windows para regenerar documentación SVG desde archivos .gag
REM
REM Uso:
REM     scripts\generate_docs.bat

echo.
echo ====================================================================
echo         Generador de Documentacion SVG - AlmaGag (Windows)
echo ====================================================================
echo.

setlocal enabledelayedexpansion

set "GAGS_DIR=docs\diagrams\gags"
set "SVGS_DIR=docs\diagrams\svgs"
set "SUCCESS=0"
set "ERRORS=0"
set "TOTAL=0"

REM Verificar que existe el directorio de gags
if not exist "%GAGS_DIR%" (
    echo [ERROR] No se encontro el directorio: %GAGS_DIR%
    exit /b 1
)

REM Crear directorio de SVGs si no existe
if not exist "%SVGS_DIR%" (
    echo [INFO] Creando directorio: %SVGS_DIR%
    mkdir "%SVGS_DIR%"
)

echo [INFO] Procesando archivos .gag en %GAGS_DIR%
echo.

REM Contar archivos
for %%f in ("%GAGS_DIR%\*.gag") do set /a TOTAL+=1

if %TOTAL%==0 (
    echo [ERROR] No se encontraron archivos .gag en %GAGS_DIR%
    exit /b 1
)

echo [INFO] Encontrados %TOTAL% archivo(s) .gag
echo.

set "COUNTER=0"

REM Procesar cada archivo .gag
for %%f in ("%GAGS_DIR%\*.gag") do (
    set /a COUNTER+=1
    echo [!COUNTER!/%TOTAL%] Procesando: %%~nxf

    REM Generar SVG
    python -m AlmaGag.main "%%f" >nul 2>&1

    if !ERRORLEVEL! EQU 0 (
        REM Mover SVG al directorio de docs
        if exist "%%~nf.svg" (
            move /Y "%%~nf.svg" "%SVGS_DIR%\" >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo   [OK] Generado: %%~nf.svg
                set /a SUCCESS+=1
            ) else (
                echo   [ERROR] No se pudo mover %%~nf.svg
                set /a ERRORS+=1
            )
        ) else (
            echo   [ERROR] SVG no generado: %%~nf.svg
            set /a ERRORS+=1
        )
    ) else (
        echo   [ERROR] Fallo al generar %%~nxf
        set /a ERRORS+=1
    )
    echo.
)

REM Reporte final
echo ====================================================================
echo                           Reporte Final
echo ====================================================================
echo.
echo   Total procesados:  %TOTAL%
echo   Exitosos:          %SUCCESS%
echo   Errores:           %ERRORS%
echo.

if %ERRORS% EQU 0 (
    echo [OK] Toda la documentacion se genero correctamente
    exit /b 0
) else (
    echo [ERROR] Algunos archivos fallaron (%ERRORS%/%TOTAL%)
    exit /b 1
)
