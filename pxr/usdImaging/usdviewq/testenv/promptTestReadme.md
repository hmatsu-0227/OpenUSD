# USDViewer HTTP Server Prompt Endpoint Test Scripts

これらのスクリプトは、USDViewer HTTPサーバーの新しい `/prompt` エンドポイントをテストするために作成されました。

## 前提条件

- Python 3.x
- `requests` ライブラリ (`pip install requests`)
- USDViewerがHTTPサーバー機能付きで起動している

## スクリプト一覧

### 1. `test_prompt_endpoint.py` - 自動テストスクリプト

包括的な自動テストを実行します。

**使用方法:**
```bash
# デフォルト（localhost:8080）でテスト
python test_prompt_endpoint.py

# カスタムサーバーURLでテスト
python test_prompt_endpoint.py http://localhost:8081
```

**テスト内容:**
- サーバー接続確認
- 基本的なメッセージ送信テスト
- 日本語・絵文字・長文などの様々なメッセージタイプ
- エラーケースのテスト（無効なJSON、必須パラメータなし）
- 結果サマリーの表示

### 2. `interactive_prompt_test.py` - インタラクティブテストスクリプト

対話的にメッセージを送信できます。

**使用方法:**
```bash
# デフォルト（localhost:8080）で起動
python interactive_prompt_test.py

# カスタムサーバーURLで起動
python interactive_prompt_test.py http://localhost:8081
```

**機能:**
- リアルタイムでメッセージを送信
- レスポンスの即座確認
- 手動での個別テスト

**コマンド:**
- `help` または `h` - ヘルプ表示
- `quit`, `exit`, `q` - 終了
- その他のテキスト - プロンプトメッセージとして送信

## USDViewerの起動方法

HTTPサーバー機能を有効にしてUSDViewerを起動してください：

```bash
# 環境変数でポートを指定（オプション）
set USDVIEW_HTTP_PORT=8080
set USDVIEW_HTTP_HOST=localhost

# USDViewerを起動
usdview your_file.usd
```

## テスト例

### 自動テスト実行例
```bash
PS D:\AISDK\20250908\OpenUSD> python test_prompt_endpoint.py
Using server URL: http://localhost:8080
🚀 Starting USDViewer Prompt Endpoint Test Suite
============================================================
🔍 Testing server connection...
✅ Server is running
   Status: ok
   Available endpoints: ['POST /move - Move a prim by updating its transform', 'POST /prompt - Process a prompt message']

🧪 Testing 10 different prompt messages...

📤 Sending prompt: Simple greeting
   Message: 'Hello, USDViewer!'
   Response Status: 200
   ✅ Success!
   Server Response: Hello, USDViewer!
   Full Message: Received prompt message: Hello, USDViewer!
...
```

### インタラクティブテスト実行例
```bash
PS D:\AISDK\20250908\OpenUSD> python interactive_prompt_test.py
🔧 Interactive USDViewer Prompt Endpoint Test
==================================================
Server URL: http://localhost:8080
✅ Server is accessible

You can now send prompt messages to the server.
Type 'quit' or 'exit' to stop, 'help' for commands.
--------------------------------------------------

📝 Enter prompt message: Hello, USDViewer!

📤 Sending: 'Hello, USDViewer!'
------------------------------
Status Code: 200
✅ Success!
Server Message: Received prompt message: Hello, USDViewer!
Response: Hello, USDViewer!

📝 Enter prompt message: quit
👋 Goodbye!
```

## トラブルシューティング

### よくあるエラー

1. **接続エラー**: USDViewerが起動していないか、HTTPサーバーが無効
   ```
   ❌ Could not connect to server at http://localhost:8080
   ```
   → USDViewerを起動してください

2. **タイムアウト**: リクエストが時間内に完了しない
   ```
   ❌ Request timed out
   ```
   → サーバーの負荷を確認してください

3. **400エラー**: 無効なリクエスト形式
   ```
   ❌ Error: 400
   Error Message: Missing required parameter: message
   ```
   → リクエスト形式を確認してください

## 期待される動作

正常に動作している場合、プロンプトエンドポイントは：
- 送信されたメッセージをそのまま返す
- 200ステータスコードで応答
- JSON形式でレスポンスを返す

将来的には、このエンドポイントにより高度な機能が追加される予定です。
