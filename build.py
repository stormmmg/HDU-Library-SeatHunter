"""
SeatHunter 构建脚本
用法: python build.py
"""
import os
import sys
import shutil
import subprocess


def check_dependencies():
    """检查必要的依赖是否已安装"""
    print("=" * 50)
    print("检查依赖...")
    print("=" * 50)

    missing = []

    # 检查 PyInstaller
    try:
        import PyInstaller
        print(f"  [OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  [缺失] PyInstaller")
        missing.append("pyinstaller")

    # 检查项目依赖
    deps = ["playwright", "requests", "yaml", "prettytable", "pwinput", "win32gui"]
    for dep in deps:
        try:
            __import__(dep)
            print(f"  [OK] {dep}")
        except ImportError:
            # yaml 的包名是 PyYAML
            if dep == "yaml":
                try:
                    import yaml
                    print(f"  [OK] PyYAML")
                    continue
                except ImportError:
                    print(f"  [缺失] PyYAML")
                    missing.append("pyyaml")
                    continue
            print(f"  [缺失] {dep}")
            missing.append(dep)

    if missing:
        print(f"\n正在安装缺失的依赖: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("依赖安装完成。\n")

    # 确保 PyInstaller 可用
    try:
        import PyInstaller
    except ImportError:
        print("错误: PyInstaller 安装失败，请手动安装: pip install pyinstaller")
        sys.exit(1)


def find_playwright_chromium():
    """查找 Playwright Chromium 浏览器路径"""
    browsers_path = os.environ.get(
        'PLAYWRIGHT_BROWSERS_PATH',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ms-playwright')
    )

    if not os.path.exists(browsers_path):
        print("错误: 未找到 Playwright 浏览器目录。")
        print("请先运行: python -m playwright install chromium")
        sys.exit(1)

    for item in os.listdir(browsers_path):
        if item.startswith('chromium-') and not item.startswith('chromium_headless'):
            chromium_dir = os.path.join(browsers_path, item)
            # 确认 chrome.exe 存在
            if os.path.exists(os.path.join(chromium_dir, 'chrome-win64', 'chrome.exe')):
                print(f"  找到 Chromium: {chromium_dir}")
                return chromium_dir

    print("错误: 未找到 Playwright Chromium 浏览器。")
    print("请先运行: python -m playwright install chromium")
    sys.exit(1)


def run_pyinstaller():
    """运行 PyInstaller 构建"""
    print("\n" + "=" * 50)
    print("运行 PyInstaller...")
    print("=" * 50)

    spec_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SeatHunter.spec')
    subprocess.run(
        [sys.executable, '-m', 'PyInstaller', spec_file, '--clean', '--noconfirm'],
        check=True
    )


def copy_extra_files(dist_dir, chromium_dir):
    """复制额外文件到输出目录"""
    print("\n" + "=" * 50)
    print("复制额外文件...")
    print("=" * 50)

    project_root = os.path.dirname(os.path.abspath(__file__))

    # 复制 Chromium 浏览器
    chromium_dest = os.path.join(dist_dir, 'chromium')
    if os.path.exists(chromium_dest):
        print("  删除旧的 Chromium...")
        shutil.rmtree(chromium_dest)

    print(f"  复制 Chromium 浏览器（这可能需要几分钟）...")
    shutil.copytree(chromium_dir, chromium_dest)
    print(f"  [OK] Chromium -> {chromium_dest}")

    # 复制 docs 目录
    docs_src = os.path.join(project_root, 'docs')
    docs_dest = os.path.join(dist_dir, 'docs')
    if os.path.exists(docs_dest):
        shutil.rmtree(docs_dest)
    if os.path.exists(docs_src):
        shutil.copytree(docs_src, docs_dest)
        print(f"  [OK] docs -> {docs_dest}")

    # 创建空的 config 目录
    config_dest = os.path.join(dist_dir, 'config')
    os.makedirs(config_dest, exist_ok=True)
    print(f"  [OK] config 目录 -> {config_dest}")


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(project_root, 'dist', 'SeatHunter')

    print("SeatHunter 构建工具")
    print(f"项目目录: {project_root}")
    print()

    # 1. 检查依赖
    check_dependencies()

    # 2. 查找 Chromium
    print("\n查找 Playwright Chromium...")
    chromium_dir = find_playwright_chromium()

    # 3. 运行 PyInstaller
    run_pyinstaller()

    # 4. 复制额外文件
    copy_extra_files(dist_dir, chromium_dir)

    # 5. 完成
    print("\n" + "=" * 50)
    print("构建完成!")
    print("=" * 50)
    print(f"\n输出目录: {dist_dir}")
    print(f"\n使用方法:")
    print(f"  1. 将 {dist_dir} 整个文件夹分发给用户")
    print(f"  2. 用户运行 SeatHunter.exe 即可")
    print()

    # 显示总大小
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dist_dir):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    print(f"总大小: {total_size / (1024 * 1024):.1f} MB")


if __name__ == '__main__':
    main()
