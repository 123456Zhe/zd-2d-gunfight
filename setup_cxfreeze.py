
import sys
import os
from cx_Freeze import setup, Executable

# 基础配置
build_exe_options = {
    "packages": ["pygame", "random", "math", "json", "socket", "threading"],
    "excludes": ["tkinter", "matplotlib", "numpy", "pandas", "test"],
    "include_files": [],
    "optimize": 2,
    "compressed": True,
    "copy_dependent_files": True,
    "create_shared_zip": False,
    "include_in_shared_zip": False,
    "zip_includes": [],
    "zip_exclude_packages": ["pygame"],
    "build_exe": "./dist_cxfreeze"
}

# 设置可执行文件
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="ZD-2D-Gunfight",
    version="1.0",
    description="2D射击游戏",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base)]
)
