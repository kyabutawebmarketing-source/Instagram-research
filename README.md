# Instagram 競合分析ツール

Instagram の競合アカウントを分析し、エンゲージメント率・ハッシュタグ傾向・投稿パターンを可視化。Claude AI がコンテンツ戦略を提案するHTMLレポートを生成します。

## セットアップ

```bash
pip install -r requirements.txt
cp .env.example .env
# .env にAPIキーを記入
```

## 使い方

### デモモード（APIキー不要）

```bash
python main.py demo
```

モックデータで `report.html` を生成します。AI戦略提案も含める場合は `ANTHROPIC_API_KEY` を設定してください。

### 実際の競合アカウントを分析

```bash
python main.py analyze \
  --username competitor1 \
  --username competitor2 \
  --token YOUR_INSTAGRAM_ACCESS_TOKEN \
  --user-id YOUR_USER_ID
```

## ファイル構成

```
├── main.py                  # CLIエントリーポイント
├── requirements.txt
├── .env.example
├── src/
│   ├── instagram_client.py  # Instagram Graph API クライアント
│   ├── analyzer.py          # エンゲージメント・ハッシュタグ分析
│   ├── ai_strategy.py       # Claude AI による戦略生成
│   └── report_generator.py  # HTMLレポート生成
└── templates/
    └── report.html          # Jinja2 テンプレート
```

## レポートの内容

- アカウント概要カード（フォロワー・ENG率）
- エンゲージメント率グラフ
- 全アカウント比較テーブル
- 人気投稿 Top 5
- ハッシュタグ使用頻度ランキング
- 曜日・時間帯別投稿パターン
- Claude AI によるコンテンツ戦略提案
