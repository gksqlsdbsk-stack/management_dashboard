<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  listDepartments, createDepartment, updateDepartment, deleteDepartment,
  listItems, createItem, updateItem, deleteItem, listMetricKeys,
} from '../api/departments'
import { errorAlert, successAlert, noAlert } from '../utils/errors'
import InlineAlert from '../components/InlineAlert.vue'

const DEPARTMENT_LABELS = { name: '부서명', input_guide: '입력 안내 문구', sort_order: '순서' }
const ITEM_LABELS = {
  name: '항목명',
  scope: '범위',
  unit: '단위',
  metric_key: '지표 연동 키',
  help_text: '안내 문구',
  is_required: '필수 여부',
  sort_order: '순서',
}
const SCOPE_LABELS = { MONTHLY: '월 합계형', PROJECT: '프로젝트별형' }

const departments = ref([])
const items = ref([])
const metricKeys = ref([])
const selectedId = ref(null)
const pageAlert = ref(noAlert())
const saving = ref(false)

const deptMode = ref('') // '' | 'create' | 'edit'
const deptAlert = ref(noAlert())
const deptForm = reactive({})

const itemMode = ref('')
const itemAlert = ref(noAlert())
const itemForm = reactive({})

const selectedDepartment = computed(() => departments.value.find((d) => d.id === selectedId.value) ?? null)
const metricKeyLabel = (key) => metricKeys.value.find((m) => m.key === key)?.label ?? '-'

async function loadDepartments() {
  departments.value = await listDepartments()
}

async function loadItems() {
  items.value = selectedId.value ? await listItems(selectedId.value) : []
}

async function selectDepartment(id) {
  selectedId.value = id
  itemMode.value = ''
  try {
    await loadItems()
  } catch (error) {
    pageAlert.value = errorAlert(error)
  }
}

// ---- 부서 ----
function openDeptCreate() {
  Object.assign(deptForm, { id: null, name: '', inputGuide: '', sortOrder: 0 })
  deptAlert.value = noAlert()
  pageAlert.value = noAlert()
  deptMode.value = 'create'
}

function openDeptEdit(department) {
  Object.assign(deptForm, {
    id: department.id,
    name: department.name,
    inputGuide: department.input_guide,
    sortOrder: department.sort_order,
  })
  deptAlert.value = noAlert()
  pageAlert.value = noAlert()
  deptMode.value = 'edit'
}

async function saveDepartment() {
  deptAlert.value = noAlert()
  saving.value = true
  const payload = {
    name: deptForm.name.trim(),
    input_guide: deptForm.inputGuide,
    sort_order: Number(deptForm.sortOrder) || 0,
  }
  try {
    let saved
    if (deptMode.value === 'create') saved = await createDepartment(payload)
    else saved = await updateDepartment(deptForm.id, payload)
    deptMode.value = ''
    pageAlert.value = successAlert('저장되었습니다.')
    await loadDepartments()
    if (!selectedId.value) await selectDepartment(saved.id)
  } catch (error) {
    deptAlert.value = errorAlert(error, DEPARTMENT_LABELS)
  } finally {
    saving.value = false
  }
}

async function removeDepartment(department) {
  if (!confirm(`'${department.name}' 부서를 삭제하시겠습니까?\n과거 제출 데이터는 유지됩니다.`)) return
  pageAlert.value = noAlert()
  try {
    await deleteDepartment(department.id)
    deptMode.value = ''
    pageAlert.value = successAlert('삭제되었습니다.')
    await loadDepartments()
    if (selectedId.value === department.id) {
      await selectDepartment(departments.value[0]?.id ?? null)
    }
  } catch (error) {
    pageAlert.value = errorAlert(error)
  }
}

// ---- 입력 항목 ----
function openItemCreate() {
  Object.assign(itemForm, {
    id: null,
    name: '',
    scope: 'MONTHLY',
    unit: '',
    metricKey: '',
    isRequired: true,
    helpText: '',
    sortOrder: items.value.length + 1,
  })
  itemAlert.value = noAlert()
  pageAlert.value = noAlert()
  itemMode.value = 'create'
}

function openItemEdit(item) {
  Object.assign(itemForm, {
    id: item.id,
    name: item.name,
    scope: item.scope,
    unit: item.unit,
    metricKey: item.metric_key ?? '',
    isRequired: item.is_required,
    helpText: item.help_text,
    sortOrder: item.sort_order,
  })
  itemAlert.value = noAlert()
  pageAlert.value = noAlert()
  itemMode.value = 'edit'
}

async function saveItem() {
  itemAlert.value = noAlert()
  saving.value = true
  const payload = {
    name: itemForm.name.trim(),
    scope: itemForm.scope,
    unit: itemForm.unit.trim(),
    metric_key: itemForm.metricKey || null,
    is_required: itemForm.isRequired,
    help_text: itemForm.helpText,
    sort_order: Number(itemForm.sortOrder) || 0,
  }
  try {
    if (itemMode.value === 'create') await createItem(selectedId.value, payload)
    else await updateItem(itemForm.id, payload)
    itemMode.value = ''
    pageAlert.value = successAlert('저장되었습니다.')
    await loadItems()
  } catch (error) {
    itemAlert.value = errorAlert(error, ITEM_LABELS)
  } finally {
    saving.value = false
  }
}

async function removeItem(item) {
  if (!confirm(`'${item.name}' 항목을 삭제하시겠습니까?\n과거 제출 데이터는 유지됩니다.`)) return
  pageAlert.value = noAlert()
  try {
    await deleteItem(item.id)
    itemMode.value = ''
    pageAlert.value = successAlert('삭제되었습니다.')
    await loadItems()
  } catch (error) {
    pageAlert.value = errorAlert(error)
  }
}

onMounted(async () => {
  try {
    ;[metricKeys.value] = await Promise.all([listMetricKeys(), loadDepartments()])
    if (departments.value.length) await selectDepartment(departments.value[0].id)
  } catch (error) {
    pageAlert.value = errorAlert(error)
  }
})
</script>

<template>
  <h1 class="h4 mb-3">부서·입력 항목 관리</h1>
  <InlineAlert :alert="pageAlert" />

  <div class="row g-4">
    <!-- 부서 목록 -->
    <div class="col-lg-4">
      <div class="d-flex justify-content-between align-items-center mb-2">
        <h2 class="h6 mb-0">부서</h2>
        <button type="button" class="btn btn-primary btn-sm" @click="openDeptCreate">+ 부서 추가</button>
      </div>

      <form v-if="deptMode" class="card card-body mb-3" @submit.prevent="saveDepartment">
        <h3 class="h6">{{ deptMode === 'create' ? '부서 추가' : '부서 수정' }}</h3>
        <InlineAlert :alert="deptAlert" />
        <div class="mb-2">
          <label for="dept-name" class="form-label">부서명</label>
          <input id="dept-name" v-model="deptForm.name" type="text" class="form-control" maxlength="50" required />
        </div>
        <div class="mb-2">
          <label for="dept-guide" class="form-label">입력 안내 문구</label>
          <textarea id="dept-guide" v-model="deptForm.inputGuide" class="form-control" rows="4"></textarea>
          <div class="form-text">직원 입력 화면 상단에 표시됩니다.</div>
        </div>
        <div class="mb-3">
          <label for="dept-order" class="form-label">순서</label>
          <input id="dept-order" v-model="deptForm.sortOrder" type="number" min="0" class="form-control" />
        </div>
        <div>
          <button type="submit" class="btn btn-primary btn-sm me-2" :disabled="saving">저장</button>
          <button type="button" class="btn btn-outline-secondary btn-sm" @click="deptMode = ''">취소</button>
        </div>
      </form>

      <div class="list-group">
        <div
          v-for="department in departments"
          :key="department.id"
          class="list-group-item d-flex justify-content-between align-items-center"
          :class="{ active: department.id === selectedId }"
        >
          <a
            href="#"
            class="flex-grow-1 text-decoration-none"
            :class="department.id === selectedId ? 'text-white' : 'text-body'"
            @click.prevent="selectDepartment(department.id)"
          >
            {{ department.name }}
          </a>
          <span class="text-nowrap">
            <button
              type="button"
              class="btn btn-sm me-1"
              :class="department.id === selectedId ? 'btn-outline-light' : 'btn-outline-secondary'"
              @click="openDeptEdit(department)"
            >
              수정
            </button>
            <button type="button" class="btn btn-outline-danger btn-sm" @click="removeDepartment(department)">삭제</button>
          </span>
        </div>
        <div v-if="!departments.length" class="list-group-item text-muted">부서가 없습니다.</div>
      </div>
    </div>

    <!-- 선택한 부서의 입력 항목 -->
    <div class="col-lg-8">
      <div v-if="selectedDepartment">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <h2 class="h6 mb-0">{{ selectedDepartment.name }} 입력 항목</h2>
          <button type="button" class="btn btn-primary btn-sm" @click="openItemCreate">+ 항목 추가</button>
        </div>

        <form v-if="itemMode" class="card card-body mb-3" @submit.prevent="saveItem">
          <h3 class="h6">{{ itemMode === 'create' ? '항목 추가' : '항목 수정' }}</h3>
          <InlineAlert :alert="itemAlert" />
          <div class="row g-3">
            <div class="col-md-6">
              <label for="item-name" class="form-label">항목명</label>
              <input id="item-name" v-model="itemForm.name" type="text" class="form-control" maxlength="100" required />
            </div>
            <div class="col-md-3">
              <label for="item-scope" class="form-label">범위</label>
              <select id="item-scope" v-model="itemForm.scope" class="form-select">
                <option value="MONTHLY">월 합계형</option>
                <option value="PROJECT">프로젝트별형</option>
              </select>
            </div>
            <div class="col-md-3">
              <label for="item-unit" class="form-label">단위</label>
              <input id="item-unit" v-model="itemForm.unit" type="text" class="form-control" maxlength="20" placeholder="원, %, 개, 명" />
            </div>
            <div class="col-md-6">
              <label for="item-metric" class="form-label">지표 연동 키</label>
              <select id="item-metric" v-model="itemForm.metricKey" class="form-select">
                <option value="">연동 안 함</option>
                <option v-for="metric in metricKeys" :key="metric.key" :value="metric.key">
                  {{ metric.label }} ({{ metric.key }})
                </option>
              </select>
              <div class="form-text">연동하지 않은 항목은 수집·조회만 되고 지표 계산에는 쓰이지 않습니다.</div>
            </div>
            <div class="col-md-3">
              <label for="item-order" class="form-label">순서</label>
              <input id="item-order" v-model="itemForm.sortOrder" type="number" min="0" class="form-control" />
            </div>
            <div class="col-md-3 d-flex align-items-end">
              <div class="form-check">
                <input id="item-required" v-model="itemForm.isRequired" type="checkbox" class="form-check-input" />
                <label for="item-required" class="form-check-label">필수 항목</label>
              </div>
            </div>
            <div class="col-12">
              <label for="item-help" class="form-label">안내 문구</label>
              <textarea id="item-help" v-model="itemForm.helpText" class="form-control" rows="2"></textarea>
              <div class="form-text">입력 칸 아래에 표시됩니다.</div>
            </div>
          </div>
          <div class="mt-3">
            <button type="submit" class="btn btn-primary btn-sm me-2" :disabled="saving">저장</button>
            <button type="button" class="btn btn-outline-secondary btn-sm" @click="itemMode = ''">취소</button>
          </div>
        </form>

        <table class="table table-sm align-middle">
          <thead>
            <tr>
              <th>항목명</th>
              <th>범위</th>
              <th>단위</th>
              <th>지표 연동 키</th>
              <th>필수</th>
              <th>순서</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>{{ item.name }}</td>
              <td>{{ SCOPE_LABELS[item.scope] }}</td>
              <td>{{ item.unit || '-' }}</td>
              <td>{{ metricKeyLabel(item.metric_key) }}</td>
              <td>{{ item.is_required ? '예' : '아니오' }}</td>
              <td>{{ item.sort_order }}</td>
              <td class="text-end text-nowrap">
                <button type="button" class="btn btn-outline-secondary btn-sm me-1" @click="openItemEdit(item)">수정</button>
                <button type="button" class="btn btn-outline-danger btn-sm" @click="removeItem(item)">삭제</button>
              </td>
            </tr>
            <tr v-if="!items.length">
              <td colspan="7" class="text-center text-muted">입력 항목이 없습니다.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="text-muted">왼쪽에서 부서를 선택하세요.</p>
    </div>
  </div>
</template>
