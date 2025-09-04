#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ubuntu中文字体安装和检测脚本
确保游戏在Ubuntu系统上能正确显示中文
"""

import os
import subprocess
import sys
import pygame

def check_font_packages():
    """检查Ubuntu中文字体包安装状态"""
    print("=== Ubuntu中文字体检查 ===")
    
    # 推荐的中文字体包
    font_packages = {
        'fonts-noto-cjk': 'Google Noto CJK字体 (推荐)',
        'fonts-wqy-microhei': '文泉驿微米黑',
        'fonts-wqy-zenhei': '文泉驿正黑',
        'fonts-arphic-uming': '文鼎明体',
        'fonts-arphic-ukai': '文鼎楷体',
        'fonts-droid-fallback': 'Droid Fallback字体'
    }
    
    installed = []
    missing = []
    
    for package, description in font_packages.items():
        try:
            result = subprocess.run(['dpkg', '-l', package], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and 'ii' in result.stdout:
                print(f"✅ {package} - {description}")
                installed.append(package)
            else:
                print(f"❌ {package} - {description}")
                missing.append(package)
        except:
            print(f"❌ {package} - {description} (检查失败)")
            missing.append(package)
    
    return installed, missing

def test_pygame_fonts():
    """测试pygame字体加载"""
    print("\n=== Pygame字体测试 ===")
    
    # 初始化pygame字体系统
    pygame.font.init()
    
    # 测试字体列表
    test_fonts = [
        'Noto Sans CJK SC',
        'WenQuanYi Micro Hei',
        'WenQuanYi Zen Hei',
        'Droid Sans Fallback',
        'AR PL UMing CN',
        'AR PL UKai CN',
        'DejaVu Sans',
        'Liberation Sans'
    ]
    
    available_fonts = []
    
    for font_name in test_fonts:
        try:
            font = pygame.font.SysFont(font_name, 20)
            if font:
                print(f"✅ {font_name} - 可用")
                available_fonts.append(font_name)
        except:
            print(f"❌ {font_name} - 不可用")
    
    # 测试中文渲染
    if available_fonts:
        print(f"\n测试中文渲染 (使用 {available_fonts[0]}):")
        try:
            font = pygame.font.SysFont(available_fonts[0], 24)
            test_text = "中文测试 - ZD 2D 枪战游戏"
            surface = font.render(test_text, True, (255, 255, 255))
            print(f"✅ 中文渲染测试成功: '{test_text}'")
            print(f"   渲染尺寸: {surface.get_size()}")
        except Exception as e:
            print(f"❌ 中文渲染测试失败: {e}")
    else:
        print("❌ 没有可用的中文字体")
    
    return available_fonts

def install_recommended_fonts():
    """安装推荐的中文字体"""
    print("\n=== 安装推荐字体 ===")
    
    # 最小化字体包 - 只安装最必要的
    essential_fonts = [
        'fonts-noto-cjk',      # Google Noto CJK (最推荐)
        'fonts-wqy-microhei'   # 文泉驿微米黑 (备用)
    ]
    
    print("推荐安装以下字体包以获得最佳中文显示效果:")
    for font in essential_fonts:
        print(f"  - {font}")
    
    try:
        choice = input("\n是否现在安装? (y/N): ").strip().lower()
        if choice == 'y':
            print("正在更新包列表...")
            subprocess.run(['sudo', 'apt', 'update'], check=True)
            
            print("正在安装字体包...")
            subprocess.run(['sudo', 'apt', 'install', '-y'] + essential_fonts, check=True)
            
            print("✅ 字体安装完成！")
            
            # 刷新字体缓存
            print("刷新字体缓存...")
            subprocess.run(['fc-cache', '-fv'], capture_output=True)
            
            return True
        else:
            print("跳过字体安装")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n用户取消安装")
        return False

def show_manual_install_instructions():
    """显示手动安装说明"""
    print("\n=== 手动安装说明 ===")
    print("如果自动安装失败，请手动执行以下命令:")
    print()
    print("# 更新包列表")
    print("sudo apt update")
    print()
    print("# 安装基础中文字体 (选择一个即可)")
    print("sudo apt install fonts-noto-cjk          # Google Noto字体 (推荐)")
    print("sudo apt install fonts-wqy-microhei      # 文泉驿微米黑")
    print()
    print("# 安装完整中文字体支持 (可选)")
    print("sudo apt install fonts-noto-cjk fonts-wqy-microhei fonts-wqy-zenhei")
    print()
    print("# 刷新字体缓存")
    print("fc-cache -fv")
    print()
    print("安装完成后重新运行此脚本进行测试")

def create_font_test_script():
    """创建字体测试脚本"""
    test_script_content = '''#!/usr/bin/env python3
import pygame
import sys

def test_fonts():
    pygame.init()
    pygame.font.init()
    
    fonts = [
        'Noto Sans CJK SC',
        'WenQuanYi Micro Hei', 
        'WenQuanYi Zen Hei',
        'Droid Sans Fallback'
    ]
    
    print("字体测试结果:")
    for font_name in fonts:
        try:
            font = pygame.font.SysFont(font_name, 20)
            if font:
                text = font.render("中文测试", True, (255, 255, 255))
                print(f"✅ {font_name}: 可用 (尺寸: {text.get_size()})")
            else:
                print(f"❌ {font_name}: 不可用")
        except:
            print(f"❌ {font_name}: 加载失败")

if __name__ == "__main__":
    test_fonts()
'''
    
    with open('test_fonts.py', 'w', encoding='utf-8') as f:
        f.write(test_script_content)
    
    os.chmod('test_fonts.py', 0o755)
    print("✅ 字体测试脚本已创建: test_fonts.py")

def main():
    """主函数"""
    print("ZD 2D Gunfight - Ubuntu字体支持工具")
    print("=" * 40)
    
    # 检查是否在Linux系统上
    if os.name != 'posix':
        print("此脚本仅适用于Linux系统")
        return False
    
    # 检查字体包
    installed, missing = check_font_packages()
    
    # 测试pygame字体
    try:
        available_fonts = test_pygame_fonts()
    except Exception as e:
        print(f"❌ Pygame字体测试失败: {e}")
        print("请确保已安装pygame: pip3 install pygame")
        return False
    
    # 根据测试结果给出建议
    if not available_fonts:
        print("\n⚠️  警告: 没有检测到可用的中文字体")
        print("游戏可能无法正确显示中文文本")
        
        if missing:
            if install_recommended_fonts():
                print("\n重新测试字体...")
                available_fonts = test_pygame_fonts()
            else:
                show_manual_install_instructions()
        else:
            show_manual_install_instructions()
    
    elif len(available_fonts) < 2:
        print(f"\n⚠️  建议: 当前只有 {len(available_fonts)} 个中文字体可用")
        print("建议安装更多字体以获得更好的兼容性")
        
        if missing:
            install_recommended_fonts()
    
    else:
        print(f"\n✅ 字体支持良好! 检测到 {len(available_fonts)} 个可用中文字体")
        print("游戏应该能够正确显示中文文本")
    
    # 创建测试脚本
    create_font_test_script()
    
    print("\n" + "=" * 40)
    print("字体检查完成!")
    print("现在可以运行游戏或进行打包了")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)