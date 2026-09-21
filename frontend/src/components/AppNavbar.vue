<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { session, clearSession, homePathFor } from '../auth'
import { logout } from '../api/auth'

const router = useRouter()

const isAdmin = computed(() => session.user?.role === 'ADMIN')
const userLabel = computed(() => {
  const user = session.user
  return `${user.name} (${isAdmin.value ? '관리자' : user.department?.name ?? '소속 없음'})`
})

async function onLogout() {
  try {
    await logout()
  } catch {
    // 서버 호출이 실패해도 클라이언트 세션은 지운다
  }
  clearSession()
  router.push('/login')
}
</script>

<template>
  <nav class="navbar navbar-expand navbar-dark bg-dark">
    <div class="container">
      <router-link class="navbar-brand" :to="homePathFor(session.user)">경영지표 대시보드</router-link>
      <ul class="navbar-nav me-auto">
        <li v-if="!isAdmin" class="nav-item">
          <router-link class="nav-link" active-class="active" to="/entry">월 실적 입력</router-link>
        </li>
        <template v-if="isAdmin">
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/admin/dashboard">대시보드</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/admin/report">월별 리포트</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/admin/status">입력 현황</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/admin/goals">연간 목표</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/admin/users">사용자</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/admin/departments">부서·항목</router-link>
          </li>
        </template>
      </ul>
      <span class="navbar-text me-3">{{ userLabel }}</span>
      <button type="button" class="btn btn-outline-light btn-sm" @click="onLogout">로그아웃</button>
    </div>
  </nav>
</template>
