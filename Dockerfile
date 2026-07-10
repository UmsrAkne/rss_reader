# 軽量なPythonイメージ
FROM python:3.11-slim

# コンテナ内の作業ディレクトリ
WORKDIR /workspace

# 先に requirements.txt をコピーしてキャッシュを効かせる
COPY requirements.txt .

# 依存パッケージ
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードを丸ごとコピー
COPY . .

# ポート開放（API用）
EXPOSE 8000
