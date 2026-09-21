"""지표 연동 키 고정 목록 [A-07, 05 §2]. DB 테이블이 아니라 코드 상수다."""

# (key, 표시명, 단위, 집계 유형)
METRIC_KEYS = [
    ("REVENUE", "매출액", "원", "flow"),
    ("MATERIAL_COST", "재료비", "원", "flow"),
    ("LABOR_COST", "노무비", "원", "flow"),
    ("EXPENSE_COST", "경비", "원", "flow"),
    ("SGA_EXPENSE", "판매관리비", "원", "flow"),
    ("PURCHASE_AMOUNT", "매입액", "원", "flow"),
    ("COLLECTION_AMOUNT", "수금액", "원", "flow"),
    ("RECEIVABLE_BALANCE", "미수금 잔액", "원", "stock"),
    ("CASH_BALANCE", "현금 잔액", "원", "stock"),
    ("PRODUCTION_QTY", "생산량", "개", "flow"),
    ("PRODUCTION_CAPACITY", "생산 능력", "개", "flow"),
    ("HEADCOUNT", "인원수", "명", "stock"),
    ("ORDER_RECEIVED", "신규 수주액", "원", "flow"),
    ("ORDER_BACKLOG", "수주 잔고", "원", "stock"),
    ("PIPELINE_AMOUNT", "파이프라인 금액", "원", "stock"),
    ("PIPELINE_WIN_RATE", "예상 수주 확률", "%", "rate"),
]

METRIC_KEY_CHOICES = [(key, label) for key, label, _unit, _aggregation in METRIC_KEYS]
