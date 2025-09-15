@echo off
echo Starting DevFlow - Code Review Training Platform
echo.

echo Installing server dependencies...
cd server
call npm install
if %errorlevel% neq 0 (
    echo Error installing server dependencies
    pause
    exit /b 1
)

echo.
echo Setting up database with seed data...
call node seedData.js
if %errorlevel% neq 0 (
    echo Error setting up database
    pause
    exit /b 1
)

echo.
echo Starting backend server...
start "DevFlow Backend" cmd /k "npm run dev"

echo.
echo Waiting for backend to start...
timeout /t 3 /nobreak > nul

cd ..\client
echo Starting frontend...
start "DevFlow Frontend" cmd /k "npm start"

echo.
echo DevFlow is starting up!
echo Backend: http://localhost:3001
echo Frontend: http://localhost:3000
echo.
echo Press any key to exit this window...
pause > nul