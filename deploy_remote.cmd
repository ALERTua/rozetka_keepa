
@echo off
cd %~dp0
if not defined DOCKER_HOST (
    set DOCKER_HOST=tcp://docker:2375
)
set DOCKER_REMOTE=1
call deploy.cmd %*
where nircmd >nul 2>nul && nircmd beep 500 500
