import os
import shutil
import datetime
import argparse
import logging

BACKUP_ROOT = "backups"
CONFIG_DIRS = [
    ("config/agents", "agents"),
    ("config/crews", "crews"),
    ("config/tasks", "tasks"),
]

def backup_configs():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(BACKUP_ROOT, timestamp)
    os.makedirs(backup_dir, exist_ok=True)
    for src, name in CONFIG_DIRS:
        dst = os.path.join(backup_dir, name)
        shutil.copytree(src, dst)
    logging.info(f"バックアップ完了: {backup_dir}")
    return backup_dir

def rollback_configs(backup_dir):
    if not os.path.isdir(backup_dir):
        logging.error(f"指定したバックアップディレクトリが存在しません: {backup_dir}")
        return
    for _, name in CONFIG_DIRS:
        src = os.path.join(backup_dir, name)
        dst = os.path.join("config", name)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    logging.info(f"ロールバック完了: {backup_dir}")

def list_backups():
    if not os.path.isdir(BACKUP_ROOT):
        logging.error("バックアップが存在しません。")
        return
    for d in sorted(os.listdir(BACKUP_ROOT)):
        logging.info(d)

def main():
    parser = argparse.ArgumentParser(description="YAMLバックアップ・ロールバックスクリプト")
    parser.add_argument("action", choices=["backup", "rollback", "list"], help="操作種別: backup, rollback, list")
    parser.add_argument("--to", help="ロールバック先のバックアップディレクトリ名（例: 20240525_153000）")
    args = parser.parse_args()
    if args.action == "backup":
        backup_configs()
    elif args.action == "rollback":
        if not args.to:
            logging.error("--toでロールバック先ディレクトリ名を指定してください")
            return
        rollback_configs(os.path.join(BACKUP_ROOT, args.to))
    elif args.action == "list":
        list_backups()

if __name__ == "__main__":
    main() 