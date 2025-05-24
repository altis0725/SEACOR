# SEACOR: FastAPI × crewAI × MonicaAI (OpenAI互換) 日本語AIシステム

## 概要

SEACORは、FastAPI・crewAI・MonicaAI(OpenAI互換API)を組み合わせた、  
**日本語対応・自己進化型AIエージェントシステム**です。  
YAMLでエージェント・タスク・クルーを柔軟に定義し、  
Web UI/REST API経由でOpenAI互換のチャット体験を提供します。

---

## 特徴

- **OpenAI互換API**（/v1/chat/completions）でMonicaAIを利用
- **日本語YAML設定**＆日本語Web UI
- **自己進化・自動フィードバック**（crewAIクルー構成）
- **Docker/Docker Compose対応**で簡単デプロイ
- **ログ・進化履歴・自動バックアップ**機能

---

## ディレクトリ構成

```
.
├── main.py                # FastAPIエントリーポイント
├── requirements.txt       # Python依存パッケージ
├── Dockerfile             # Dockerビルド定義
├── docker-compose.yaml    # Docker Compose定義
├── public/                # Web UI（index.html等）
├── config/                # YAML設定（agents, tasks, crews, tools）
│   ├── agents/
│   ├── tasks/
│   ├── crews/
│   └── tools.yaml
├── crews/                 # crewAIクルー実装
├── core/                  # エージェント生成・進化・バリデーション等
├── tools/                 # MonicaAI LLMツール実装
├── utils/                 # ユーティリティ（YAML再エンコード等）
├── logs/                  # 実行ログ・進化履歴
└── .env                   # 環境変数（APIキー等、手動作成）
```

---

## セットアップ手順

### 1. .envファイル作成

プロジェクトルートに`.env`を作成し、MonicaAIのAPIキー等を記載します。

```env
MONICA_API_KEY=sk-xxxxxxx
OPENAI_API_BASE=https://openapi.monica.im/v1
SEACOR_LOG_LEVEL=INFO
```

### 2. Dockerビルド＆起動

```sh
docker-compose up --build
```

- Web UI: [http://localhost:8000/](http://localhost:8000/)
- OpenAI互換API: `POST /v1/chat/completions`

---

## 主要API

### OpenAI互換チャットAPI

- `POST /v1/chat/completions`
  - body例:
    ```json
    {
      "model": "gpt-4o-mini",
      "messages": [
        {"role": "system", "content": "あなたは有能なAIアシスタントです。"},
        {"role": "user", "content": "日本語で自己紹介して"}
      ]
    }
    ```
  - レスポンス: OpenAI互換

### ヘルスチェック

- `GET /health` → `{ "status": "ok" }`

---

## 設定ファイル例

### config/tools.yaml

```yaml
monica_llm:
  type: llm
  provider: monicaai
  description: MonicaAI LLM（大規模言語モデル）APIツール
  api_key_env: MONICA_API_KEY
  endpoint: https://openapi.monica.im/v1/chat/completions
  model: gpt-4o-mini
  temperature: 0.7
  max_tokens: 2000 
```

### config/agents/main_agents.yaml

```yaml
main_agent:
  allow_delegation: false
  goal: ユーザーのプロンプトに対して最適な回答を生成する
  name: MainAgent
  role: メイン
  tools:
    - monica_llm
  verbose: true
# ...他エージェントも同様
```

### config/tasks/main_tasks.yaml

```yaml
main_task:
  description: ユーザーの質問に対して最適な回答を生成する
  agent: main_agent
  expected_output: 明確で実用的な回答
  human_input: false
# ...他タスクも同様
```

### config/crews/main_crew.yaml

```yaml
MetaCrew:
  name: main_crew
  description: メインの業務遂行クルー。main_agentとfeedback_agentで構成
  agents:
    - main_agent
    - feedback_agent
  tasks:
    - main_task
    - feedback_task
    - revise_task
  process: sequential
  manager_agent: main_agent
  feedback_agent: feedback_agent
  output_log_file: logs/meta_crew.json
  memory:
    type: file
    path: memory/main_crew.json
  kickoff_async: true
  verbose: true
```

---

## Web UI

- `public/index.html`は日本語対応のシンプルなチャットUI
- Tailwind CSS＋Noto Sans JPで美しい日本語表示
- 入力→API呼び出し→AI応答を即時表示

---

## ログ・進化履歴

- `logs/`配下に各クルーの出力・進化案・エラー等を自動保存
- YAMLの日本語は`ensure_ascii=False`で再エンコードし、可読性を維持

---

## よくあるトラブル・運用ノウハウ

- **静的ファイルが見つからない**  
  → `public/`ディレクトリがルート直下にあるか確認
- **APIキーが反映されない**  
  → `.env`の内容・docker-composeの`env_file`指定を確認
- **YAMLの日本語がエスケープされる**  
  → `utils/yaml_loader.py`の再エンコード関数で自動修正
- **crewAIツール引数エラー**  
  → `tools/monica_llm.py`でdict→str変換のワークアラウンド実装済み

---

## ライセンス

本リポジトリはMITライセンスです。

---

## 開発・カスタマイズ

- crewAI/MonicaAI/タスクフローのカスタマイズは`config/`配下YAML編集で柔軟に可能
- エージェント・タスク・クルーの追加はYAML追記のみでOK
- 詳細な拡張は`core/`や`tools/`のPythonコードを編集

---

## コントリビューション歓迎

- Issue・PR・質問は日本語でお気軽にどうぞ！ 