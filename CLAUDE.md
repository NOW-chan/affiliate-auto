# affiliate-auto — Claude Code 向けプロジェクトルール

はてなブログ（nowchan）のアフィリエイト記事を作り、SNSで告知するための自動化リポジトリ。
Claude Code は GitHub Actions 上で `claude -p`（無人実行）として呼ばれる。

## 役割分担

- **Claude Code がやること**：記事HTMLの作成（`articles/<id>/article.html` と `meta.yaml`）、SNS文面の作成（`articles/<id>/sns.yaml`）
- **Python スクリプトがやること**：案件の選定、検証、はてなへの投稿、SNSへの投稿、`cases.yaml` の状態更新
- **Claude Code は `cases.yaml` と `scripts/` を絶対に編集しない**（状態管理を壊さないため）

## 絶対ルール（違反すると検証で落ちる）

1. **PR表記**：記事の最初の要素として、必ず次の1行を入れる
   `<p class="nowc-pr">【PR】本記事はアフィリエイト広告を利用しています。</p>`
2. **体験談の捏造禁止**：筆者は紹介サービスを使っていない。「使ってみた」「実際に使って」「試してみた」「愛用」「効果を実感」など、一人称の利用体験は一切書かない。比較・解説型で書く。
   - 口コミを使うなら「公式サイトに掲載されている声によると」のように出典を明記して要約する（創作しない）
3. **事実確認**：料金・キャンペーン・数値は WebFetch で公式サイトを確認し、本文に「（20XX年X月X日時点・公式サイトより）」と確認日を入れる。確認できない数値は書かない。
4. **誇大表現の禁止**：「絶対」「必ず稼げる」「100%」「業界No.1（根拠なし）」「誰でも簡単に」などは使わない。
5. **薬機法**：育毛・美容・健康系では「髪が生える」「発毛」「治る」「〜が改善する」などの効果効能を書かない。医薬品・医薬部外品・化粧品の区分を確認し、公式表記の範囲で表現する。
6. **アフィリエイトリンク**：必ず `cases.yaml` の `link` をそのまま使い、
   `<a href="..." target="_blank" rel="sponsored nofollow noopener">` とする。

## HTML の書き方

- 全体を `<div class="nowc-article">` で包む
- `<style>` 内のセレクタは **すべて `.nowc-article` から始める**（はてなブログのテーマCSSと衝突させない）
  - 例：`.nowc-article h2 { ... }`、`.nowc-article .cta { ... }`
  - `@media` の中も同様。`@keyframes` 名は `nowc-` で始める
- 既存パターン：スコープ付きCSS、スティッキーサイドバー（PC幅のみ）、スクロールアニメーション（IntersectionObserver）
- JavaScript は `<script>` 内で即時関数にし、`document.querySelector('.nowc-article')` の範囲内だけを操作する
- 画像は使わない（著作権リスク回避）。図解はCSSや表で表現する
- `<html>` `<head>` `<body>` は書かない（はてなの本文に貼る断片として作る）

## 著者プロフィール（記事末尾に必ず入れる）

- 名前：NOW
- 役職：フリーランス
- 自己紹介：「フリーランスとして活動しながら、自分の自由時間をいかに作るか模索中。仕事の効率化と自分時間を両立するためのヒントを発信しています。」

## 出力ファイル

```
articles/<id>/article.html   # 本文HTML（上記ルールに従う）
articles/<id>/meta.yaml      # title / description / categories
articles/<id>/sns.yaml       # SNS文面（write-sns-post スキルで作る）
```
