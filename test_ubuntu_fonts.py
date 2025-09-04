#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ubuntu字体加载测试脚本
测试游戏中的字体加载功能是否正常工作
"""

import pygame
import sys
import os

def load_fonts():
    """加载字体，支持Windows、Ubuntu和其他Linux发行版"""
    import platform
    
    # 检测操作系统
    system = platform.system().lower()
    
    # 根据操作系统选择字体候选列表
    if system == 'windows':
        font_candidates = [
            'Microsoft YaHei',
            'SimHei',
            'SimSun',
            'Arial Unicode MS',
            'DejaVu Sans',
            'Arial'
        ]
    elif system == 'linux':
        # Linux/Ubuntu字体优先级
        font_candidates = [
            'Noto Sans CJK SC',      # Ubuntu默认中文字体
            'Noto Sans CJK TC',      # 繁体中文
            'WenQuanYi Micro Hei',   # 文泉驿微米黑
            'WenQuanYi Zen Hei',     # 文泉驿正黑
            'Droid Sans Fallback',   # Android字体
            'AR PL UMing CN',        # 文鼎明体
            'AR PL UKai CN',         # 文鼎楷体
            'DejaVu Sans',           # 通用字体
            'Liberation Sans',       # LibreOffice字体
            'FreeSans'               # GNU字体
        ]
    elif system == 'darwin':  # macOS
        font_candidates = [
            'PingFang SC',
            'Hiragino Sans GB',
            'STHeiti',
            'Arial Unicode MS',
            'Helvetica',
            'Arial'
        ]
    else:
        # 其他系统使用通用字体
        font_candidates = [
            'DejaVu Sans',
            'Liberation Sans',
            'FreeSans',
            'Arial'
        ]
    
    print("=== 字体加载测试 ===")
    print(f"检测到操作系统: {system}")
    print(f"测试 {len(font_candidates)} 个字体候选...")
    
    # 尝试加载字体并验证中文渲染
    for i, font_name in enumerate(font_candidates, 1):
        try:
            # 尝试创建字体对象
            test_font = pygame.font.SysFont(font_name, 20)
            
            if test_font:
                # 验证字体是否能正确渲染中文
                try:
                    # 测试中文渲染
                    chinese_text = "中文测试"
                    surface = test_font.render(chinese_text, True, (255, 255, 255))
                    
                    # 检查渲染结果是否有效（宽度大于0）
                    if surface.get_width() > 0:
                        print(f"✅ [{i:2d}] {font_name} - 加载成功，中文渲染正常 (尺寸: {surface.get_size()})")
                        
                        return {
                            'font': pygame.font.SysFont(font_name, 20),
                            'small_font': pygame.font.SysFont(font_name, 16),
                            'large_font': pygame.font.SysFont(font_name, 28),
                            'title_font': pygame.font.SysFont(font_name, 40),
                            'font_name': font_name
                        }
                    else:
                        print(f"❌ [{i:2d}] {font_name} - 中文渲染失败 (宽度为0)")
                        
                except Exception as render_error:
                    print(f"❌ [{i:2d}] {font_name} - 中文渲染异常: {render_error}")
                    continue
            else:
                print(f"❌ [{i:2d}] {font_name} - 字体对象创建失败")
                
        except Exception as font_error:
            print(f"❌ [{i:2d}] {font_name} - 字体加载异常: {font_error}")
            continue
    
    # 如果所有字体都失败，使用默认字体
    print("\n⚠️  警告: 无法加载任何系统字体，使用默认字体")
    print("建议安装中文字体包以获得更好的显示效果")
    
    if system == 'linux':
        print("Ubuntu/Linux用户可以运行: sudo apt install fonts-noto-cjk fonts-wqy-microhei")
    
    return {
        'font': pygame.font.Font(None, 20),
        'small_font': pygame.font.Font(None, 16),
        'large_font': pygame.font.Font(None, 28),
        'title_font': pygame.font.Font(None, 40),
        'font_name': 'Default'
    }

def test_font_rendering(fonts):
    """测试字体渲染效果"""
    print(f"\n=== 字体渲染测试 (使用: {fonts['font_name']}) ===")
    
    test_texts = [
        ("英文测试", "English Test"),
        ("中文测试", "ZD 2D 枪战游戏"),
        ("数字测试", "12345 67890"),
        ("符号测试", "!@#$%^&*()"),
        ("混合测试", "Player玩家123")
    ]
    
    for test_name, text in test_texts:
        try:
            # 测试不同大小的字体
            for font_type, font_obj in fonts.items():
                if font_type == 'font_name':
                    continue
                    
                surface = font_obj.render(text, True, (255, 255, 255))
                size = surface.get_size()
                print(f"✅ {test_name} ({font_type}): '{text}' -> {size}")
                
        except Exception as e:
            print(f"❌ {test_name}: 渲染失败 - {e}")

def create_visual_test():
    """创建可视化测试窗口"""
    print("\n=== 创建可视化测试窗口 ===")
    
    try:
        # 初始化pygame
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("ZD 2D Gunfight - 字体测试")
        
        # 加载字体
        fonts = load_fonts()
        
        # 测试文本
        test_texts = [
            (fonts['title_font'], "ZD 2D 枪战游戏", (255, 255, 0)),
            (fonts['large_font'], "字体测试 Font Test", (255, 255, 255)),
            (fonts['font'], f"当前字体: {fonts['font_name']}", (0, 255, 0)),
            (fonts['font'], "玩家1 连接成功", (0, 255, 255)),
            (fonts['font'], "弹药: 30/30  生命值: 100", (255, 255, 255)),
            (fonts['small_font'], "按ESC键退出测试", (128, 128, 128)),
        ]
        
        # 主循环
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # 清屏
            screen.fill((50, 50, 50))
            
            # 渲染测试文本
            y_offset = 100
            for font_obj, text, color in test_texts:
                try:
                    surface = font_obj.render(text, True, color)
                    x = (800 - surface.get_width()) // 2
                    screen.blit(surface, (x, y_offset))
                    y_offset += surface.get_height() + 20
                except Exception as e:
                    print(f"渲染错误: {e}")
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()
        print("✅ 可视化测试完成")
        
    except Exception as e:
        print(f"❌ 可视化测试失败: {e}")

def main():
    """主函数"""
    print("ZD 2D Gunfight - Ubuntu字体测试")
    print("=" * 40)
    
    try:
        # 初始化pygame
        pygame.init()
        pygame.font.init()
        
        # 加载字体
        fonts = load_fonts()
        
        # 测试字体渲染
        test_font_rendering(fonts)
        
        # 询问是否进行可视化测试
        print("\n" + "=" * 40)
        try:
            choice = input("是否进行可视化测试? (y/N): ").strip().lower()
            if choice == 'y':
                create_visual_test()
        except KeyboardInterrupt:
            print("\n跳过可视化测试")
        
        print("\n字体测试完成!")
        print(f"推荐字体: {fonts['font_name']}")
        
        if fonts['font_name'] == 'Default':
            print("\n⚠️  建议安装中文字体以获得更好的显示效果:")
            print("sudo apt install fonts-noto-cjk fonts-wqy-microhei")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户取消测试")
        sys.exit(1)