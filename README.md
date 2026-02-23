# YouTube 日付順検索ツール

YouTube Data API v3 を使って、検索結果を **アップロード日時が新しい順** で表示します。



## 事前準備

### (1) API キーの取得
Google Cloud で YouTube Data API v3 を有効化し、APIキーを取得してください。

### (2) Python 環境構築
このツールのコードは Python で書かれており、動かすには Python が必要です。


## 動かし方（Mac / Windows 共通）

### (1) ZIP を展開
このリポジトリ（ZIP）を任意の場所に展開して、コンソールから当該フォルダに移動します。

```bash
cd youtube_upload_date_sorter
```

### (2) 仮想環境を作る（必須ではないが推奨）
#### Mac / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows（PowerShell）
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### (3) 必要なツールをインストール
```bash
pip install -r requirements.txt
```

### (4) 起動
```bash
streamlit run app.py
```

ブラウザが開きます。上部の入力欄にAPIキーと検索ワードを入れて「検索」を押してください。

## 使い方・補足

### 検索結果表示
- 投稿日時は **日本時間（JST）** で表示します
- 各動画の **再生数（viewCount）** を表示します

### 検索条件（詳細）
入力欄の下にある「検索条件（詳細）」を開くと、次が指定できます（任意）：
- 取得件数（最大500）
- regionCode / relevanceLanguage
- safeSearch
- videoDuration / videoDefinition / videoType / eventType
- channelId（特定チャンネル内検索）
- 再生数フィルタ（下限 / 上限）
- 期間指定（開始 / 終了、日本時間/JST）

※ 再生数フィルタは YouTube Data API 側で直接絞り込めないため、検索結果（候補）取得後に videos.list で再生数を取ってアプリ側でフィルタします。
