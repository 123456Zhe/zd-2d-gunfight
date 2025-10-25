#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ubuntu应用程序打包脚本
使用Nuitka将Python游戏打包为Ubuntu原生应用程序
"""

import os
import subprocess
import sys
import shutil
import platform

def check_system():
    """检查系统环境"""
    print("=== 系统环境检查 ===")
    print(f"操作系统: {platform.system()}")
    print(f"系统版本: {platform.release()}")
    print(f"架构: {platform.machine()}")
    print(f"Python版本: {sys.version}")
    
    if platform.system() != "Linux":
        print("警告: 此脚本专为Linux系统设计，在其他系统上可能无法正常工作")
    
    return True

def check_dependencies():
    """检查依赖项"""
    print("\n=== 依赖项检查 ===")
    
    # 检查Python包
    required_packages = ['pygame', 'nuitka']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n请安装缺失的包:")
        print(f"pip3 install {' '.join(missing_packages)}")
        return False
    
    # 检查系统依赖
    system_deps = {
        'gcc': 'gcc --version',
        'g++': 'g++ --version',
        'python3-dev': 'dpkg -l | grep python3-dev'
    }
    
    print("\n检查系统依赖:")
    for dep, cmd in system_deps.items():
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {dep} 可用")
            else:
                print(f"❌ {dep} 不可用")
        except FileNotFoundError:
            print(f"❌ {dep} 未找到")
    
    return True

def install_ubuntu_fonts():
    """安装Ubuntu中文字体支持"""
    print("\n=== 字体支持检查 ===")
    
    # 检查常用中文字体包
    font_packages = [
        'fonts-noto-cjk',      # Google Noto CJK字体
        'fonts-wqy-microhei',  # 文泉驿微米黑
        'fonts-wqy-zenhei',    # 文泉驿正黑
        'fonts-arphic-uming',  # 文鼎字体
        'fonts-droid-fallback' # Droid字体
    ]
    
    installed_fonts = []
    missing_fonts = []
    
    for font_pkg in font_packages:
        try:
            result = subprocess.run(['dpkg', '-l', font_pkg], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and 'ii' in result.stdout:
                print(f"✅ {font_pkg} 已安装")
                installed_fonts.append(font_pkg)
            else:
                print(f"❌ {font_pkg} 未安装")
                missing_fonts.append(font_pkg)
        except:
            print(f"❌ 无法检查 {font_pkg}")
            missing_fonts.append(font_pkg)
    
    if missing_fonts:
        print(f"\n建议安装中文字体支持:")
        print(f"sudo apt update")
        print(f"sudo apt install {' '.join(missing_fonts)}")
        
        # 询问是否自动安装
        try:
            choice = input("\n是否现在安装字体包? (y/N): ").strip().lower()
            if choice == 'y':
                print("正在安装字体包...")
                subprocess.run(['sudo', 'apt', 'update'])
                subprocess.run(['sudo', 'apt', 'install', '-y'] + missing_fonts)
                print("字体包安装完成")
        except KeyboardInterrupt:
            print("\n跳过字体安装")
    
    return True

def build_with_nuitka():
    """使用Nuitka打包Ubuntu应用程序"""
    print("\n=== 开始Nuitka打包 ===")
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, 'dist_ubuntu')
    
    # 清理旧的构建文件
    if os.path.exists(output_dir):
        print("清理旧的构建文件...")
        shutil.rmtree(output_dir)
    
    # Nuitka命令参数 - Ubuntu优化版本
    cmd = [
        sys.executable,
        '-m', 'nuitka',
        '--onefile',                    # 打包成单个文件
        '--enable-plugin=anti-bloat',   # 启用反膨胀插件
        '--include-module=pygame',      # 包含pygame模块
        '--include-module=socket',      # 包含网络模块
        '--include-module=threading',   # 包含线程模块
        '--include-module=json',        # 包含JSON模块
        '--include-module=ipaddress',   # 包含IP地址模块
        
        # 排除不需要的模块以减小文件大小
        '--nofollow-import-to=tkinter',
        '--nofollow-import-to=matplotlib',
        '--nofollow-import-to=numpy',
        '--nofollow-import-to=pandas',
        '--nofollow-import-to=scipy',
        '--nofollow-import-to=PIL',
        '--nofollow-import-to=cv2',
        
        # 输出配置
        '--output-dir=' + output_dir,
        '--output-filename=zd-2d-gunfight',  # Ubuntu风格的文件名
        
        # 优化选项
        '--assume-yes-for-downloads',
        '--show-progress',
        '--show-memory',
        
        # Linux特定选项
        '--linux-onefile-icon=icon.png',  # 如果有图标文件
        
        'main.py'
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    print("这可能需要几分钟时间，请耐心等待...")
    
    try:
        # 执行打包命令
        result = subprocess.run(cmd, cwd=current_dir)
        
        if result.returncode == 0:
            print("\n✅ Nuitka打包成功！")
            
            # 查找生成的可执行文件
            exe_path = os.path.join(output_dir, 'zd-2d-gunfight')
            if os.path.exists(exe_path):
                # 设置可执行权限
                os.chmod(exe_path, 0o755)
                
                # 显示文件信息
                file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
                print(f"生成的可执行文件: {exe_path}")
                print(f"文件大小: {file_size:.2f} MB")
                
                # 创建桌面快捷方式
                create_desktop_entry(exe_path)
                
                return True
            else:
                print("❌ 找不到生成的可执行文件")
                return False
        else:
            print("❌ Nuitka打包失败！")
            return False
            
    except FileNotFoundError:
        print("❌ 未找到Nuitka，请先安装：")
        print("pip3 install nuitka")
        return False
    except Exception as e:
        print(f"❌ 打包过程中出现错误: {e}")
        return False

def create_desktop_entry(exe_path):
    """创建桌面快捷方式"""
    print("\n=== 创建桌面快捷方式 ===")
    
    desktop_entry_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=ZD 2D Gunfight
Name[zh_CN]=ZD 2D 枪战游戏
Comment=A 2D multiplayer shooting game
Comment[zh_CN]=一个2D多人射击游戏
Exec={exe_path}
Icon=applications-games
Terminal=false
Categories=Game;ActionGame;
Keywords=game;shooting;multiplayer;
StartupNotify=true
"""
    
    # 保存到当前目录
    desktop_file = os.path.join(os.path.dirname(exe_path), 'zd-2d-gunfight.desktop')
    
    try:
        with open(desktop_file, 'w', encoding='utf-8') as f:
            f.write(desktop_entry_content)
        
        # 设置可执行权限
        os.chmod(desktop_file, 0o755)
        
        print(f"✅ 桌面快捷方式已创建: {desktop_file}")
        print("你可以将此文件复制到以下位置:")
        print("  - ~/.local/share/applications/ (用户应用)")
        print("  - /usr/share/applications/ (系统应用)")
        
        # 询问是否安装到用户应用目录
        try:
            choice = input("\n是否安装到用户应用目录? (y/N): ").strip().lower()
            if choice == 'y':
                user_apps_dir = os.path.expanduser('~/.local/share/applications')
                os.makedirs(user_apps_dir, exist_ok=True)
                
                user_desktop_file = os.path.join(user_apps_dir, 'zd-2d-gunfight.desktop')
                shutil.copy2(desktop_file, user_desktop_file)
                
                print(f"✅ 已安装到: {user_desktop_file}")
                print("现在可以在应用程序菜单中找到游戏了！")
        except KeyboardInterrupt:
            print("\n跳过安装")
            
    except Exception as e:
        print(f"❌ 创建桌面快捷方式失败: {e}")

def create_install_script():
    """创建安装脚本"""
    print("\n=== 创建安装脚本 ===")
    
    install_script_content = """#!/bin/bash
# ZD 2D Gunfight 游戏安装脚本

set -e

echo "=== ZD 2D Gunfight 安装程序 ==="

# 检查是否为root用户
if [[ $EUID -eq 0 ]]; then
   echo "请不要以root用户运行此脚本"
   exit 1
fi

# 创建应用程序目录
APP_DIR="$HOME/.local/share/zd-2d-gunfight"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo "创建目录..."
mkdir -p "$APP_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"

# 复制可执行文件
echo "安装游戏文件..."
cp zd-2d-gunfight "$APP_DIR/"
chmod +x "$APP_DIR/zd-2d-gunfight"

# 创建符号链接到bin目录
ln -sf "$APP_DIR/zd-2d-gunfight" "$BIN_DIR/zd-2d-gunfight"

# 复制桌面快捷方式
if [ -f "zd-2d-gunfight.desktop" ]; then
    cp zd-2d-gunfight.desktop "$DESKTOP_DIR/"
    # 更新桌面文件中的路径
    sed -i "s|Exec=.*|Exec=$APP_DIR/zd-2d-gunfight|" "$DESKTOP_DIR/zd-2d-gunfight.desktop"
fi

echo "✅ 安装完成！"
echo "你现在可以："
echo "  1. 在终端中运行: zd-2d-gunfight"
echo "  2. 在应用程序菜单中找到游戏"
echo ""
echo "卸载方法："
echo "  rm -rf '$APP_DIR'"
echo "  rm -f '$BIN_DIR/zd-2d-gunfight'"
echo "  rm -f '$DESKTOP_DIR/zd-2d-gunfight.desktop'"
"""
    
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist_ubuntu', 'install.sh')
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(install_script_content)
        
        os.chmod(script_path, 0o755)
        print(f"✅ 安装脚本已创建: {script_path}")
        
    except Exception as e:
        print(f"❌ 创建安装脚本失败: {e}")

def main():
    """主函数"""
    print("ZD 2D Gunfight - Ubuntu应用程序打包工具")
    print("=" * 50)
    
    # 检查系统环境
    if not check_system():
        return False
    
    # 检查依赖项
    if not check_dependencies():
        print("\n请先安装缺失的依赖项，然后重新运行此脚本")
        return False
    
    # 检查字体支持
    install_ubuntu_fonts()
    
    # 开始打包
    if build_with_nuitka():
        # 创建安装脚本
        create_install_script()
        
        print("\n" + "=" * 50)
        print("🎉 打包完成！")
        print("\n生成的文件:")
        print("  - dist_ubuntu/zd-2d-gunfight (可执行文件)")
        print("  - dist_ubuntu/zd-2d-gunfight.desktop (桌面快捷方式)")
        print("  - dist_ubuntu/install.sh (安装脚本)")
        print("\n使用方法:")
        print("  1. 直接运行: ./dist_ubuntu/zd-2d-gunfight")
        print("  2. 安装到系统: cd dist_ubuntu && ./install.sh")
        print("\n注意: 确保系统已安装中文字体以获得最佳显示效果")
        
        return True
    else:
        print("\n❌ 打包失败")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        sys.exit(1)