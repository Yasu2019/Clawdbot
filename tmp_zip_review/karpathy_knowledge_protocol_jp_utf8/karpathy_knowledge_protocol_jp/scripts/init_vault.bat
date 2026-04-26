\
@echo off
set ROOT=D:\KnowledgeVault

mkdir "%ROOT%\raw\web" 2>nul
mkdir "%ROOT%\raw\pdf" 2>nul
mkdir "%ROOT%\raw\papers" 2>nul
mkdir "%ROOT%\raw\internal" 2>nul
mkdir "%ROOT%\raw\images" 2>nul

mkdir "%ROOT%\processed\summaries" 2>nul
mkdir "%ROOT%\processed\indexes" 2>nul
mkdir "%ROOT%\processed\entities" 2>nul
mkdir "%ROOT%\processed\relations" 2>nul

mkdir "%ROOT%\wiki\topics" 2>nul
mkdir "%ROOT%\wiki\qa" 2>nul
mkdir "%ROOT%\wiki\projects" 2>nul
mkdir "%ROOT%\wiki\glossary" 2>nul
mkdir "%ROOT%\wiki\decision_logs" 2>nul

mkdir "%ROOT%\inbox" 2>nul
mkdir "%ROOT%\archive" 2>nul
mkdir "%ROOT%\prompts" 2>nul
mkdir "%ROOT%\scripts" 2>nul
mkdir "%ROOT%\config" 2>nul

echo KnowledgeVault folders created at %ROOT%
pause
