import { createRouter, createWebHistory } from 'vue-router'
import { session, setSession, clearSession, homePathFor } from '../auth'
import { fetchMe } from '../api/auth'
import LoginView from '../views/LoginView.vue'
import EntryView from '../views/EntryView.vue'
import AdminDashboardView from '../views/AdminDashboardView.vue'

const routes = [
  { path: '/login', component: LoginView, meta: { public: true } },
  { path: '/entry', component: EntryView, meta: { role: 'EMPLOYEE' } },
  { path: '/admin/dashboard', component: AdminDashboardView, meta: { role: 'ADMIN' } },
  // `/` 포함 알 수 없는 경로는 로그인으로 보낸다. 로그인 상태면 가드가 역할별 홈으로 다시 보낸다.
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 화면 접근 제어(실제 통제는 서버가 한다) [04 §1]
router.beforeEach(async (to) => {
  // 새로고침 후 토큰만 남아 있으면 현재 사용자를 다시 불러온다
  if (session.token && !session.user) {
    try {
      setSession(session.token, await fetchMe())
    } catch {
      clearSession()
    }
  }

  if (!session.user) {
    return to.meta.public ? true : '/login'
  }
  if (to.meta.public) {
    return homePathFor(session.user)
  }
  if (to.meta.role && to.meta.role !== session.user.role) {
    return homePathFor(session.user)
  }
  return true
})

export default router
