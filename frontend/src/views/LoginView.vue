<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { setSession, homePathFor } from '../auth'
import { login } from '../api/auth'

const router = useRouter()

const name = ref('')
const employeeNo = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function onSubmit() {
  errorMessage.value = ''
  submitting.value = true
  try {
    const result = await login(name.value.trim(), employeeNo.value.trim(), password.value)
    setSession(result.token, result.user)
    router.push(homePathFor(result.user))
  } catch (error) {
    errorMessage.value =
      error.code === 'login_failed' ? error.message : '로그인에 실패했습니다. 입력값을 확인해 주세요.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="row justify-content-center">
    <div class="col-md-5 col-lg-4">
      <h1 class="h4 text-center mb-4">경영지표 대시보드</h1>
      <form class="card card-body" @submit.prevent="onSubmit">
        <div v-if="errorMessage" class="alert alert-danger" role="alert">{{ errorMessage }}</div>
        <div class="mb-3">
          <label for="name" class="form-label">성명</label>
          <input id="name" v-model="name" type="text" class="form-control" required autofocus />
        </div>
        <div class="mb-3">
          <label for="employee-no" class="form-label">사번</label>
          <input id="employee-no" v-model="employeeNo" type="text" class="form-control" required />
        </div>
        <div class="mb-3">
          <label for="password" class="form-label">비밀번호</label>
          <input id="password" v-model="password" type="password" class="form-control" required />
        </div>
        <button type="submit" class="btn btn-primary" :disabled="submitting">로그인</button>
      </form>
    </div>
  </div>
</template>
