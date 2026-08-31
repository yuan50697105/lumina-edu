# ============================================
# Lumina 墨光 · 直播演示推流器
# 用 ffmpeg 向 mediamtx 推送「演示课堂画面」（墨色底 + 实时时钟 + 中英标题）
# 默认推流键 roomdemo，对应演示直播间的固定 stream_key
# 用法：
#   python media_demo_stream.py                     # 推流 roomdemo（默认）
#   python media_demo_stream.py --key roomxxxx      # 推流到指定房间 key
#   python media_demo_stream.py --title "高级数据结构"  # 自定义画面标题
# 停止：Ctrl+C（.bat 启动时），或 stop_demo_stream.bat
# ============================================
import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def find_ffmpeg() -> str | None:
    """优先系统 PATH，其次 lumina-app venv 内 imageio-ffmpeg 静态二进制"""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Lumina 直播演示推流")
    ap.add_argument("--key", default="roomdemo", help="推流键（= 直播房间 stream_key）")
    ap.add_argument("--title", default="墨光 · 实时课堂直播", help="画面标题文本")
    ap.add_argument("--rtmp", default="rtmp://127.0.0.1:1935/live", help="mediamtx RTMP 端点")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        sys.exit("未找到 ffmpeg：请安装 ffmpeg 或先 `pip install imageio-ffmpeg`")

    key = args.key.lstrip("/")
    # 标题经 UTF-8 临时文件传给 drawtext，规避 Windows 命令行编码问题
    fd, title_file = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(args.title)

    try:
        # 画面：testsrc2 测试色带 + 顶部标题 + 底部实时时码
        vf = (
            f"drawtext=fontfile='C\\:/Windows/Fonts/msyh.ttc':textfile='{title_file}'"
            ":fontcolor=0xFFFFFF:fontsize=56:box=1:boxcolor=0x000000@0.5"
            ":boxborderw=20:x=(w-text_w)/2:y=48,"
            "drawtext=fontfile='C\\:/Windows/Fonts/arial.ttf':text='%{pts\\:hms}'"
            ":fontcolor=0xF5B800:fontsize=44:box=1:boxcolor=0x000000@0.4"
            ":boxborderw=16:x=(w-text_w)/2:y=h-130"
        )
        cmd = [
            ffmpeg, "-y", "-re",
            "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-b:v", "1500k", "-g", "60", "-keyint_min", "60", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k",
            "-f", "flv", f"{args.rtmp.rstrip('/')}/{key}",
        ]
        print("推流地址:", f"{args.rtmp.rstrip('/')}/{key}")
        print("HLS 播放: http://127.0.0.1:8888/live/{key}/index.m3u8".format(key=key))
        print("按 Ctrl+C 停止推流")
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\n停止推流")
    finally:
        os.unlink(title_file)


if __name__ == "__main__":
    sys.exit(main())