"""연간 목표 지표 키 5개 [A-35, 02 §2.6]. 지표 연동 키(organization.metric_keys)와는 별개다."""

# (key, 표시명, 단위)
GOAL_METRICS = [
    ("REVENUE", "매출액", "원"),
    ("OPERATING_MARGIN", "영업이익률", "%"),
    ("UTILIZATION", "가동률", "%"),
    ("PRODUCTION_QTY", "생산량", "개"),
    ("ORDER_RECEIVED", "신규 수주액", "원"),
]

GOAL_METRIC_CHOICES = [(key, label) for key, label, _unit in GOAL_METRICS]
