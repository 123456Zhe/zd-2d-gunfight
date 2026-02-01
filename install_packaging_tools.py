import subprocess
import sys

def install_package(package):
    """安装单个包"""
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {package} 安装失败")
        return False

def install_all_tools():
    """安装所有打包工具"""
    
    packages = [
        'pyinstaller',
        'nuitka',
        'cx_Freeze',
        'upx',  # 用于压缩
    ]
    
    print("正在安装打包工具...")
    print("=" * 30)
    
    success_count = 0
    for package in packages:
        print(f"正在安装 {package}...")
        if install_package(package):
            success_count += 1
    
    print(f"\n安装完成: {success_count}/{len(packages)} 个包安装成功")
    
    if success_count == len(packages):
        print("所有打包工具已就绪！")
    else:
        print("部分工具安装失败，请手动安装失败的包")

def check_installations():
    """检查已安装的打包工具"""
    
    tools = {
        'PyInstaller': 'pyinstaller --version',
        'Nuitka': 'python -m nuitka --version',
        'cx_Freeze': 'python -m cx_Freeze --version',
    }
    
    print("检查已安装的打包工具...")
    print("=" * 30)
    
    for name, command in tools.items():
        try:
            result = subprocess.run(command.split(), 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ {name}: 已安装 ({result.stdout.strip()})")
            else:
                print(f"❌ {name}: 未安装")
        except:
            print(f"❌ {name}: 未安装或未找到")

if __name__ == "__main__":
    print("打包工具安装器")
    print("=" * 30)
    print("1. 安装所有打包工具")
    print("2. 检查已安装的工具")
    print("3. 安装单个工具")
    
    choice = input("请输入选择 (1-3): ").strip()
    
    if choice == "1":
        install_all_tools()
    elif choice == "2":
        check_installations()
    elif choice == "3":
        tool = input("请输入要安装的工具名称: ").strip()
        install_package(tool)
    else:
        print("无效选择")