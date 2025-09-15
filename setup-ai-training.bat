@echo off
echo 🤖 DevFlow AI Training Setup
echo.

echo Creating training directories...
if not exist "server\training-data" mkdir "server\training-data"
if not exist "server\training-data\code-generation" mkdir "server\training-data\code-generation"
if not exist "server\training-data\code-analysis" mkdir "server\training-data\code-analysis"
if not exist "server\training-data\feedback" mkdir "server\training-data\feedback"
if not exist "scripts" mkdir "scripts"

echo.
echo Installing dependencies...
npm install

echo.
echo Setting up environment...
if not exist ".env" (
    copy ".env.example" ".env"
    echo ✅ Created .env file
) else (
    echo ⚠️  .env file already exists
)

echo.
echo 🚀 Ready to train your model!
echo.
echo Next steps:
echo 1. Run: train-devflow-model.bat
echo 2. Let users interact with DevFlow to collect training data
echo 3. Retrain periodically with: node scripts/fine-tune-model.js
echo.
echo The model will automatically get faster and more accurate as it learns from your specific use cases!
echo.
pause