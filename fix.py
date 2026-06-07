import subprocess
import sys

print("Target Python executable:", sys.executable)
print("Installing openai...")

try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "openai"])
    print("\n Success! 'openai' has been installed into your environment.")
except Exception as e:
    print("\n Error during installation:", e)
