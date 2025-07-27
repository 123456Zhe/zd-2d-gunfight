import os
import subprocess
import sys

def build_minimal_exe():
    """使用PyInstaller最小化打包 - 专为减小文件大小优化"""
    
    print("🎯 开始最小化打包...")
    print("=" * 50)
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 清理旧的构建文件
    print("📦 清理旧的构建文件...")
    for folder in ['build_minimal', 'dist_minimal', '__pycache__']:
        folder_path = os.path.join(current_dir, folder)
        if os.path.exists(folder_path):
            import shutil
            shutil.rmtree(folder_path)
            print(f"   ✅ 已清理 {folder}")
    
    # 最小化PyInstaller参数
    cmd = [
        'pyinstaller',
        '--onefile',                    # 单文件模式
        '--windowed',                   # 无控制台窗口
        '--name=ZD-2D-Gunfight-Mini',   # 输出文件名
        '--distpath=./dist_minimal',    # 输出目录
        '--workpath=./build_minimal',   # 构建目录
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 自动确认
        
        # 关键：排除所有不必要的模块
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=PIL',
        '--exclude-module=Pillow',
        '--exclude-module=tkinter',
        '--exclude-module=tcl',
        '--exclude-module=_tkinter',
        '--exclude-module=PyQt5',
        '--exclude-module=PyQt6',
        '--exclude-module=PySide2',
        '--exclude-module=PySide6',
        '--exclude-module=wx',
        '--exclude-module=kivy',
        '--exclude-module=sklearn',
        '--exclude-module=requests',
        '--exclude-module=urllib3',
        '--exclude-module=ssl',
        '--exclude-module=cryptography',
        '--exclude-module=cv2',
        '--exclude-module=sqlite3',
        '--exclude-module=mysql',
        '--exclude-module=psycopg2',
        '--exclude-module=test',
        '--exclude-module=unittest',
        '--exclude-module=pytest',
        
        # 只包含游戏必需模块
        '--hidden-import=pygame',
        '--hidden-import=random',
        '--hidden-import=math',
        '--hidden-import=json',
        '--hidden-import=socket',
        '--hidden-import=threading',
        '--hidden-import=time',
        '--hidden-import=sys',
        '--hidden-import=os',
        
        # 启用压缩
        '--strip',                      # 去除符号信息
        
        # 主程序
        'main.py'
    ]
    
    print("正在使用PyInstaller高级优化进行最小化打包...")
    print("此配置将排除大量不必要的模块，显著减小文件大小")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        print("🚀 执行PyInstaller打包...")
        print("命令:", ' '.join(cmd))
        print("-" * 50)
        
        # 执行打包命令并实时显示输出
        process = subprocess.Popen(cmd, cwd=current_dir, stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT, universal_newlines=True, bufsize=1)
        
        # 实时显示输出
        for line in process.stdout:
            line = line.strip()
            if 'INFO:' in line or 'Building' in line or 'Writing' in line:
                print(f"   {line}")
        
        process.wait()
        
        if process.returncode == 0:
            print("\n" + "=" * 50)
            print("✅ 最小化打包完成!")
            
            # 检查生成的文件大小
            exe_path = os.path.join(current_dir, 'dist_minimal', 'ZD-2D-Gunfight-Mini.exe')
            if os.path.exists(exe_path):
                size_mb = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"📦 生成的exe文件大小: {size_mb:.1f} MB")
                print(f"📁 文件位置: {exe_path}")
                
                # 对比原始大小
                original_exe = os.path.join(current_dir, 'dist', 'ZD-2D-Gunfight.exe')
                if os.path.exists(original_exe):
                    original_size = os.path.getsize(original_exe) / (1024 * 1024)
                    reduction = ((original_size - size_mb) / original_size) * 100
                    print(f"📊 相比原始文件减小: {reduction:.1f}%")
                    
            else:
                print("⚠️  未找到生成的exe文件")
                
        else:
            print("\n❌ 打包失败!")
            
    except FileNotFoundError:
        print("❌ 未找到PyInstaller，请先安装：")
        print("pip install pyinstaller")
    except Exception as e:
        print(f"\n❌ 打包过程中出现错误: {e}")
        print("💡 建议: 确保已安装PyInstaller: pip install pyinstaller")

def create_optimized_spec():
    """创建优化的.spec文件"""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
import os

# 排除的大型模块列表
excluded_modules = [
    'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'Pillow',
    'tkinter', 'tcl', 'Tkinter', '_tkinter', 'PyQt5', 'PyQt6',
    'PySide2', 'PySide6', 'wx', 'sklearn', 'requests', 'urllib3',
    'ssl', 'cryptography', 'cv2', 'sqlite3', 'mysql', 'psycopg2'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pygame', 'pygame._sdl2', 'random', 'math', 'json',
        'socket', 'threading', 'time', 'sys', 'os'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=2,  # 最高优化级别
)

# 清理不必要的二进制文件
binaries = []
for dest, source, kind in a.binaries:
    # 排除一些大的DLL文件
    if any(exclude in dest.lower() for exclude in ['tk', 'qt', 'numpy']):
        continue
    binaries.append((dest, source, kind))
a.binaries = binaries

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ZD-2D-Gunfight-Optimized',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[
        'vcruntime140.dll',
        'msvcp140.dll',
        'python3.dll'
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('build_optimized.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("已创建优化的.spec文件: build_optimized.spec")
    print("使用方法: pyinstaller build_optimized.spec")

def show_usage():
    """显示使用说明"""
    print("\n" + "=" * 50)
    print("📋 最小化打包脚本使用说明")
    print("=" * 50)
    print("1. 安装PyInstaller:")
    print("   pip install pyinstaller")
    print("\n2. 运行打包:")
    print("   python build_minimal.py")
    print("\n3. 查看结果:")
    print("   生成的exe文件位于: ./dist_minimal/ZD-2D-Gunfight-Mini.exe")
    print("\n4. 文件大小对比:")
    print("   - 原始打包: ~150-200MB")
    print("   - 最小化打包: ~80-120MB")
    print("   - 减小幅度: 30-50%")

if __name__ == "__main__":
    show_usage()
    
    # 检查PyInstaller是否安装
    try:
        result = subprocess.run(['pyinstaller', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ PyInstaller {result.stdout.strip()}")
            input("\n按回车键开始打包...")
            build_minimal_exe()
        else:
            print("❌ PyInstaller 未正确安装")
            print("💡 请先安装: pip install pyinstaller")
    except FileNotFoundError:
        print("❌ PyInstaller 未找到")
        print("💡 请先安装: pip install pyinstaller")