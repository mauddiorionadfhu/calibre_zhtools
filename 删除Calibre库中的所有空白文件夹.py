#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除 Calibre 库中的所有空白文件夹（递归）。
运行前请关闭 Calibre，并确认库路径。
"""

import os
import sys
import argparse

def is_empty(dir_path):
    """检查目录是否为空（无文件和子目录，忽略隐藏文件）"""
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                # 忽略隐藏文件/文件夹（Unix/Linux下以 . 开头，Windows下可选的隐藏属性这里不处理）
                if not entry.name.startswith('.'):
                    return False
            return True
    except PermissionError:
        print(f"权限不足，跳过: {dir_path}")
        return False

def remove_empty_folders(root_path, dry_run=False):
    """递归删除 root_path 下的所有空文件夹"""
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        # 忽略隐藏目录（可选）
        if os.path.basename(dirpath).startswith('.'):
            continue
        if is_empty(dirpath):
            if dry_run:
                print(f"[预览] 将删除空文件夹: {dirpath}")
            else:
                try:
                    os.rmdir(dirpath)   # 只能删除空目录
                    print(f"已删除空文件夹: {dirpath}")
                    removed += 1
                except OSError as e:
                    print(f"删除失败 {dirpath}: {e}")
    return removed

def main():
    parser = argparse.ArgumentParser(description="删除 Calibre 库中的空白文件夹")
    parser.add_argument('library', nargs='?', default='.',
                        help='Calibre库路径（默认为当前目录）')
    parser.add_argument('--dry-run', action='store_true',
                        help='仅预览，不实际删除')
    args = parser.parse_args()

    lib_path = os.path.abspath(args.library)
    if not os.path.isdir(lib_path):
        print(f"错误: 路径不存在 {lib_path}")
        sys.exit(1)

    # 确保目录是 Calibre 库（可选检查 metadata.db）
    if not os.path.isfile(os.path.join(lib_path, 'metadata.db')):
        print(f"警告: {lib_path} 中未找到 metadata.db，可能不是 Calibre 库根目录")

    print(f"扫描库目录: {lib_path}")
    removed = remove_empty_folders(lib_path, dry_run=args.dry_run)

    if args.dry_run:
        print(f"预览完成，发现 {removed} 个空文件夹（未实际删除）")
    else:
        print(f"清理完成，共删除 {removed} 个空文件夹")

if __name__ == '__main__':
    main()