# ベースイメージ
FROM python:3.11-slim
# 作業ディレクトリ
WORKDIR /app
# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*
# 依存関係のコピーとインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# アプリケーションのコピー
COPY . .
# ポート公開
EXPOSE 8000
# アプリケーションの起動
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
