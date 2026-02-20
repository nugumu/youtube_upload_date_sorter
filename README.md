# YouTube 日付順検索ツール

YouTube Data API v3 を使って、検索結果を **アップロード日時が新しい順** で表示します。



## 事前準備（YouTube Data API キー）

### (1) API キーの取得
Google Cloud で YouTube Data API v3 を有効化し、APIキーを取得してください。

### (2) Python 環境効率
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
streamlit run main.py
```

ブラウザが開きます。上部の入力欄にAPIキーと検索ワードを入れて「検索」を押してください。

## 使い方・補足

### 検索条件（詳細）
入力欄の下にある「検索条件（詳細）」を開くと、次が指定できます（任意）：
- 取得件数（最大500）
- regionCode / relevanceLanguage
- safeSearch
- videoDuration / videoDefinition / videoType / eventType
- channelId（特定チャンネル内検索）
- publishedAfter / publishedBefore（RFC3339形式）

RFC3339例: `2024-01-01T00:00:00Z`
