import cx_Freeze
import sys

base = None

if sys.platform == 'win32':
    base = "Win32GUI"

cx_Freeze.setup(
    name="Pool_IRL",
    options={"build_exe": {"packages": [
        "tkinter", "cv2", "PIL"], "include_files": ["images/"]}},
    version="0.02",
    description="Pool IRL",
    executables=[cx_Freeze.Executable(
        "app.py", base=base, targetName="Pool IRL")]
)
