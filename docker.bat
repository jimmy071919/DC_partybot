@echo off
setlocal

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="build" goto build
if "%1"=="up" goto up
if "%1"=="down" goto down
if "%1"=="logs" goto logs
if "%1"=="restart" goto restart
if "%1"=="clean" goto clean

:help
echo Discord Bot Docker 管理指令：
echo   docker.bat build    - 建置 Docker 映像
echo   docker.bat up       - 啟動服務
echo   docker.bat down     - 停止服務
echo   docker.bat logs     - 查看日誌
echo   docker.bat restart  - 重新啟動服務
echo   docker.bat clean    - 清理所有 Docker 資源
goto end

:build
echo 建置 Docker 映像...
docker-compose build
goto end

:up
echo 啟動服務...
docker-compose up -d
goto end

:down
echo 停止服務...
docker-compose down
goto end

:logs
echo 查看日誌...
docker-compose logs -f discord-bot
goto end

:restart
echo 重新啟動服務...
docker-compose restart
goto end

:clean
echo 清理 Docker 資源...
docker-compose down --rmi all --volumes --remove-orphans
goto end

:end