import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// dev 代理：前端 5173 → user-service:8080（Nginx 按路径分发到各服务）
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8080',
                changeOrigin: true,
                // SSE 流式：关闭缓冲
                configure: function (proxy) {
                    proxy.on('proxyReq', function (_proxyReq, _req, _res) {
                        ;
                        _res.setHeader('X-Accel-Buffering', 'no');
                    });
                },
            },
        },
    },
});
