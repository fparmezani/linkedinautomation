@echo off
cd /d "C:\Projetos\LinkedinAutomation"
call .venv\Scripts\activate.bat
python orchestrator.py --auto
