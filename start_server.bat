@echo off
echo.
echo =====================================================
echo  🎓 ERP Attendance Scraper Web Application
echo =====================================================
echo.
echo 📡 Starting server...
echo 🌐 Server will be available at: http://localhost:5000
echo ⏳ Please wait while the server starts up...
echo.

cd /d "%~dp0"

if not exist ".venv" (
    echo ❌ Error: Virtual environment not found!
    echo Please make sure you have set up the project correctly.
    pause
    exit /b 1
)

echo ✅ Activating virtual environment...
call .venv\Scripts\activate.bat

echo ✅ Starting Flask web application...
echo.
echo 💡 Tips:
echo    - Enter your roll number (e.g., 23R11A0590)
echo    - Wait 30-60 seconds for data extraction
echo    - Press Ctrl+C to stop the server
echo.
echo =====================================================

python app.py

echo.
echo 🛑 Server stopped.
pause
