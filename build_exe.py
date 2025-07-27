import os
import subprocess
import sys

def build_exe():
    """构建游戏的exe文件"""
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # PyInstaller命令参数
    cmd = [
        'pyinstaller',
        '--onefile',           # 打包成单个exe文件
        '--windowed',          # 不显示控制台窗口
        '--name=ZD-2D-Gunfight',  # exe文件名
        '--distpath=./dist',   # 输出目录
        '--workpath=./build',  # 临时工作目录
        '--clean',             # 清理临时文件
        '--noconfirm',         # 自动确认
        # 排除不需要的文件
        '--exclude-module=main_bak',
        # 添加所有需要的模块
        '--hidden-import=pygame',
        '--hidden-import=random',
        '--hidden-import=math',
        '--hidden-import=time',
        '--hidden-import=threading',
        '--hidden-import=json',
        '--hidden-import=socket',
        '--hidden-import=select',
        '--hidden-import=sys',
        '--hidden-import=os',
        'main.py'
    ]
    
    print("正在打包游戏...")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        # 执行打包命令
        result = subprocess.run(cmd, cwd=current_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 打包成功！")
            print(f"生成的exe文件位置: {os.path.join(current_dir, 'dist', 'ZD-2D-Gunfight.exe')}")
        else:
            print("❌ 打包失败！")
            print("错误信息:")
            print(result.stderr)
            
    except FileNotFoundError:
        print("❌ 未找到PyInstaller，请先安装：")
        print("pip install pyinstaller")
    except Exception as e:
        print(f"❌ 打包过程中出现错误: {e}")

if __name__ == "__main__":
    build_exe()