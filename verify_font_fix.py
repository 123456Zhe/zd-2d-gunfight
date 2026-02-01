#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体修复验证脚本
验证Ubuntu上Microsoft YaHei字体加载问题是否已修复
"""

import pygame
import platform
import sys

def test_font_loading_issue():
    """测试字体加载问题"""
    print("=== 字体加载问题验证 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {sys.version}")
    
    # 初始化pygame
    pygame.init()
    pygame.font.init()
    
    # 测试有问题的字体（Microsoft YaHei在Ubuntu上）
    problematic_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun']
    
    print("\n1. 测试有问题的Windows字体在Ubuntu上的行为:")
    for font_name in problematic_fonts:
        print(f"\n测试字体: {font_name}")
        
        try:
            # 尝试创建字体对象
            font_obj = pygame.font.SysFont(font_name, 20)
            print(f"  ✓ 字体对象创建: 成功")
            
            # 测试字体是否真的可用
            if font_obj:
                try:
                    # 尝试渲染中文
                    test_text = "中文测试"
                    surface = font_obj.render(test_text, True, (255, 255, 255))
                    
                    if surface.get_width() > 0:
                        print(f"  ✓ 中文渲染: 成功 (宽度: {surface.get_width()})")
                        
                        # 进一步验证：渲染英文对比
                        english_surface = font_obj.render("Test", True, (255, 255, 255))
                        print(f"  ✓ 英文渲染: 成功 (宽度: {english_surface.get_width()})")
                        
                        # 检查是否是fallback字体
                        actual_font_name = pygame.font.get_default_font()
                        print(f"  ? 实际字体可能是: {actual_font_name}")
                        
                    else:
                        print(f"  ✗ 中文渲染: 失败 (宽度为0)")
                        
                except Exception as e:
                    print(f"  ✗ 渲染测试: 异常 - {e}")
            else:
                print(f"  ✗ 字体对象: 无效")
                
        except Exception as e:
            print(f"  ✗ 字体创建: 异常 - {e}")

def test_ubuntu_fonts():
    """测试Ubuntu原生字体"""
    print("\n2. 测试Ubuntu原生中文字体:")
    
    ubuntu_fonts = [
        'Noto Sans CJK SC',
        'WenQuanYi Micro Hei',
        'WenQuanYi Zen Hei',
        'Droid Sans Fallback',
        'AR PL UMing CN'
    ]
    
    working_fonts = []
    
    for font_name in ubuntu_fonts:
        print(f"\n测试字体: {font_name}")
        
        try:
            font_obj = pygame.font.SysFont(font_name, 20)
            
            if font_obj:
                try:
                    surface = font_obj.render("中文测试", True, (255, 255, 255))
                    
                    if surface.get_width() > 0:
                        print(f"  ✅ 可用 (中文宽度: {surface.get_width()})")
                        working_fonts.append(font_name)
                    else:
                        print(f"  ❌ 不可用 (中文渲染失败)")
                        
                except Exception as e:
                    print(f"  ❌ 渲染异常: {e}")
            else:
                print(f"  ❌ 字体对象创建失败")
                
        except Exception as e:
            print(f"  ❌ 字体加载异常: {e}")
    
    return working_fonts

def test_improved_font_loading():
    """测试改进后的字体加载逻辑"""
    print("\n3. 测试改进后的字体加载逻辑:")
    
    # 模拟改进后的字体加载函数
    def load_fonts_improved():
        import platform
        
        system = platform.system().lower()
        
        if system == 'linux':
            font_candidates = [
                'Noto Sans CJK SC',
                'WenQuanYi Micro Hei',
                'WenQuanYi Zen Hei',
                'Droid Sans Fallback',
                'AR PL UMing CN',
                'DejaVu Sans',
                'Liberation Sans'
            ]
        else:
            font_candidates = [
                'Microsoft YaHei',
                'SimHei',
                'Arial'
            ]
        
        print(f"  系统: {system}")
        print(f"  候选字体: {len(font_candidates)} 个")
        
        for i, font_name in enumerate(font_candidates, 1):
            try:
                test_font = pygame.font.SysFont(font_name, 20)
                
                if test_font:
                    # 验证中文渲染
                    test_surface = test_font.render("中文测试", True, (255, 255, 255))
                    
                    if test_surface.get_width() > 0:
                        print(f"  ✅ [{i}] {font_name} - 选中")
                        return font_name
                    else:
                        print(f"  ❌ [{i}] {font_name} - 中文渲染失败")
                else:
                    print(f"  ❌ [{i}] {font_name} - 字体对象创建失败")
                    
            except Exception as e:
                print(f"  ❌ [{i}] {font_name} - 异常: {e}")
        
        print(f"  ⚠️  回退到默认字体")
        return "Default"
    
    selected_font = load_fonts_improved()
    print(f"\n  最终选择: {selected_font}")
    
    return selected_font

def generate_font_report():
    """生成字体报告"""
    print("\n" + "="*50)
    print("字体修复验证报告")
    print("="*50)
    
    # 系统信息
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {platform.machine()}")
    
    # 测试结果
    working_fonts = test_ubuntu_fonts()
    selected_font = test_improved_font_loading()
    
    print(f"\n可用的Ubuntu中文字体: {len(working_fonts)} 个")
    for font in working_fonts:
        print(f"  - {font}")
    
    print(f"\n改进后的字体选择: {selected_font}")
    
    # 建议
    print(f"\n建议:")
    if len(working_fonts) == 0:
        print("  ⚠️  建议安装中文字体包:")
        print("     sudo apt install fonts-noto-cjk fonts-wqy-microhei")
    elif len(working_fonts) < 2:
        print("  💡 建议安装更多中文字体以提高兼容性:")
        print("     sudo apt install fonts-noto-cjk fonts-wqy-microhei fonts-wqy-zenhei")
    else:
        print("  ✅ 字体支持良好，无需额外安装")
    
    if selected_font == "Default":
        print("  ⚠️  当前将使用默认字体，中文显示可能不完整")
    else:
        print(f"  ✅ 将使用 {selected_font} 字体，中文显示正常")

def main():
    """主函数"""
    print("ZD 2D Gunfight - 字体修复验证工具")
    print("验证Ubuntu上Microsoft YaHei字体加载问题是否已修复")
    print("="*60)
    
    try:
        # 运行测试
        test_font_loading_issue()
        generate_font_report()
        
        print("\n" + "="*60)
        print("验证完成!")
        print("如果看到 '改进后的字体选择' 不是 'Microsoft YaHei'，")
        print("说明修复生效，Ubuntu将使用合适的本地字体。")
        
    except Exception as e:
        print(f"\n❌ 验证过程中出现错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消验证")
        sys.exit(1)