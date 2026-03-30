#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calibre 中文目录修复工具（重构作者文件夹结构）
---------------------------------------------
将Calibre库中位于根目录的书籍文件夹（如 "书名 (ID)"）移动到对应的作者文件夹下，
并重命名为正确的中文名称。内部文件重命名为 "作者 - 书名.扩展名"（可选）。

使用前请关闭Calibre，建议先备份metadata.db。
"""

import os
import sys
import sqlite3
import argparse
import re
import shutil

# ---------- 配置参数 ----------
DEFAULT_LIBRARY_PATH = "PPES"      # 默认库路径
DRY_RUN = False                     # 仅预览
RENAME_FILES = True                  # 重命名内部文件
BACKUP_DB = True                     # 备份数据库
CLEAN_EMPTY = False                  # 完成后清理空文件夹
MAX_NAME_LENGTH = 200                # 文件名最大长度
INVALID_CHARS = r'[\\/*?:"<>|]'      # 非法字符


def sanitize_filename(name):
    """清理文件名，替换非法字符，去除首尾空格"""
    if not name:
        return ""
    name = re.sub(INVALID_CHARS, '_', name)
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'_+', '_', name)
    if len(name) > MAX_NAME_LENGTH:
        name = name[:MAX_NAME_LENGTH].rsplit(' ', 1)[0]
    return name


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
    """创建SQLite连接并注册Calibre自定义函数（如title_sort）"""
    conn = sqlite3.connect(db_path)

    def title_sort(title):
        return title if title is not None else ""
    conn.create_function("title_sort", 1, title_sort)

    # 如有其他自定义函数报错，可在此添加
    return conn


def get_books_data(conn):
    """
    获取所有书籍信息：
        id, title, old_path, author_name, data_records
    data_records: (id, name, format)
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, path FROM books")
    books = cursor.fetchall()

    books_data = []
    for book_id, title, old_path in books:
        # 取第一个作者
        cursor.execute("""
            SELECT authors.name FROM authors
            JOIN books_authors_link ON authors.id = books_authors_link.author
            WHERE books_authors_link.book = ?
            LIMIT 1
        """, (book_id,))
        author_row = cursor.fetchone()
        author_name = author_row[0] if author_row else "未知作者"

        # 获取所有书籍文件
        cursor.execute("SELECT id, name, format FROM data WHERE book = ?", (book_id,))
        data_records = cursor.fetchall()

        books_data.append({
            'id': book_id,
            'title': title,
            'old_path': old_path,
            'author': author_name,
            'data': data_records
        })
    return books_data


def generate_author_folder_name(author):
    """生成作者文件夹名（清理非法字符）"""
    return sanitize_filename(author)


def generate_new_book_folder_name(book):
    """生成新的书籍文件夹名：书名 (ID)"""
    title = book['title']
    book_id = book['id']
    base = f"{title} ({book_id})"
    return sanitize_filename(base)


def generate_new_filename(book, ext):
    """生成新的内部文件名：作者 - 书名.扩展名（若作者为未知作者则只用书名）"""
    if book['author'] and book['author'] != "未知作者":
        base = f"{book['author']} - {book['title']}"
    else:
        base = book['title']
    return sanitize_filename(f"{base}.{ext.lstrip('.')}")


def ensure_unique_path(base_dir, target_path):
    """如果路径已存在，添加数字后缀直到唯一"""
    original = target_path
    counter = 1
    while os.path.exists(target_path):
        base, ext = os.path.splitext(original)
        target_path = f"{base}_{counter}{ext}"
        counter += 1
    return target_path


def process_book(calibre_path, book, dry_run=False, rename_files=False):
    """
    处理单本书：
        - 确保书籍位于正确的作者文件夹下
        - 更新数据库中的 path 字段
        - 可选重命名内部文件
    返回 True 表示有修改，False 表示无变化或出错
    """
    book_id = book['id']
    old_path = book['old_path']          # 例如 "西洋哲学史 (107)" 或 "冯友兰/西洋哲学史 (107)"
    author = book['author']

    # 生成规范化的作者文件夹名和书籍文件夹名
    author_folder = generate_author_folder_name(author)
    new_book_folder = generate_new_book_folder_name(book)

    # 目标完整路径：calibre_path/author_folder/new_book_folder
    target_full = os.path.join(calibre_path, author_folder, new_book_folder)
    target_full = ensure_unique_path(calibre_path, target_full)  # 避免重名（理论上ID唯一，但预防）
    target_path = os.path.relpath(target_full, calibre_path)     # 相对路径用于数据库

    old_full = os.path.join(calibre_path, old_path)

    # 判断是否需要移动/重命名
    if old_full == target_full:
        print(f"书ID {book_id}: 位置和名称已正确，跳过。")
        return False

    print(f"书ID {book_id}: 准备处理书籍")
    print(f"  当前: {old_path}")
    print(f"  目标: {target_path}")

    if dry_run:
        return True

    # 实际执行
    try:
        # 确保目标作者目录存在
        author_dir = os.path.join(calibre_path, author_folder)
        if not os.path.exists(author_dir):
            os.makedirs(author_dir)
            print(f"  创建作者目录: {author_folder}")

        # 移动/重命名书籍文件夹
        if not os.path.exists(old_full):
            print(f"  错误: 源文件夹不存在 {old_full}")
            return False
        shutil.move(old_full, target_full)   # 使用shutil.move支持跨目录移动
        print(f"  文件夹移动/重命名成功")

        # 更新数据库
        conn = create_calibre_connection(get_calibre_db_path(calibre_path))
        conn.isolation_level = None
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("UPDATE books SET path = ? WHERE id = ?", (target_path, book_id))

        # 重命名内部文件（如果启用）
        if rename_files:
            for data_id, old_filename, fmt in book['data']:
                ext = fmt.lower() if fmt else os.path.splitext(old_filename)[1].lstrip('.')
                actual_old_filename = f"{old_filename}.{ext}"
                new_full_filename = generate_new_filename(book, ext)

                old_file_full = os.path.join(target_full, actual_old_filename)
                new_file_full = os.path.join(target_full, new_full_filename)
                new_file_full = ensure_unique_path(target_full, new_file_full)
                new_filename_with_ext = os.path.basename(new_file_full)

                if actual_old_filename == new_filename_with_ext:
                    continue

                print(f"    重命名文件: {actual_old_filename} -> {new_filename_with_ext}")
                if os.path.exists(old_file_full):
                    os.rename(old_file_full, new_file_full)
                    new_name_without_ext = os.path.splitext(new_filename_with_ext)[0]
                    cursor.execute("UPDATE data SET name = ? WHERE id = ?", (new_name_without_ext, data_id))
                else:
                    print(f"    警告: 文件不存在 {old_file_full}")

        conn.commit()
        conn.close()
        print(f"  数据库更新完成")
        return True

    except Exception as e:
        print(f"  处理失败: {e}")
        try:
            conn.rollback()
        except:
            pass
        # 如果已移动但失败，尝试将文件夹移回原处
        if os.path.exists(target_full) and not os.path.exists(old_full):
            try:
                shutil.move(target_full, old_full)
                print(f"  已恢复文件夹到 {old_path}")
            except:
                print("  警告: 无法恢复文件夹，请手动处理")
        return False


def is_empty_dir(dir_path):
    """检查目录是否为空（忽略隐藏文件）"""
    try:
        with os.scandir(dir_path) as it:
            for entry in it:
                if not entry.name.startswith('.'):
                    return False
            return True
    except PermissionError:
        print(f"权限不足，跳过: {dir_path}")
        return False


def remove_empty_folders(root_path, dry_run=False):
    """递归删除空文件夹"""
    removed = 0
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        if os.path.basename(dirpath).startswith('.'):
            continue
        if is_empty_dir(dirpath):
            if dry_run:
                print(f"[预览] 将删除空文件夹: {dirpath}")
            else:
                try:
                    os.rmdir(dirpath)
                    print(f"已删除空文件夹: {dirpath}")
                    removed += 1
                except OSError as e:
                    print(f"删除失败 {dirpath}: {e}")
    return removed


def main():
    parser = argparse.ArgumentParser(description="修复Calibre库的目录结构：将书籍移动到作者文件夹下")
    parser.add_argument('library', nargs='?', default=DEFAULT_LIBRARY_PATH,
                        help='Calibre库路径（默认为PPES）')
    parser.add_argument('--dry-run', action='store_true', default=DRY_RUN,
                        help='仅预览，不实际修改')
    parser.add_argument('--rename-files', action='store_true', default=RENAME_FILES,
                        help='同时重命名内部书籍文件（默认启用）')
    parser.add_argument('--no-rename-files', dest='rename_files', action='store_false',
                        help='不重命名内部文件，只移动/重命名文件夹')
    parser.add_argument('--no-backup', dest='backup', action='store_false', default=BACKUP_DB,
                        help='不备份数据库')
    parser.add_argument('--clean-empty', action='store_true', default=CLEAN_EMPTY,
                        help='完成后删除所有空文件夹')
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
    books = get_books_data(conn)
    conn.close()
    print(f"共找到 {len(books)} 本书\n")

    success_count = 0
    for book in books:
        if process_book(library_path, book,
                        dry_run=args.dry_run,
                        rename_files=args.rename_files):
            success_count += 1
        print("-" * 40)

    print(f"重命名处理完成。成功修改 {success_count} 本书。")

    if args.clean_empty and not args.dry_run:
        print("\n开始清理空文件夹...")
        removed = remove_empty_folders(library_path, dry_run=False)
        print(f"空文件夹清理完成，共删除 {removed} 个。")
    elif args.clean_empty and args.dry_run:
        print("\n预览空文件夹清理...")
        removed = remove_empty_folders(library_path, dry_run=True)
        print(f"预览完成，发现 {removed} 个空文件夹。")

    if args.dry_run:
        print("\n这是预览模式，未实际修改。如需实际修改，去掉 --dry-run 参数。")


if __name__ == '__main__':
    main()