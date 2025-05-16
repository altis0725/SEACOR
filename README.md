# SEACOR: Self-Evolving Autonomous Crew of Experts and Resources

## 概要
SEACORは、複数の専門家エージェント（Crew）が協調し、課題解決・自己進化を行うAIオーケストレーション基盤です。LLM（大規模言語モデル）を活用し、戦略設計・ゴール分解・プランニング・意思決定理論などの複雑な知的作業を自律的に実行・評価・改善します。

- **自己進化型**: 実行・評価・改善・記録のループで知識と戦略を自動進化
- **多層エージェント**: 戦略・実行・評価・記録など多様な役割のエージェントをYAMLで定義
- **Web UI/REST API**: チャット形式で自然言語による対話・指示が可能
- **Docker対応**: 環境依存なくすぐに起動

## ディレクトリ構成
```
seacor/
  ├── __main__.py         # FastAPIエントリーポイント
  ├── public/             # Web UI (index.html)
  ├── config/             # 設定ファイル（experts.yaml, tools.yaml, seacor-settings.yaml）
  ├── agents/             # エージェント生成ロジック
  ├── crews/              # Crew（専門家集団）ロジック
  ├── tools/              # LLM/ツール連携
  ├── utils/              # 各種ユーティリティ
Dockerfile, docker-compose.yml, requirements.txt
```

## 主なエージェント例（experts.yamlより抜粋）
- **strategy_architect**: 戦略設計・ゴール分解・プランニング・意思決定理論
- **ux_product_owner**: ユーザ要件分析・ビジネス価値評価
- **code_analyst**: コード分析・リファクタリング
- **security_expert**: セキュリティ設計・脆弱性診断
- **performance_optimizer**: パフォーマンスチューニング
- **architecture_designer**: システム設計・技術選定
- **testing_specialist**: テスト戦略・自動テスト設計
- **evaluation_manager**: KPI設計・品質評価
- **experiment_scientist**: 仮説検証・統計解析
- **knowledge_librarian**: ナレッジマネジメント

## セットアップ
### 1. 必要パッケージのインストール
```sh
pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env`ファイルに以下を記載（例）
```
MONICA_API_KEY=sk-xxxxxx
SEACOR_LOG_LEVEL=INFO
```

### 3. 起動方法
#### ローカル
```sh
uvicorn seacor.__main__:app --reload
```
#### Docker
```sh
docker-compose up --build
```

## Web UI
- ブラウザで [http://localhost:8000/](http://localhost:8000/) にアクセス
- チャット形式で自然言語による指示・対話が可能

## REST API
- `POST /api/chat`  
  - リクエスト: `{ "message": "あなたは何ができますか" }`
  - レスポンス: `{ "reply": "...AIの回答..." }`
- `GET /health`  
  - ヘルスチェック

## カスタマイズ例
- `seacor/config/experts.yaml` でエージェントの専門分野やゴールを編集可能
- `seacor/config/tools.yaml` で独自ツールを追加可能
- `seacor/config/seacor-settings.yaml` でLLMや学習パラメータを調整可能

## ライセンス
MIT

---

> 最新のコード・詳細は [GitHubリポジトリ](https://github.com/altis0725/SEACOR) を参照してください。 