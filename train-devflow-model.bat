@echo off
echo 🚀 DevFlow Model Training Script
echo.

echo Checking Ollama installation...
ollama --version
if %errorlevel% neq 0 (
    echo ❌ Ollama not found. Please install Ollama first.
    pause
    exit /b 1
)

echo.
echo Pulling base GPT-OSS model...
ollama pull gpt-oss:20b

echo.
echo Creating DevFlow-optimized model...
node scripts/create-devflow-model.js

echo.
echo ✅ Training complete! 
echo.
echo Next steps:
echo 1. Update your .env file with the new model name
echo 2. Restart DevFlow to use the optimized model
echo 3. The model will get better as users interact with it
echo.
pause