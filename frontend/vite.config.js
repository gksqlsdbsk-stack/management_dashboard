import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 개발 중 /api 는 Django(8000)로 프록시한다 (CORS 설정 대신) [A-39]
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
