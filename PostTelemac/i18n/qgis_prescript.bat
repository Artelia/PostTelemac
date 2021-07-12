REM Change OSGeo4W_ROOT to point to your install of QGIS.

REM Define paths
SET OSGEO4W_ROOT=C:\OSGeo4W64
SET QGISNAME=qgis
SET QGIS=%OSGEO4W_ROOT%\apps\%QGISNAME%
set QGIS_PREFIX_PATH=%QGIS%

REM Call qgis launch file
CALL "%OSGEO4W_ROOT%\bin\o4w_env.bat"

REM Python Setup********************************************
set PATH=%OSGEO4W_ROOT%\bin;%QGIS%\bin;%PATH%
SET PYTHONHOME=%OSGEO4W_ROOT%\apps\Python37
set PYTHONPATH=%QGIS%\python;%PYTHONPATH%

REM If we want verbose...
REM ECHO OSGeo path is: %OSGEO4W_ROOT%
REM ECHO Getting QGIS libs from: %QGIS%
REM ECHO Python loaded from: %PYTHONHOME%
