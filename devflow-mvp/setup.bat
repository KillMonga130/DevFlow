@echo off
echo 🚀 DevFlow MVP Setup
echo.

echo Installing root dependencies...
call npm install
if %errorlevel% neq 0 (
    echo ❌ Root dependency installation failed
    pause
    exit /b 1
)

echo.
echo Installing server dependencies...
cd server
call npm install
if %errorlevel% neq 0 (
    echo ❌ Server dependency installation failed
    pause
    exit /b 1
)

echo.
echo Installing client dependencies...
cd ../client
call npm install
if %errorlevel% neq 0 (
    echo ❌ Client dependency installation failed
    pause
    exit /b 1
)

cd ..

echo.
echo ✅ Setup complete!
echo.
echo 🚀 To start DevFlow MVP:
echo    npm run dev
echo.
echo Or start components separately:
echo    Server: cd server && npm run dev
echo    Client: cd client && npm start
echo.
echo 🌐 Access at: http://localhost:3000
echo 📡 API at: http://localhost:3001
echo.
pause