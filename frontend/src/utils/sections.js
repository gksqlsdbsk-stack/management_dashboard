// 대시보드·리포트 표의 행 정의. `field`는 API 응답(03 §8.3)의 필드 이름이다.
// kind: 표시 형식 (money 원, qty 정수, percent %, decimal 소수 1자리), asField: 이월된 값의 기준 월 필드
export const SECTION_ROWS = {
  cost_profit: [
    { label: '매출액', kind: 'money', field: 'revenue' },
    { label: '재료비', kind: 'money', field: 'material_cost' },
    { label: '노무비', kind: 'money', field: 'labor_cost' },
    { label: '경비', kind: 'money', field: 'expense_cost' },
    { label: '총원가', kind: 'money', field: 'total_cost' },
    { label: '매출총이익', kind: 'money', field: 'gross_profit' },
    { label: '판매관리비', kind: 'money', field: 'sga_expense' },
    { label: '영업이익', kind: 'money', field: 'operating_profit' },
    { label: '매출총이익률', kind: 'percent', field: 'gross_margin' },
    { label: '영업이익률', kind: 'percent', field: 'operating_margin' },
  ],
  trade: [
    { label: '매출액', kind: 'money', field: 'revenue' },
    { label: '매입액', kind: 'money', field: 'purchase_amount' },
    { label: '수금액', kind: 'money', field: 'collection_amount' },
    { label: '미수금 잔액', kind: 'money', field: 'receivable_balance', asField: 'receivable_balance_as_of_month' },
    { label: '미수금 비율', kind: 'percent', field: 'receivable_ratio' },
  ],
  bep: [
    { label: '변동비', kind: 'money', field: 'variable_cost' },
    { label: '고정비', kind: 'money', field: 'fixed_cost' },
    { label: '공헌이익률', kind: 'percent', field: 'contribution_margin_ratio' },
    { label: 'BEP 매출액', kind: 'money', field: 'bep_revenue' },
    { label: 'BEP 달성률', kind: 'percent', field: 'bep_achievement_rate' },
  ],
  production: [
    { label: '생산량', kind: 'qty', field: 'production_qty' },
    { label: '생산 능력', kind: 'qty', field: 'production_capacity' },
    { label: '가동률', kind: 'percent', field: 'utilization_rate' },
  ],
  orders: [
    { label: '신규 수주액', kind: 'money', field: 'order_received' },
    { label: '수주 잔고', kind: 'money', field: 'order_backlog', asField: 'order_backlog_as_of_month' },
    { label: '파이프라인 금액', kind: 'money', field: 'pipeline_amount', asField: 'pipeline_amount_as_of_month' },
    { label: '예상 수주 확률', kind: 'percent', field: 'pipeline_win_rate', asField: 'pipeline_win_rate_as_of_month' },
    { label: '가중 파이프라인', kind: 'money', field: 'weighted_pipeline' },
  ],
  productivity: [
    { label: '인원수', kind: 'qty', field: 'headcount', asField: 'headcount_as_of_month' },
    { label: '인당 매출액', kind: 'money', field: 'revenue_per_head' },
    { label: '인당 영업이익', kind: 'money', field: 'operating_profit_per_head' },
    { label: '인당 생산량', kind: 'decimal', field: 'production_per_head' },
  ],
}

export const SECTION_TITLES = {
  cost_profit: '종합 원가/이익률',
  projects: '프로젝트별 원가/이익률',
  trade: '매입·매출·미수금',
  cash_forecast: '자금 수지 예측',
  bep: '손익분기점(BEP) 달성률',
  production: '생산량·공장 가동률',
  orders: '수주 잔고·영업 파이프라인',
  productivity: '인당 생산성',
  goals: '목표 대비 달성률',
}
