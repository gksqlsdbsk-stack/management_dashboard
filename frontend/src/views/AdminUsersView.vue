<script setup>
import { onMounted, reactive, ref } from 'vue'
import { listUsers, createUser, updateUser, deleteUser } from '../api/users'
import { listDepartments } from '../api/departments'
import { errorAlert, successAlert, noAlert } from '../utils/errors'
import InlineAlert from '../components/InlineAlert.vue'

const FIELD_LABELS = {
  name: '성명',
  employee_no: '사번',
  role: '역할',
  department_id: '부서',
  password: '비밀번호',
  is_active: '활성 여부',
}
const ROLE_LABELS = { EMPLOYEE: '직원', ADMIN: '관리자' }

const users = ref([])
const departments = ref([])
const pageAlert = ref(noAlert())
const formAlert = ref(noAlert())
const formMode = ref('') // '' | 'create' | 'edit'
const saving = ref(false)
const form = reactive({})

function resetForm(user = null) {
  Object.assign(form, {
    id: user?.id ?? null,
    name: user?.name ?? '',
    employeeNo: user?.employee_no ?? '',
    role: user?.role ?? 'EMPLOYEE',
    departmentId: user?.department?.id ?? '',
    password: '',
    isActive: user?.is_active ?? true,
  })
}

async function load() {
  try {
    ;[users.value, departments.value] = await Promise.all([listUsers(), listDepartments()])
  } catch (error) {
    pageAlert.value = errorAlert(error)
  }
}

function openCreate() {
  resetForm()
  formAlert.value = noAlert()
  pageAlert.value = noAlert()
  formMode.value = 'create'
}

function openEdit(user) {
  resetForm(user)
  formAlert.value = noAlert()
  pageAlert.value = noAlert()
  formMode.value = 'edit'
}

function closeForm() {
  formMode.value = ''
}

async function save() {
  formAlert.value = noAlert()
  saving.value = true
  const payload = {
    name: form.name.trim(),
    employee_no: form.employeeNo.trim(),
    role: form.role,
    department_id: form.departmentId || null,
    is_active: form.isActive,
  }
  if (form.password) payload.password = form.password
  try {
    if (formMode.value === 'create') await createUser(payload)
    else await updateUser(form.id, payload)
    closeForm()
    pageAlert.value = successAlert('저장되었습니다.')
    await load()
  } catch (error) {
    formAlert.value = errorAlert(error, FIELD_LABELS)
  } finally {
    saving.value = false
  }
}

async function remove(user) {
  if (!confirm(`'${user.name}' 사용자를 삭제하시겠습니까?`)) return
  pageAlert.value = noAlert()
  try {
    await deleteUser(user.id)
    if (formMode.value === 'edit' && form.id === user.id) closeForm()
    pageAlert.value = successAlert('삭제되었습니다.')
    await load()
  } catch (error) {
    pageAlert.value = errorAlert(error)
  }
}

onMounted(load)
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h1 class="h4 mb-0">사용자 관리</h1>
    <button type="button" class="btn btn-primary btn-sm" @click="openCreate">+ 사용자 추가</button>
  </div>

  <div class="alert alert-info">기본 관리자(ADMIN)의 초기 비밀번호는 변경하세요.</div>
  <InlineAlert :alert="pageAlert" />

  <form v-if="formMode" class="card card-body mb-4" @submit.prevent="save">
    <h2 class="h6">{{ formMode === 'create' ? '사용자 추가' : '사용자 수정' }}</h2>
    <InlineAlert :alert="formAlert" />
    <div class="row g-3">
      <div class="col-md-3">
        <label for="user-name" class="form-label">성명</label>
        <input id="user-name" v-model="form.name" type="text" class="form-control" maxlength="50" required />
      </div>
      <div class="col-md-3">
        <label for="user-no" class="form-label">사번</label>
        <input id="user-no" v-model="form.employeeNo" type="text" class="form-control" maxlength="150" required />
      </div>
      <div class="col-md-3">
        <label for="user-role" class="form-label">역할</label>
        <select id="user-role" v-model="form.role" class="form-select">
          <option value="EMPLOYEE">직원</option>
          <option value="ADMIN">관리자</option>
        </select>
      </div>
      <div class="col-md-3">
        <label for="user-dept" class="form-label">부서<span v-if="form.role === 'EMPLOYEE'"> (필수)</span></label>
        <select id="user-dept" v-model="form.departmentId" class="form-select">
          <option value="">선택 안 함</option>
          <option v-for="department in departments" :key="department.id" :value="department.id">
            {{ department.name }}
          </option>
        </select>
      </div>
      <div class="col-md-6">
        <label for="user-password" class="form-label">
          비밀번호<span v-if="formMode === 'create'"> (8자 이상)</span>
        </label>
        <input
          id="user-password"
          v-model="form.password"
          type="password"
          class="form-control"
          minlength="8"
          autocomplete="new-password"
          :required="formMode === 'create'"
        />
        <div v-if="formMode === 'edit'" class="form-text">입력하면 비밀번호가 재설정됩니다. 비워 두면 유지됩니다.</div>
      </div>
      <div class="col-md-6 d-flex align-items-end">
        <div class="form-check">
          <input id="user-active" v-model="form.isActive" type="checkbox" class="form-check-input" />
          <label for="user-active" class="form-check-label">활성 (로그인 가능)</label>
        </div>
      </div>
    </div>
    <div class="mt-3">
      <button type="submit" class="btn btn-primary btn-sm me-2" :disabled="saving">저장</button>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="closeForm">취소</button>
    </div>
  </form>

  <table class="table table-sm align-middle">
    <thead>
      <tr>
        <th>성명</th>
        <th>사번</th>
        <th>역할</th>
        <th>부서</th>
        <th>활성 여부</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="user in users" :key="user.id">
        <td>{{ user.name }}</td>
        <td>{{ user.employee_no }}</td>
        <td>{{ ROLE_LABELS[user.role] }}</td>
        <td>{{ user.department?.name ?? '-' }}</td>
        <td>
          <span class="badge" :class="user.is_active ? 'bg-success' : 'bg-secondary'">
            {{ user.is_active ? '활성' : '비활성' }}
          </span>
        </td>
        <td class="text-end">
          <button type="button" class="btn btn-outline-secondary btn-sm me-1" @click="openEdit(user)">수정</button>
          <button type="button" class="btn btn-outline-danger btn-sm" @click="remove(user)">삭제</button>
        </td>
      </tr>
      <tr v-if="!users.length">
        <td colspan="6" class="text-center text-muted">사용자가 없습니다.</td>
      </tr>
    </tbody>
  </table>
</template>
