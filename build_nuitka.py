import os
import subprocess
import sys

def build_with_nuitka():
    """使用Nuitka进行更优化的打包，生成更小的exe文件"""
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Nuitka命令参数 - 简化版本
    cmd = [
        sys.executable,
        '-m', 'nuitka',
        # '--standalone',           # 独立可执行文件
        '--onefile',              # 打包成单个文件
        '--windows-disable-console',  # 禁用控制台窗口
        '--enable-plugin=anti-bloat',  # 启用反膨胀插件
        '--include-module=pygame',     # 包含pygame模块
        '--nofollow-import-to=tkinter',   # 排除tkinter
        '--nofollow-import-to=matplotlib', # 排除matplotlib
        # '--nofollow-import-to=numpy',    # 排除numpy 现在用了这个库，不能排除了
        '--nofollow-import-to=pandas',   # 排除pandas
        '--output-dir=./dist_nuitka',  # 输出目录
        '--assume-yes-for-downloads',  # 自动下载依赖
        # '--quiet',                # 静默模式，减少输出
        'main.py'
    ]
    
    print("正在使用Nuitka进行优化打包...")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        # 执行打包命令
        result = subprocess.run(cmd, cwd=current_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Nuitka打包成功！")
            print(f"生成的exe文件位置: {os.path.join(current_dir, 'dist_nuitka', 'main.exe')}")
            print("文件大小应该比PyInstaller打包的小30-50%")
        else:
            print("❌ Nuitka打包失败！")
            print("错误信息:")
            print(result.stderr)
            
    except FileNotFoundError:
        print("❌ 未找到Nuitka，请先安装：")
        print("pip install nuitka")
    except Exception as e:
        print(f"❌ 打包过程中出现错误: {e}")

def build_with_cx_freeze():
    """使用cx_Freeze进行打包"""
    
    # cx_Freeze setup脚本内容
    setup_content = '''
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
'''
    
    # 写入setup脚本
    with open('setup_cxfreeze.py', 'w', encoding='utf-8') as f:
        f.write(setup_content)
    
    cmd = [sys.executable, 'setup_cxfreeze.py', 'build']
    
    print("正在使用cx_Freeze进行打包...")
    try:
        result = subprocess.run(cmd, cwd=current_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ cx_Freeze打包成功！")
            print(f"生成的exe文件位置: {os.path.join(current_dir, 'dist_cxfreeze')}")
        else:
            print("❌ cx_Freeze打包失败！")
            print(result.stderr)
            
    except FileNotFoundError:
        print("❌ 未找到cx_Freeze，请先安装：")
        print("pip install cx_Freeze")

if __name__ == "__main__":
    
    choice = 1
    
    if choice == "1":
        build_with_nuitka()
    elif choice == "2":
        build_with_cx_freeze()
    else:
        print("无效选择，退出")
