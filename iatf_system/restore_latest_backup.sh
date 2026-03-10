#!/bin/bash

# データベースの設定
DB_NAME="myapp_development"
DB_USER="postgres"
DB_PASSWORD="password"
DB_HOST="db"
BACKUP_DIR="/myapp/db/backup"

# データベースが存在するかどうかを確認
if PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    echo "データベース $DB_NAME は既に存在します。"
else
    # データベースが存在しない場合、作成
    echo "データベース $DB_NAME が存在しません。作成します。"
    PGPASSWORD=$DB_PASSWORD psql -U $DB_USER -h $DB_HOST -c "CREATE DATABASE $DB_NAME"
fi

# 最新のバックアップファイルを取得
BACKUP_FILE=$(ls $BACKUP_DIR/backup_*.sql | sort -r | head -n 1)

# バックアップファイルが存在するか確認
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found!"
  exit 1
fi

# データベースをリストア（クリーンオプション付き）
PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -c -1 $BACKUP_FILE

# エラーが発生した場合、クリーンオプションなしでリトライ
if [[ $? -ne 0 ]]; then
  echo "Error restoring database with clean option. Retrying without clean option..."
  PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -1 $BACKUP_FILE
  if [[ $? -ne 0 ]]; then
    echo "Error restoring database!"
    exit 1
  fi
fi

echo "Database restored successfully from $BACKUP_FILE!"

