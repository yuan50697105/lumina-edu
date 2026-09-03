import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// dev 代理：前端 5173 → user-service:8080（Nginx 按路径分发到各服务）
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
        // SSE 流式：关闭缓冲
        configure: (proxy) => {
          proxy.on('proxyReq', (_proxyReq, _req, _res) => {
            ;(_res as any).setHeader('X-Accel-Buffering', 'no')
          })
        },
      },
      // 直播 HLS 同源反代（后端 /media → mediamtx）
      '/media': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
})