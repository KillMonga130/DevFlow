@echo off
echo 🚀 DevFlow Quick Setup & Launch
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
call npm install socket.io-client lucide-react
if %errorlevel% neq 0 (
    echo ❌ Client dependency installation failed
    pause
    exit /b 1
)

echo.
echo Setting up environment...
cd ..
if not exist ".env" (
    copy ".env.example" ".env"
    echo ✅ Created .env file
)

echo.
echo Creating optimized AI model...
call train-devflow-model.bat

echo.
echo 🎉 Setup complete!
echo.
echo 🚀 Ready to launch DevFlow:
echo 1. Start server: cd server && npm run dev
echo 2. Start client: cd client && npm start
echo 3. Open http://localhost:3000
echo.
echo 💡 Your AI model will get smarter as users interact with it!
echo.
pause