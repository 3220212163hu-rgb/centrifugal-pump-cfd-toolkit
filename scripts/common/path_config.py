# -*- coding: utf-8 -*-
"""
路径配置模块：自动检测运行环境(WSL/Windows)并返回正确路径。

⚠️ 开源注意事项：
  - 所有路径通过环境变量配置，不再硬编码个人路径。
  - 设置 PROJECT_ROOT 环境变量指向项目根目录。
  - 或在项目根目录创建 .env 文件（参考 .env.example）。
"""
import os
import sys


def is_wsl():
    """检测是否在WSL环境中运行"""
    try:
        return 'microsoft' in os.uname().release.lower()
    except AttributeError:
        return False


def get_path(windows_path):
    """
    将Windows路径自动转换为当前环境的路径。
    示例: r"D:\\project\\data" → "/mnt/d/project/data" (WSL)
    """
    if is_wsl():
        path = windows_path.replace('\\', '/')
        for drive in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            path = path.replace(f'{drive}:/', f'/mnt/{drive.lower()}/')
        return path
    else:
        return windows_path


def _get_project_root():
    """获取项目根目录，优先环境变量，其次脚本位置推断。"""
    env_root = os.environ.get('PROJECT_ROOT')
    if env_root:
        return env_root
    # 回退：从当前文件位置向上两级 (scripts/common/ → 项目根)
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..')
    )


PROJECT_ROOT = _get_project_root()

# 常用路径（相对于项目根目录）
PROJECT_DIR = PROJECT_ROOT
QDRANT_PATH = os.environ.get(
    'QDRANT_PATH',
    os.path.join(PROJECT_ROOT, 'qdrant_data')
)
REF_DIR = os.environ.get(
    'REF_DIR',
    os.path.join(PROJECT_ROOT, '01-参考文献')
)
NOTES_DIR = os.environ.get(
    'NOTES_DIR',
    os.path.join(PROJECT_ROOT, '02-文献笔记')
)
HF_CACHE = os.environ.get(
    'HF_HOME',
    os.path.join(os.path.expanduser('~'), '.cache', 'huggingface')
)
