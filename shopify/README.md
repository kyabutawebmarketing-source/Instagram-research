# 冷感接触ドッグウェア 特設LP — Shopify テンプレート設置ガイド

hakutaka × 加賀美健 コラボLPを、Shopifyの **ページテンプレート** として設置し、
管理画面のページ編集から「テーマテンプレート」で直接選べるようにするためのファイル一式です。

元データ（プレビュー用の単体HTML）: リポジトリ直下の `dogwear-cooltouch-lp.html`

---

## 含まれるファイル

| ファイル | 役割 |
|---|---|
| `sections/dogwear-cooltouch-lp.liquid` | LP本体（セクション）。Online Store 2.0 用 |
| `templates/page.dogwear-cooltouch.json` | 上記セクションを呼び出すページテンプレート（**推奨**） |
| `templates/page.dogwear-cooltouch-simple.liquid` | 1ファイル完結のページテンプレート（**簡易版／代替**） |

> どちらか一方の方法を選んでください。**推奨はA（セクション＋JSON）** です。

---

## 方法A（推奨）: セクション ＋ JSONテンプレート

テーマエディタで表示のオン/オフや複製ができ、テンプレート選択にも対応します。

1. Shopify管理画面 → **オンラインストア → テーマ → （対象テーマの）… → コードを編集**
2. `sections` フォルダで **新しいセクションを追加** → 名前を `dogwear-cooltouch-lp` にして作成 →
   中身を **すべて削除**し、`sections/dogwear-cooltouch-lp.liquid` の内容を貼り付けて保存
3. `templates` フォルダで **新しいテンプレートを追加** →
   - 種類: **page**
   - 形式: **json**
   - 名前: `dogwear-cooltouch`
   作成後、中身を `templates/page.dogwear-cooltouch.json` の内容に置き換えて保存
4. 管理画面 → **販売チャネル → ページ** で対象ページを開く（新規作成でも可）
5. 右側 **「テーマテンプレート」** で **`dogwear-cooltouch`** を選択して保存

> ファイルをそのままアップロードできるテーマ（Gitやテーマkit連携）の場合は、
> `sections/` と `templates/` の各ファイルを同じパスに配置するだけでOKです。

---

## 方法B（簡易）: 1ファイルのLiquidテンプレート

セクション分割が不要で、1ファイルだけで完結させたい場合。

1. コードを編集 → `templates` フォルダで **新しいテンプレートを追加** →
   - 種類: **page**
   - 形式: **liquid**
   - 名前: `dogwear-cooltouch-simple`
2. 作成された `templates/page.dogwear-cooltouch-simple.liquid` の中身を、
   本リポジトリの同名ファイルの内容に置き換えて保存
3. 対象ページの **「テーマテンプレート」** で **`dogwear-cooltouch-simple`** を選択して保存

---

## 方法C（最も手軽）: ページのHTMLに直接貼り付け

テンプレートを作らず、既存の「デフォルト」ページに貼るだけの方法です。

1. 管理画面 → ページ → 対象ページ → 本文エディタ右上の **`< >`（HTMLを表示）** をクリック
2. `dogwear-cooltouch-lp.html`（リポジトリ直下）の内容を丸ごと貼り付けて保存

---

## メモ

- LPは `#dog-lp` 配下に完全に閉じたCSS/JSで、テーマ既存のスタイルと干渉しにくい構成です。
- Liquidの誤解釈を防ぐため、Liquidファイル内ではLP全体を `{% raw %}` … `{% endraw %}` で囲っています
  （LP内に `{{ }}` / `{% %}` は含まれていないため、そのままでも動作しますが安全策として付与）。
- 商品画像・商品リンク・キービジュアルは `hakutaka-shop.com` / Shopify CDN を直接参照しています。
- テーマによってはページ本文の最大幅が制限されることがあります。全幅で表示したい場合は、
  方法A/Bのテンプレート（本文カラムの制約を受けにくい）を推奨します。
