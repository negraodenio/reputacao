@echo off
cd /d "%~dp0"
python -c "import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=8080, reload=False)"
pause