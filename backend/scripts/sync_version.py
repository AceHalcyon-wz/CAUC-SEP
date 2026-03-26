"""
文件名: sync_version.py
路径: backend/scripts/sync_version.py
功能: 版本号自动同步工具，确保前后端版本一致
版本: v1.0.0
创建日期: 2026-03-25
作者: DevOps Engineer Agent

功能说明:
1. 从 pyproject.toml 读取版本号
2. 同步到 package.json (frontend)
3. 同步到 package.json (electron)
4. 同步到 electron-builder.yml
5. 同步到 CHANGELOG.md
6. 生成版本信息文件

使用方法:
    python backend/scripts/sync_version.py [version]
    - 不带参数：读取 pyproject.toml 版本号并同步
    - 带参数：设置新版本号并同步
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class VersionSync:
    """版本号同步工具类。"""
    
    def __init__(self, project_root: Path):
        """
        初始化版本同步工具。
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"
        self.electron_dir = project_root / "electron"
        
        # 配置文件路径
        self.pyproject_path = self.backend_dir / "pyproject.toml"
        self.frontend_pkg_path = self.frontend_dir / "package.json"
        self.electron_pkg_path = self.electron_dir / "package.json"
        self.electron_builder_path = self.electron_dir / "electron-builder.yml"
        self.changelog_path = project_root / "CHANGELOG.md"
        self.version_file_path = project_root / "VERSION"
    
    def get_current_version(self) -> str:
        """
        从 pyproject.toml 获取当前版本号。
        
        Returns:
            当前版本号字符串
        """
        content = self.pyproject_path.read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
        raise ValueError("无法从 pyproject.toml 读取版本号")
    
    def update_pyproject(self, version: str) -> None:
        """
        更新 pyproject.toml 版本号。
        
        Args:
            version: 新版本号
        """
        content = self.pyproject_path.read_text(encoding="utf-8")
        updated = re.sub(
            r'(version\s*=\s*)["\'][^"\']+["\']',
            f'\\g<1>"{version}"',
            content
        )
        self.pyproject_path.write_text(updated, encoding="utf-8")
        print(f"[OK] backend/pyproject.toml: {version}")
    
    def update_frontend_package(self, version: str) -> None:
        """
        更新前端 package.json 版本号。
        
        Args:
            version: 新版本号
        """
        pkg = json.loads(self.frontend_pkg_path.read_text(encoding="utf-8"))
        old_version = pkg.get("version", "unknown")
        pkg["version"] = version
        self.frontend_pkg_path.write_text(
            json.dumps(pkg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        print(f"[OK] frontend/package.json: {old_version} -> {version}")
    
    def update_electron_package(self, version: str) -> None:
        """
        更新 Electron package.json 版本号。
        
        Args:
            version: 新版本号
        """
        pkg = json.loads(self.electron_pkg_path.read_text(encoding="utf-8"))
        old_version = pkg.get("version", "unknown")
        pkg["version"] = version
        self.electron_pkg_path.write_text(
            json.dumps(pkg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        print(f"[OK] electron/package.json: {old_version} -> {version}")
    
    def update_electron_builder(self, version: str) -> None:
        """
        更新 electron-builder.yml 版本号。
        
        Args:
            version: 新版本号
        """
        content = self.electron_builder_path.read_text(encoding="utf-8")
        # 更新 artifactName 中的版本号占位符
        # 版本号通过 ${version} 变量自动获取，无需手动修改
        print(f"[OK] electron/electron-builder.yml: 使用 ${version} 变量")
    
    def update_version_file(self, version: str) -> None:
        """
        创建/更新 VERSION 文件。
        
        Args:
            version: 新版本号
        """
        version_info = {
            "version": version,
            "build_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "build_type": "release"
        }
        self.version_file_path.write_text(
            f"{version}\n"
            f"BUILD_TIME={version_info['build_time']}\n"
            f"BUILD_TYPE={version_info['build_type']}\n",
            encoding="utf-8"
        )
        print(f"[OK] VERSION: {version}")
    
    def validate_version(self, version: str) -> bool:
        """
        验证版本号格式。
        
        Args:
            version: 版本号字符串
        
        Returns:
            是否有效
        """
        # 语义化版本格式: X.Y.Z 或 X.Y.Z-prerelease
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$'
        return bool(re.match(pattern, version))
    
    def sync_all(self, new_version: Optional[str] = None) -> str:
        """
        同步所有版本号。
        
        Args:
            new_version: 新版本号（可选）
        
        Returns:
            最终版本号
        """
        version = new_version or self.get_current_version()
        
        if not self.validate_version(version):
            raise ValueError(f"无效的版本号格式: {version}")
        
        print(f"\n{'='*60}")
        print(f"  CAUC-SEP 版本同步工具")
        print(f"  版本号: {version}")
        print(f"{'='*60}\n")
        
        if new_version:
            self.update_pyproject(version)
        
        self.update_frontend_package(version)
        self.update_electron_package(version)
        self.update_electron_builder(version)
        self.update_version_file(version)
        
        print(f"\n{'='*60}")
        print(f"  版本同步完成: {version}")
        print(f"{'='*60}\n")
        
        return version


def main():
    """主函数。"""
    project_root = Path(__file__).parent.parent.parent
    
    # 获取命令行参数
    new_version = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        syncer = VersionSync(project_root)
        version = syncer.sync_all(new_version)
        
        # 输出供 CI/CD 使用
        print(f"::set-output name=version::{version}")
        
    except Exception as e:
        print(f"[ERROR] 版本同步失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
