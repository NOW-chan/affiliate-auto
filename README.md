# affiliate-auto

A8.net の案件 → はてなブログ記事（下書き）→ 人が公開 → Threads / X で告知、を自動で回す仕組み。
**人がやるのは「週1回の案件追記」と「毎朝の下書き確認→公開ボタン」だけ。**

---

## 前提（どこで動くか）

| 項目 | 内容 |
|---|---|
| 実行基盤 | **GitHub Actions**（GitHub が用意するクラウド上の Ubuntu。サーバ不要） |
| 起動 | cron スケジュール（記事生成：毎朝7時／SNS：1日4回／トークン更新：月1回） |
| 状態管理 | `cases.yaml`（Git にコミットして保存。DB不要） |
| 秘密情報 | GitHub Secrets |
| AI | Claude Code（`claude -p` の無人実行。Claude の有料プランのトークンで認証） |
| 言語 | Python 3.12 / Node.js 22 |

> リポジトリは **Private** を推奨（案件リストや戦略が丸見えになるため）。
> Private リポジトリは無料枠の実行時間に上限があります。この構成は1日数分程度なので、通常は収まります（最新の無料枠は GitHub の料金ページで確認してください）。

同じスクリプトは **自宅の Linux サーバや VPS の cron でもそのまま動きます**（後述）。

---

## 全体の流れ

```
[週1・手動] cases.yaml に案件を追記（status: todo）
      │
[毎朝7時] generate.yml
      │  Claude Code が記事HTMLを作成
      │  validate_article.py がルールを検証（落ちたら1回だけ自動修正）
      │  post_hatena.py が「下書き」で投稿 → status: hatena_draft
      ▼
[あなた] スマホで下書きを確認して「公開」  ← 承認はここだけ
      │
[1日4回] sns.yml
      │  check_published.py が公開を検知 → status: published
      │  Claude Code が告知文（sns.yaml）を作成
      │  post_sns.py が Threads（＋任意でX）に投稿 → status: sns_posted
      ▼
    完了
```

---

## セットアップ

### 1. GitHub にリポジトリを作る

```bash
cd affiliate-auto
git init && git add -A && git commit -m "init"
gh repo create affiliate-auto --private --source=. --push
```

### 2. はてなブログの準備

1. はてなブログ「設定」→「基本設定」→**編集モードを「見たままモード」**にする（HTMLがそのまま反映されるため）
2. 「設定」→「詳細設定」→「AtomPub」で **APIキー** と **ルートエンドポイント** を確認する
   - ルートエンドポイント `https://blog.hatena.ne.jp/<はてなID>/<ブログドメイン>/atom` の
     `<ブログドメイン>` 部分（例：`nowchan.hatenablog.com`）を `HATENA_BLOG_DOMAIN` に使う

### 3. Claude Code の認証トークン

自分のPCで `claude setup-token` を実行し、表示された `sk-ant-oat01-...` を
Secret `CLAUDE_CODE_OAUTH_TOKEN` に登録する（有効期限1年。Pro 以上のプランが必要）。
プランの利用枠を使うので追加料金はかからないが、チャットと同じ枠を消費する。

> API キー（従量課金）に切り替える場合は、ワークフローの
> `CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` を
> `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}` に置き換える（両方は登録しない）。

### 4. Threads API のトークン

（Meta の画面名は変わることがあります）

1. [Meta for Developers](https://developers.facebook.com/) でアプリを作成し、ユースケースに「Threads API へのアクセス」を選ぶ
2. 権限 `threads_basic` と `threads_content_publish` を追加する
3. 自分の Threads アカウントを**テスター**に追加し、Threads アプリ側で招待を承認する
4. ユーザートークンを発行し、**長期トークン（60日）**に交換する
5. 60日で失効するので、`refresh-threads-token.yml` が月1回自動で更新する
   - そのために、このリポジトリの Secrets に書き込める **fine-grained PAT** を作り、`GH_PAT` として登録する
     （権限：対象リポジトリのみ／Secrets: Read and write）

### 5. X（任意）

X API は従量課金で、**リンク付き投稿は1件あたりの料金が高くなります**。
初期設定ではリンクなしで投稿します（`X_INCLUDE_LINK=false`）。

1. X Developer Console でアプリを作り、クレジットを購入する（支出上限も設定する）
2. OAuth 1.0a のキーを4つ発行する（API Key / Secret、Access Token / Secret。権限は Read and Write）
3. リポジトリの **Variables** に `X_ENABLED=true` を設定する

### 6. Secrets / Variables を登録する

Settings → Secrets and variables → Actions

| 種類 | 名前 | 必須 |
|---|---|---|
| Secret | `CLAUDE_CODE_OAUTH_TOKEN` | ✅ |
| Secret | `HATENA_ID` | ✅ |
| Secret | `HATENA_BLOG_DOMAIN` | ✅ |
| Secret | `HATENA_API_KEY` | ✅ |
| Secret | `THREADS_ACCESS_TOKEN` | ✅ |
| Secret | `GH_PAT` | ✅（トークン自動更新用） |
| Secret | `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_SECRET` | X を使う場合 |
| Variable | `X_ENABLED` | X を使う場合 `true` |
| Variable | `X_INCLUDE_LINK` | 通常は設定しない（`false`） |

gh CLI でまとめて登録する例：

```bash
gh secret set CLAUDE_CODE_OAUTH_TOKEN
gh secret set HATENA_ID --body "nowchan"
gh secret set HATENA_BLOG_DOMAIN --body "nowchan.hatenablog.com"
gh secret set HATENA_API_KEY
gh secret set THREADS_ACCESS_TOKEN
gh secret set GH_PAT
```

### 7. 最初のテスト（dry-run）

1. `cases.yaml` のサンプルを、実際の案件1件に書き換えて push する
2. Actions → **generate-article** → Run workflow（`dry_run` にチェックを入れたまま）
3. 実行結果の **Artifacts** から記事HTMLをダウンロードし、中身を確認する
4. 問題なければ `dry_run` のチェックを外してもう一度実行 → はてなに下書きが入る
5. はてなで公開 → **sns-post** を `dry_run` ありで実行して文面を確認 → チェックを外して本番投稿

---

## 毎日の運用

| 頻度 | やること | 時間 |
|---|---|---|
| 週1回 | A8.net で提携した案件を `cases.yaml` に追記（`status: todo`） | 10分 |
| 毎朝 | はてなアプリで下書きを確認して公開（下のチェック3点） | 1〜2分/記事 |
| 週1回 | A8.net のレポートを見て、伸びた切り口を `cases.yaml` の `angle` に反映 | 10分 |

**公開前チェック（3点だけ）**
1. 冒頭に【PR】表記がある
2. 「使ってみた」のような、実際には体験していない記述がない
3. 料金や数字が公式サイトと合っている

---

## 出来栄えに納得がいかず、作り直したいとき

直したい範囲によって、書く場所が違います。

| 直したい範囲 | 書く場所 | 例 |
|---|---|---|
| **この記事だけ、今すぐ作り直したい** | Actions → **regenerate-article** → Run workflow の「修正指示」欄 | 「導入を3行に。比較表に解約方法の列を追加」 |
| **この案件では毎回こうしてほしい** | `cases.yaml` のその案件の `feedback:` | 「初心者向けに専門用語を使わない」 |
| **全部の記事でこうしてほしい** | `.claude/skills/write-article/SKILL.md`（書き方）か `CLAUDE.md`（絶対ルール・デザイン） | 「CTAボタンは緑」「1記事5,000字前後」 |

**regenerate-article の動き**

1. 案件ID（`cases.yaml` の `id`）と修正指示を入力して実行する
2. 既存の記事があればそれを土台に、なければ新しく作り直す
3. 修正指示は `articles/<id>/feedback.md` に履歴として残り、次に作り直すときも引き継がれる
4. 何を直したかは、実行結果ページの Summary に表示される
5. `dry_run` のチェックを外すと、はてなの**下書きを上書き**する（新しい下書きは増えない）
6. 公開済みの記事は自動では上書きしない（はてなで直接直す）

**修正指示のコツ**：「もっと良くして」ではなく、「どこを・どう」を具体的に書く。
例：「冒頭の悩みを、残業が多い会社員の視点に変える」「比較表の1列目を料金にする」「見出しを5個以内にする」

---

## ローカル／自宅サーバで動かす場合

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code
cp .env.example .env   # 値を入れる
set -a && . ./.env && set +a

ID=$(python scripts/cases.py next)
claude -p "CLAUDE.md と .claude/skills/write-article/SKILL.md を読み、手順に従って cases.yaml の id: $ID の記事を articles/$ID/ に作成。cases.yaml と scripts/ は編集しない。" \
  --allowedTools "Read,Write,Edit,Glob,Grep,WebSearch,WebFetch" --max-turns 40
python scripts/validate_article.py "$ID"
python scripts/post_hatena.py "$ID" --dry-run
```

cron に登録する場合は、上の処理を `run_generate.sh` にまとめて `0 7 * * *` で実行してください。

---

## ファイル構成

```
CLAUDE.md                       Claude Code が守るルール（PR表記・体験談禁止・CSSスコープ等）
.claude/skills/write-article/   記事の書き方
.claude/skills/write-sns-post/  SNS文面の書き方
cases.yaml                      案件リスト兼、状態管理
articles/<id>/                  article.html / meta.yaml / sns.yaml
scripts/cases.py                次の案件の選定・一覧
scripts/validate_article.py     ルール違反の機械チェック（禁止表現・PR表記・rel・CSSスコープ）
scripts/post_hatena.py          はてなに下書き投稿（AtomPub）
scripts/check_published.py      公開されたかを確認
scripts/post_sns.py             Threads / X に投稿（二重投稿防止つき）
scripts/refresh_threads_token.py Threads トークン更新
.github/workflows/              generate.yml / regenerate.yml / sns.yml / refresh-threads-token.yml
```

## status の意味

| status | 意味 | 次に動くもの |
|---|---|---|
| `todo` | 記事化待ち | generate.yml |
| `hatena_draft` | はてなに下書きあり | **あなたが公開** |
| `published` | 公開を検知した | sns.yml |
| `sns_posted` | 告知まで完了 | — |
| `hatena_missing` | はてな側で記事が消えた | 手動で確認 |

## よくあるトラブル

- **検証で落ちて止まった**：Actions のログに理由が出ます。禁止表現の誤検知なら `validate_article.py` の `FORBIDDEN` を調整してください。
- **はてなで HTTP 401**：`HATENA_ID` と `HATENA_API_KEY` を確認（パスワードではなく AtomPub の APIキー）。
- **Threads で認証エラー**：トークン切れの可能性があります。手動で再発行して `THREADS_ACCESS_TOKEN` を更新してください。
- **push が失敗する**：Settings → Actions → General → Workflow permissions を「Read and write」にしてください。
