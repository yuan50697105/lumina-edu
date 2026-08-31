# Lumina 直播演示流（mediamtx + ffmpeg）

让「开播即有画面」的本地真实 HLS 流方案：`HLS.js` 播放后端 `/media/**` 同源反代，反代转发到本地 mediamtx 把 RTMP 转成 HLS。

## 组成

| 组件 | 说明 | 端口 |
|------|------|------|
| `mediamtx/mediamtx.exe` | 媒体服务器（RTMP 收流 → HLS 输出） | RTMP 1935 · HLS 8888 |
| `media_demo_stream.py` | ffmpeg 推流器：演示课堂画面（标题 + 实时时钟 + 测试色带） | — |
| `start_demo_stream.bat [key]` | 一键：启动 MediaMTX + 推流（默认 `roomdemo`） | — |
| `stop_demo_stream.bat` | 停止 MediaMTX 与 ffmpeg | — |
| `setup_stream.bat` | 新机器安装 ffmpeg（venv imageio-ffmpeg）+ mediamtx 下载指引 | — |

## 快速开始（一键）

```bat
# 首次：准备 mediamtx + ffmpeg（本项目已就绪，新环境执行）
部署\stream\setup_stream.bat

# 起流：MediaMTX + 推流 roomdemo（与演示直播间固定流对应）
部署\stream\start_demo_stream.bat
```

起流后验证 HLS：浏览器打开 `http://127.0.0.1:8888/live/roomdemo/index.m3u8?cookieCheck=1`。

## 后端 / 前端配置

- `服务/lumina-app/.env`（本库已随 gstack demo 写入，需自行创建）：

  ```ini
  LIVE_STREAM_BASE=http://127.0.0.1:8888/live   # mediamtx HLS 根
  LIVE_STREAM_PROXY=true                        # stream_url 走同源 /media 反代
  ```

- 后端 `app/media_proxy.py`：`/media/{path}` → `LIVE_STREAM_BASE/{path}`（开发演示反代，处理 mediamtx cookie 校验）。
- 前端：`LiveRoom.tsx` 播放器已支持 `/media` 相对地址；`vite.config.ts` 已把 `/media` 代理到 8080。

## 演示流程

1. `start_demo_stream.bat`（MediaMTX + 推 roomdemo，常驻）。
2. 后端 8080 + 前端 dev（5173/5174）。
3. 教师登录，进入「冒烟测试课程」→「直播演示间（固定流 roomdemo）」→ 点**开播**。
4. 播放器立刻出现真实画面（直播画面/时钟在动）。

> 任意房间：创建房间后，用房间 `stream_key` 以 `start_demo_stream.bat <key>` 起对应推流即可。

## 生产形态说明

生产环境不依赖本演示反代：把 `LIVE_STREAM_PROXY=false`，`LIVE_STREAM_BASE` 指向 CDN / 网关上的 HLS 根，由网关把 `/media`（或直接 HLS 域名）→ 媒体服务器。`app/media_proxy.py` 仅开发/演示使用。