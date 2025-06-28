import os
import subprocess
import paramiko
from urllib.parse import urlparse
import base64

# 設定檔案路徑
yt_info_path = "yt_info.txt"
output_dir = "output"
cookies_path = os.path.join(os.getcwd(), "cookies.txt")

# 從環境變數讀取 SFTP 連線資訊
SF_L = os.getenv("SF_L", "")

if not SF_L:
    print("❌ 環境變數 SF_L 未設置")
    exit(1)

# 解析 SFTP URL
parsed_url = urlparse(SF_L)

SFTP_HOST = parsed_url.hostname
SFTP_PORT = parsed_url.port if parsed_url.port else 22  # 預設 SFTP 端口 22
SFTP_USER = parsed_url.username
SFTP_PASSWORD = parsed_url.password
SFTP_REMOTE_DIR = parsed_url.path if parsed_url.path else "/"  # 取得路徑部分

# 確保輸出目錄存在
os.makedirs(output_dir, exist_ok=True)

def grab(youtube_url):
    """使用 yt-dlp 解析 M3U8 連結"""
    yt_dlp_cmd = f"yt-dlp --cookies cookies.txt -f 'best[height=720]' -g {youtube_url}"
    try:
        result = subprocess.run(yt_dlp_cmd, shell=True, capture_output=True, text=True, check=True)
        m3u8_url = result.stdout.strip()
        if m3u8_url.startswith("http"):
            return m3u8_url
    except subprocess.CalledProcessError as e:
        print(f"⚠️ yt-dlp 解析失敗，錯誤訊息: {e.stderr}")
    return "https://raw.githubusercontent.com/dks-123/YT2m/main/assets/no_s.m3u8"  # 預設無訊號M3U8

def process_yt_info():
    """解析 yt_info.txt 並生成 M3U8 和 PHP 檔案"""
    with open(yt_info_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 1
    for line in lines:
        line = line.strip()
        if line.startswith("~~") or not line:
            continue
        if "|" in line:  # 頻道資訊行
            parts = line.split("|")
            channel_name = parts[0].strip() if len(parts) > 0 else f"Channel {i}"
        else:  # YouTube 連結行
            youtube_url = line
            print(f"🔍 嘗試解析 M3U8: {youtube_url}")
            m3u8_url = grab(youtube_url)

            # 生成 M3U8 文件
            m3u8_content = f"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1280000\n{m3u8_url}\n"
            output_m3u8 = os.path.join(output_dir, f"y{i:02d}.m3u8")
            with open(output_m3u8, "w", encoding="utf-8") as f:
                f.write(m3u8_content)

            # 生成 PHP 文件
            php_content = f"""<?php
header('Location: {m3u8_url}');
?>"""
            output_php = os.path.join(output_dir, f"y{i:02d}.php")
            with open(output_php, "w", encoding="utf-8") as f:
                f.write(php_content)

            print(f"✅ 生成 {output_m3u8} 和 {output_php}")
            i += 1

def upload_files():
    """使用 SFTP 上傳 M3U8 檔案"""
    print("🚀 啟動 SFTP 上傳程序...")
    try:
        
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp = paramiko.SFTPClient.from_transport(transport)

        print(f"✅ 成功連接到 SFTP：{SFTP_HOST}")

        # 確保遠端目錄存在
        try:
            sftp.chdir(SFTP_REMOTE_DIR)
        except IOError:
            print(f"📁 遠端目錄 {SFTP_REMOTE_DIR} 不存在，正在創建...")
            sftp.mkdir(SFTP_REMOTE_DIR)
            sftp.chdir(SFTP_REMOTE_DIR)

        # 上傳所有檔案
        for file in os.listdir(output_dir):
            local_path = os.path.join(output_dir, file)
            remote_path = os.path.join(SFTP_REMOTE_DIR, file)
            print(f"Local file: {local_path}")
            if os.path.isfile(local_path):
                print(f"⬆️ 上傳 {local_path} → {remote_path}")
                sftp.put(local_path, remote_path)

        sftp.close()
        transport.close()
        print("✅ SFTP 上傳完成！")

    except Exception as e:
        print(f"❌ SFTP 上傳失敗: {e}")

if __name__ == "__main__":
    process_yt_info()
    upload_files()
