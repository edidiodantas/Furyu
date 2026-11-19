@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo ERRO: rode install-windows.bat primeiro.
  exit /b 1
)
if not exist "ipeia_academico\__init__.py" (
  echo ERRO: falta a pasta ipeia_academico. Copie a pasta inteira do projeto.
  exit /b 1
)

call .venv\Scripts\activate.bat
echo IPeia Academico - Ollama precisa estar aberto ^(localhost:11434^).
echo Abrindo http://localhost:8501 ...
streamlit run app.py
endlocal
