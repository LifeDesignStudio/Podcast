#!/usr/bin/env python3
"""
podcast_admin.py — ポッドキャストエピソード管理サーバー
使い方: python3 podcast_admin.py
ブラウザで http://localhost:8080 が自動的に開きます
"""

import json
import os
import subprocess
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
EPISODES_JSON = os.path.join(REPO_DIR, "episodes.json")
EPISODES_DIR = os.path.join(REPO_DIR, "docs", "episodes")
PORT = 8080


def load_episodes():
    with open(EPISODES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_episodes(data):
    with open(EPISODES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def delete_episodes(filenames):
    data = load_episodes()
    deleted = []
    not_found = []

    for filename in filenames:
        before = len(data["episodes"])
        data["episodes"] = [e for e in data["episodes"] if e["filename"] != filename]
        if len(data["episodes"]) < before:
            deleted.append(filename)
            mp3_path = os.path.join(EPISODES_DIR, filename)
            if os.path.exists(mp3_path):
                os.remove(mp3_path)
        else:
            not_found.append(filename)

    if not deleted:
        return False, not_found

    save_episodes(data)
    subprocess.run(["python3", "generate_feed.py"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "add", "."], cwd=REPO_DIR, check=True)
    commit_msg = "Delete episode(s): " + ", ".join(deleted)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, check=True)

    local_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_DIR, capture_output=True, text=True
    ).stdout.strip()

    subprocess.run(
        ["git", "push", "origin", "main"],
        cwd=REPO_DIR, capture_output=True, text=True
    )

    # push の成否はリモートの実際の状態で判定（VS Code が先行 push する場合があるため）
    subprocess.run(["git", "fetch", "origin"], cwd=REPO_DIR, capture_output=True)
    remote_head = subprocess.run(
        ["git", "rev-parse", "origin/main"], cwd=REPO_DIR, capture_output=True, text=True
    ).stdout.strip()
    if remote_head != local_head:
        raise RuntimeError("リモートへの反映に失敗しました。手動で git push してください。")

    return True, deleted


def format_size(size_bytes):
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / 1024:.0f} KB"


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Podcast 管理</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    background: #f5f5f7; color: #1d1d1f;
    max-width: 860px; margin: 0 auto; padding: 48px 24px;
  }
  h1 { font-size: 28px; font-weight: 700; margin-bottom: 6px; }
  .subtitle { font-size: 15px; color: #6e6e73; margin-bottom: 32px; }
  .message {
    padding: 14px 18px; border-radius: 10px; margin-bottom: 24px; font-size: 14px;
  }
  .message.success { background: #d4f5e2; color: #1a6e3c; }
  .message.error   { background: #fde8e8; color: #c00; }
  .card {
    background: white; border-radius: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08); overflow: hidden;
  }
  .episode {
    display: flex; align-items: center;
    padding: 14px 20px; border-bottom: 1px solid #f0f0f0; gap: 14px;
    transition: background 0.1s;
  }
  .episode:last-child { border-bottom: none; }
  .episode:hover { background: #fafafa; }
  .episode input[type=checkbox] {
    width: 18px; height: 18px; flex-shrink: 0;
    cursor: pointer; accent-color: #ff3b30;
  }
  .episode label { flex: 1; cursor: pointer; }
  .ep-title { font-size: 15px; font-weight: 600; margin-bottom: 3px; }
  .ep-meta { font-size: 13px; color: #6e6e73; }
  .sep { margin: 0 6px; }
  .controls {
    display: flex; align-items: center; gap: 16px; margin-top: 20px; flex-wrap: wrap;
  }
  .btn-ghost {
    font-size: 14px; color: #0071e3; background: none;
    border: none; padding: 0; cursor: pointer;
  }
  .btn-ghost:hover { text-decoration: underline; }
  .selected-count { font-size: 14px; color: #6e6e73; }
  .btn-delete {
    margin-left: auto;
    background: #ff3b30; color: white; border: none;
    padding: 10px 22px; border-radius: 8px;
    font-size: 15px; font-weight: 600; cursor: pointer;
  }
  .btn-delete:hover:not(:disabled) { background: #d70015; }
  .btn-delete:disabled { background: #c7c7cc; cursor: not-allowed; }
  .empty { text-align: center; padding: 60px 20px; color: #6e6e73; font-size: 15px; }
</style>
</head>
<body>
<h1>🎙️ Podcast 管理</h1>
<p class="subtitle">エピソードを選択して削除できます</p>
{message}
{content}
<script>
function updateUI() {
  const checked = document.querySelectorAll('input[type=checkbox]:checked').length;
  const total = document.querySelectorAll('input[type=checkbox]').length;
  document.getElementById('count').textContent = checked > 0 ? checked + ' 件選択中' : '';
  document.getElementById('deleteBtn').disabled = checked === 0;
  document.getElementById('toggleBtn').textContent =
    checked === total ? 'すべて解除' : 'すべて選択';
}
function toggleAll() {
  const boxes = document.querySelectorAll('input[type=checkbox]');
  const allChecked = [...boxes].every(b => b.checked);
  boxes.forEach(b => { b.checked = !allChecked; });
  updateUI();
}
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[type=checkbox]').forEach(b =>
    b.addEventListener('change', updateUI));
  updateUI();
});
</script>
</body>
</html>
"""


def render_page(message="", message_type=""):
    data = load_episodes()
    episodes = data["episodes"]

    msg_html = (
        f'<div class="message {message_type}">{message}</div>' if message else ""
    )

    if not episodes:
        content = '<div class="card"><div class="empty">エピソードがありません</div></div>'
    else:
        rows = []
        for ep in episodes:
            fn = ep["filename"].replace('"', "&quot;")
            title = ep["title"].replace("<", "&lt;").replace(">", "&gt;")
            size = format_size(ep["file_size_bytes"])
            rows.append(
                f'  <div class="episode">'
                f'<input type="checkbox" name="filenames" value="{fn}" id="cb_{fn}">'
                f'<label for="cb_{fn}">'
                f'<div class="ep-title">{title}</div>'
                f'<div class="ep-meta">{ep["pub_date"]}'
                f'<span class="sep">·</span>{ep["duration"]}'
                f'<span class="sep">·</span>{size}</div>'
                f'</label></div>'
            )
        content = (
            '<form method="POST" action="/delete"'
            ' onsubmit="return confirm(\'選択したエピソードを削除しますか？この操作は元に戻せません。\')">'
            '<div class="card">' + "\n".join(rows) + "</div>"
            '<div class="controls">'
            '<button type="button" class="btn-ghost" id="toggleBtn" onclick="toggleAll()">すべて選択</button>'
            '<span class="selected-count" id="count"></span>'
            '<button type="submit" class="btn-delete" id="deleteBtn" disabled>削除する</button>'
            "</div></form>"
        )

    return (HTML_TEMPLATE
            .replace("{message}", msg_html)
            .replace("{content}", content)
            .encode("utf-8"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            body = render_page()
            self._send(200, body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/delete":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8")
            params = parse_qs(raw)
            filenames = params.get("filenames", [])

            if not filenames:
                body = render_page("削除するエピソードが選択されていません", "error")
            else:
                try:
                    ok, result = delete_episodes(filenames)
                    if ok:
                        msg = f"{len(result)} 件を削除しました"
                        body = render_page(msg, "success")
                    else:
                        body = render_page("対象エピソードが見つかりませんでした", "error")
                except Exception as e:
                    body = render_page(f"エラーが発生しました: {e}", "error")

            self._send(200, body)
        else:
            self.send_response(404)
            self.end_headers()

    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Podcast 管理サーバー起動中: {url}")
    print("終了するには Ctrl+C を押してください")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止しました")
        server.server_close()


if __name__ == "__main__":
    main()
