# USDViewer HTTP Request Server

USDViewer用のHTTPリクエストサーバー機能です。この機能により、外部アプリケーションからHTTPリクエストを送信して、USDViewerで現在読み込まれているUSDファイルを操作できます。

## 機能概要

- **Move操作**: SdfPathで指定されたPrimの位置と回転を更新
- **マルチスレッド対応**: HTTPサーバーは別スレッドで動作し、USDViewerの操作を阻害しません
- **リアルタイム更新**: 変更は即座にUSDViewerの表示に反映されます

## 使用方法

### 1. USDViewerの起動

通常通りUSDViewerを起動します：

```bash
usdview your_file.usd
```

HTTPサーバーは自動的に開始され、以下のメッセージが表示されます：

```
USDViewer HTTP Request Server started on http://localhost:8080
Available endpoints:
  GET  / - Server status
  POST /move - Move a prim
```

### 2. サーバー設定のカスタマイズ

環境変数でサーバーの設定を変更できます：

```bash
# ポート番号を変更
export USDVIEW_HTTP_PORT=9090

# ホストアドレスを変更  
export USDVIEW_HTTP_HOST=0.0.0.0

usdview your_file.usd
```

### 3. HTTPリクエストの送信

#### サーバーステータスの確認

```bash
curl http://localhost:8080/
```

#### Move操作（全パラメータ指定）

```bash
curl -X POST http://localhost:8080/move \
  -H "Content-Type: application/json" \
  -d '{
    "sdfPath": "/World/Cube",
    "x": 5.0,
    "y": 0.0,
    "z": 2.0,
    "rotateZ": 45.0
  }'
```

#### Move操作（部分的な更新）

```bash
# X座標のみ変更（他の値は現在値を維持）
curl -X POST http://localhost:8080/move \
  -H "Content-Type: application/json" \
  -d '{
    "sdfPath": "/World/Cube",
    "x": 10.0
  }'

# 回転のみ変更
curl -X POST http://localhost:8080/move \
  -H "Content-Type: application/json" \
  -d '{
    "sdfPath": "/World/Cube",
    "rotateZ": 90.0
  }'
```

## API リファレンス

### GET /

サーバーのステータスと利用可能なエンドポイントを返します。

**レスポンス例:**
```json
{
  "status": "ok",
  "message": "USDViewer HTTP Request Server is running",
  "available_endpoints": [
    "POST /move - Move a prim by updating its transform"
  ]
}
```

### POST /move

指定されたPrimの位置と回転を更新します。

**リクエストパラメータ:**
- `sdfPath` (string, 必須): 操作対象のPrimのSdfPath（例: "/World/Cube"）
- `x` (float, オプション): X座標（省略時は現在値を維持）
- `y` (float, オプション): Y座標（省略時は現在値を維持）
- `z` (float, オプション): Z座標（省略時は現在値を維持）
- `rotateZ` (float, オプション): Z軸回転（度単位、省略時は現在値を維持）

**リクエスト例 (全パラメータ指定):**
```json
{
  "sdfPath": "/World/Cube",
  "x": 5.0,
  "y": 0.0,
  "z": 2.0,
  "rotateZ": 45.0
}
```

**リクエスト例 (部分的な更新):**
```json
{
  "sdfPath": "/World/Cube",
  "x": 10.0
}
```

**リクエスト例 (位置のみ更新):**
```json
{
  "sdfPath": "/World/Cube",
  "x": 5.0,
  "y": 2.0,
  "z": 1.0
}
```

**成功レスポンス例:**
```json
{
  "status": "success",
  "message": "Successfully moved prim /World/Cube to position (5.0, 0.0, 2.0) with Z rotation 45.0 degrees",
  "prim_path": "/World/Cube",
  "transform": {
    "translation": [5.0, 0.0, 2.0],
    "rotation_z_degrees": 45.0
  }
}
```

**エラーレスポンス例:**
```json
{
  "status": "error",
  "code": 400,
  "message": "Prim not found at path: /Invalid/Path"
}
```

## Pythonクライアント例

`examples/usdview_http_client_example.py`に完全なPythonクライアントの例があります：

```python
import requests
import json

def send_move_request(sdf_path, x, y, z, rotate_z):
    url = "http://localhost:8080/move"
    data = {
        "sdfPath": sdf_path,
        "x": x,
        "y": y,
        "z": z,
        "rotateZ": rotate_z
    }
    
    response = requests.post(url, json=data)
    return response.json()

# 使用例
result = send_move_request("/World/Cube", 5.0, 0.0, 2.0, 45.0)
print(result)
```

## エラーハンドリング

### 一般的なエラー

1. **400 Bad Request**: 不正なパラメータまたは存在しないPrim
2. **404 Not Found**: 存在しないエンドポイント
3. **500 Internal Server Error**: サーバー内部エラー

### トラブルシューティング

1. **サーバーに接続できない**
   - USDViewerが起動していることを確認
   - ポート番号とホストアドレスが正しいことを確認
   - ファイアウォール設定を確認

2. **Primが見つからない**
   - SdfPathが正しいことを確認
   - USDViewerの階層ブラウザで正確なパスを確認

3. **Transform操作が失敗する**
   - PrimがXformableかどうか確認
   - 数値パラメータが有効な範囲内かどうか確認

## 技術仕様

- **プロトコル**: HTTP/1.1
- **データ形式**: JSON
- **CORS**: 有効（開発用）
- **スレッド**: デーモンスレッドで実行
- **依存関係**: Python標準ライブラリ、USD API

## セキュリティ注意事項

このHTTPサーバーは開発・デバッグ用途を想定しています：

- 認証機能はありません
- 本番環境での使用は推奨されません
- ネットワーク経由でのアクセスを許可する場合は適切なセキュリティ対策を実施してください

## 制限事項

- 現在はMove操作（位置と回転）のみサポート
- Z軸回転のみサポート（X、Y軸回転は今後の拡張予定）
- 同時リクエストの制限はありませんが、USDの並行性制限に従います

## 今後の拡張予定

- 他の変形操作（スケール、完全な回転行列）
- Primの作成・削除
- アトリビュート値の設定・取得
- 複数Primの一括操作
- WebSocket対応によるリアルタイム通信
