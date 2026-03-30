#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calibre 批量删除书籍标签工具
--------------------------------
删除 Calibre 库中所有书籍的标签（清空 books_tags_link 表）。
可选同时删除所有标签定义（清空 tags 表）。
"""

import os
import sys
import sqlite3
import argparse
import shutil

# 配置参数
DEFAULT_LIBRARY_PATH = "PPES"          # 默认库路径（可修改）
DRY_RUN = True                         # 仅预览
BACKUP_DB = True                         # 备份数据库
PURGE_TAGS = True                        # 是否同时删除所有标签定义


def get_calibre_db_path(library_path):
    """返回metadata.db的完整路径"""
    db_path = os.path.join(library_path, 'metadata.db')
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"在 {library_path} 中未找到 metadata.db")
    return db_path


def backup_database(db_path):
    """备份metadata.db"""
    backup_path = db_path + '.backup'
    if not os.path.exists(backup_path):
        shutil.copy2(db_path, backup_path)
        print(f"已备份数据库到: {backup_path}")
    else:
        print(f"备份文件已存在，跳过备份: {backup_path}")


def create_calibre_connection(db_path):
    """
    创建 SQLite 连接并注册 Calibre 自定义函数（如 title_sort），避免触发器报错。
    """
    conn = sqlite3.connect(db_path)

    def title_sort(title):
        return title if title is not None else ""
    conn.create_function("title_sort", 1, title_sort)

    # 如果有其他自定义函数（如 author_sort）导致错误，可类似添加
    # def author_sort(author):
    #     return author if author is not None else ""
    # conn.create_function("author_sort", 1, author_sort)

    return conn


def count_affected(conn):
    """返回当前关联数量和标签数量"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM books_tags_link")
    link_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tags")
    tags_count = cursor.fetchone()[0]
    return link_count, tags_count


def delete_all_tags(conn, dry_run=False, purge=False):
    """
    删除所有书籍的标签关联，可选同时删除所有标签定义。
    返回 (link_deleted, tags_deleted) 受影响的行数。
    """
    cursor = conn.cursor()
    link_before, tags_before = count_affected(conn)

    if dry_run:
        return link_before, (tags_before if purge else 0)

    try:
        cursor.execute("BEGIN TRANSACTION")

        # 删除所有书籍-标签关联
        cursor.execute("DELETE FROM books_tags_link")
        link_deleted = cursor.rowcount

        # 如果要求同时删除标签定义，清空 tags 表
        tags_deleted = 0
        if purge:
            cursor.execute("DELETE FROM tags")
            tags_deleted = cursor.rowcount

        conn.commit()
        return link_deleted, tags_deleted
    except Exception as e:
        conn.rollback()
        raise e


def main():
    parser = argparse.ArgumentParser(description="删除 Calibre 库中所有书籍的标签")
    parser.add_argument('library', nargs='?', default=DEFAULT_LIBRARY_PATH,
                        help='Calibre库路径（默认为配置的PPES）')
    parser.add_argument('--dry-run', action='store_true', default=DRY_RUN,
                        help='仅预览，不实际修改')
    parser.add_argument('--no-backup', dest='backup', action='store_false', default=BACKUP_DB,
                        help='不备份数据库')
    parser.add_argument('--purge', action='store_true', default=PURGE_TAGS,
                        help='同时删除所有标签定义（清空 tags 表）')
    args = parser.parse_args()

    library_path = os.path.abspath(args.library)
    if not os.path.isdir(library_path):
        print(f"错误: 库路径不存在 {library_path}")
        sys.exit(1)

    try:
        db_path = get_calibre_db_path(library_path)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)

    if args.backup and not args.dry_run:
        backup_database(db_path)

    print(f"连接数据库: {db_path}")
    conn = create_calibre_connection(db_path)

    # 预览信息
    link_count, tags_count = count_affected(conn)
    print(f"当前书籍标签关联数量: {link_count}")
    print(f"当前标签定义数量: {tags_count}")

    if args.dry_run:
        print("\n[预览模式] 将执行以下操作：")
        print(f"  - 删除所有书籍标签关联（共 {link_count} 条）")
        if args.purge:
            print(f"  - 删除所有标签定义（共 {tags_count} 条）")
        print("未实际修改数据库。")
        conn.close()
        return

    # 执行删除
    try:
        link_deleted, tags_deleted = delete_all_tags(conn, dry_run=False, purge=args.purge)
        print("\n操作完成：")
        print(f"  - 已删除书籍标签关联: {link_deleted} 条")
        if args.purge:
            print(f"  - 已删除标签定义: {tags_deleted} 条")
        else:
            print("  - 标签定义表 tags 未改动。")
    except Exception as e:
        print(f"操作失败: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()