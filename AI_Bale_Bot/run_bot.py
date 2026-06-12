import subprocess

subprocess.Popen(["python", "bot/bot.py"])
subprocess.Popen(["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "10000"])