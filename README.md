# ctcsfg-tec-02
ECS上でPythonアプリケーションをGitHub Actionsから自動デプロイする検証用リポジトリです。

## エンドポイント

- `GET /health`: ALBヘルスチェック用（`{"status":"ok"}`）
- `GET /`: アプリケーション応答（`{"message":"hello"}`）

## ローカル実行

```powershell
python -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## コンテナ実行

```powershell
docker build -t ctcsfg-tec-02 .
docker run --rm -p 8000:8000 ctcsfg-tec-02
```

CI/CDのAWS・GitHub設定は [docs/cicd/README.md](docs/cicd/README.md) を参照してください。