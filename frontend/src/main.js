import { createApp } from 'vue'
import 'bootstrap/dist/css/bootstrap.min.css' // CSS만 사용한다 (Bootstrap JS 미사용) [A-38]
import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/client'

setUnauthorizedHandler(() => router.push('/login'))

createApp(App).use(router).mount('#app')
