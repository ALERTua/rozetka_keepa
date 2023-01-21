@echo off
set REGISTRY_IP=192.168.1.3
set REGISTRY_PORT=5001
set IMAGE_NAME=rozetka_keepa
set IMAGE_TAG=latest
set BUILD_TAG=%REGISTRY_IP%:%REGISTRY_PORT%/%IMAGE_NAME%:%IMAGE_TAG%
set BUILD_PATH=.

set DOCKER_SERVICE=com.docker.service
set DOCKER_EXE=docker
where %DOCKER_EXE% >nul || (
    set "DOCKER_EXE=%ProgramFiles%\Docker\Docker\resources\bin\docker.exe"
)

pushd %~dp0

echo Checking service %DOCKER_SERVICE% runing
sc query %DOCKER_SERVICE% | findstr /IC:"running" >nul || (
    echo Starting service %DOCKER_SERVICE%
    sudo net start %DOCKER_SERVICE% || (
        echo "Error starting docker service %DOCKER_SERVICE%
        exit /b
    )
    echo Service %DOCKER_SERVICE% started
)

echo Checking Docker Desktop is running
tasklist | findstr /IC:"Docker Desktop.exe" >nul || (
    echo Starting Docker Desktop
    start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    timeout /t 60
)
echo Done checking Docker Desktop is running

echo Building the image
"%DOCKER_EXE%" build -t %BUILD_TAG% %BUILD_PATH% || exit /b
echo Done building the image

echo Pushing the image
"%DOCKER_EXE%" push %REGISTRY_IP%:%REGISTRY_PORT%/%IMAGE_NAME% || exit /b
echo Done pushing the image

@REM net stop %DOCKER_SERVICE% || exit /b
