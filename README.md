# Instagram 競合・インフルエンサー分析ツール

Instagram の競合アカウントやジャンル別インフルエンサーを分析し、エンゲージメント率・ハッシュタグ傾向・投稿パターンを可視化。Claude AI がコンテンツ戦略を提案するHTMLレポートを生成します。

## セットアップ

```bash
pip install -r requirements.txt
cp .env.example .env
# .env にAPIキーを記入
```

## 使い方

### 競合分析: デモモード（APIキー不要）

```bash
python main.py demo
```

モックデータで `report.html` を生成します。AI戦略提案も含める場合は `ANTHROPIC_API_KEY` を設定してください。

### 競合分析: 実際の競合アカウントを分析

```bash
python main.py analyze \
  --username competitor1 \
  --username competitor2 \
  --token YOUR_INSTAGRAM_ACCESS_TOKEN \
  --user-id YOUR_USER_ID
```

対応カテゴリ（`--genre`/`-g` で指定、以下のいずれか固定）：

- 美容・コスメ
- ファッション
- 子育て・ベビー
- ダイエット・フィットネス
- 旅行
- プレゼント
- ペット

### インフルエンサー分析: デモモード（APIキー不要）

```bash
python main.py influencer-demo --genre "ダイエット・フィットネス"
```

`influencer_report.html` を生成します。

### インフルエンサー分析: カテゴリ指定で実データを分析（Apify連携）

カテゴリ別のインフルエンサー検索・フォロワー数・投稿データはInstagram公式APIでは取得できないため、[Apify](https://apify.com/) のInstagramスクレイパーを利用します。`APIFY_API_TOKEN` を設定してください。

```bash
python main.py influencer --genre "美容・コスメ" --limit 10
# 特定ユーザーを直接指定する場合
python main.py influencer --genre "美容・コスメ" --username someuser --username otheruser
```

取得・算出される項目：

- フォロワー数 / フォロワー月別推移（過去3ヶ月）
- エンゲージメント率 / エンゲージメント推移（過去3ヶ月）
- PR率（過去3ヶ月、キャプション内の `#PR` `#ad` `#sponsored` 等のマーカーから判定）
- カテゴリジャンル（bio・ハッシュタグから推定分類）
- インフルエンサー属性デモグラ・フォロワー属性デモグラ（※公開Instagramデータには存在しないため**推定値**として表示）

フォロワー数推移は実行ごとに `data/influencer_snapshots.json` へスナップショットを蓄積し、3ヶ月分の履歴がまだ無い場合は現在値からの推定値で不足分を補完します（レポート上に「※一部推定値」と明示）。

## ファイル構成

```
├── main.py                    # CLIエントリーポイント
├── requirements.txt
├── .env.example
├── src/
│   ├── instagram_client.py    # Instagram Graph API クライアント
│   ├── apify_client.py        # Apify Instagramスクレイパー連携
│   ├── analyzer.py            # エンゲージメント・ハッシュタグ分析
│   ├── influencer_analyzer.py # PR率・ジャンル分類・トレンド・デモグラ推定
│   ├── snapshot_store.py      # フォロワー数等の履歴スナップショット保存
│   ├── ai_strategy.py         # Claude AI による戦略生成
│   └── report_generator.py    # HTMLレポート生成
└── templates/
    ├── report.html            # 競合分析レポート
    └── influencer_report.html # インフルエンサー分析レポート
```

## レポートの内容

### 競合分析レポート

- アカウント概要カード（フォロワー・ENG率）
- エンゲージメント率グラフ
- 全アカウント比較テーブル
- 人気投稿 Top 5
- ハッシュタグ使用頻度ランキング
- 曜日・時間帯別投稿パターン
- Claude AI によるコンテンツ戦略提案

### インフルエンサー分析レポート

- フォロワー数・フォロワー月別推移
- エンゲージメント率・推移
- PR率
- カテゴリジャンル
- インフルエンサー / フォロワー属性デモグラ（推定値）
