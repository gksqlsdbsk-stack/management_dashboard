"""초기 부서·입력 항목 [A-01, A-02]. 1회만 삽입하며 앱 시작 시 재생성하지 않는다.

안내 문구(input_guide, help_text)는 초안이며 관리자가 화면에서 수정한다 [A-08].
"""

from django.db import migrations

M, P = "MONTHLY", "PROJECT"

# (부서명, 부서 안내, [(항목명, 범위, 단위, 연동 키, 항목 안내), ...])
SEED = [
    (
        "영업",
        "당월 영업 실적을 입력합니다. 금액은 원 단위 숫자로 입력하고, '월말' 항목은 해당 월 마지막 날 기준 값을 입력하세요.",
        [
            ("프로젝트별 매출액", P, "원", "REVENUE", "당월 매출액을 프로젝트마다 한 줄씩 입력하세요. 프로젝트명은 생산 부서와 같게 적어야 원가와 합쳐집니다."),
            ("당월 수금액", M, "원", "COLLECTION_AMOUNT", "당월에 실제로 입금된 금액의 합계를 입력하세요."),
            ("미수금 잔액(월말)", M, "원", "RECEIVABLE_BALANCE", "월말 기준 아직 받지 못한 매출 대금의 합계를 입력하세요."),
            ("당월 신규 수주액", M, "원", "ORDER_RECEIVED", "당월에 새로 수주한 금액의 합계를 입력하세요."),
            ("수주 잔고(월말)", M, "원", "ORDER_BACKLOG", "월말 기준 수주했으나 아직 매출로 잡히지 않은 금액의 합계를 입력하세요."),
            ("영업 파이프라인 금액", M, "원", "PIPELINE_AMOUNT", "월말 기준 진행 중인 영업 기회의 예상 금액 합계를 입력하세요."),
            ("파이프라인 예상 수주 확률", M, "%", "PIPELINE_WIN_RATE", "파이프라인 전체의 예상 수주 확률을 0~100 사이 숫자로 입력하세요."),
            ("월말 인원수", M, "명", "HEADCOUNT", "월말 기준 부서 인원수를 입력하세요."),
        ],
    ),
    (
        "생산",
        "당월 생산·원가 실적을 입력합니다. 프로젝트별 항목은 프로젝트명과 금액을 한 줄씩 입력하고, 특정 프로젝트에 나눌 수 없는 비용은 프로젝트명을 '공통'으로 입력하세요.",
        [
            ("프로젝트별 재료비", P, "원", "MATERIAL_COST", "당월 프로젝트에 투입된 재료비를 프로젝트마다 한 줄씩 입력하세요."),
            ("프로젝트별 노무비", P, "원", "LABOR_COST", "당월 프로젝트에 투입된 노무비를 프로젝트마다 한 줄씩 입력하세요."),
            ("프로젝트별 경비", P, "원", "EXPENSE_COST", "당월 프로젝트에 발생한 경비를 프로젝트마다 한 줄씩 입력하세요."),
            ("생산량", M, "개", "PRODUCTION_QTY", "당월 총 생산 수량을 입력하세요."),
            ("생산 능력(월 최대 생산량)", M, "개", "PRODUCTION_CAPACITY", "당월 최대로 생산할 수 있는 수량을 입력하세요."),
            ("월말 인원수", M, "명", "HEADCOUNT", "월말 기준 부서 인원수를 입력하세요."),
        ],
    ),
    (
        "구매/자재",
        "당월 매입 실적을 입력합니다. 금액은 원 단위 숫자로 입력하세요.",
        [
            ("당월 매입액", M, "원", "PURCHASE_AMOUNT", "당월 매입(자재 구매 등) 금액의 합계를 입력하세요."),
            ("월말 인원수", M, "명", "HEADCOUNT", "월말 기준 부서 인원수를 입력하세요."),
        ],
    ),
    (
        "경영지원",
        "당월 판매관리비와 월말 자금 현황을 입력합니다. 금액은 원 단위 숫자로 입력하세요.",
        [
            ("당월 판매관리비", M, "원", "SGA_EXPENSE", "당월 판매관리비(인건비 외 관리 비용 포함)의 합계를 입력하세요."),
            ("월말 현금 잔액", M, "원", "CASH_BALANCE", "월말 기준 보유 현금과 예금의 합계를 입력하세요."),
            ("월말 인원수", M, "명", "HEADCOUNT", "월말 기준 부서 인원수를 입력하세요."),
        ],
    ),
]


def seed(apps, schema_editor):
    Department = apps.get_model("organization", "Department")
    InputItem = apps.get_model("organization", "InputItem")
    for dept_order, (dept_name, input_guide, items) in enumerate(SEED, start=1):
        department = Department.objects.create(name=dept_name, input_guide=input_guide, sort_order=dept_order)
        for item_order, (name, scope, unit, metric_key, help_text) in enumerate(items, start=1):
            InputItem.objects.create(
                department=department,
                name=name,
                scope=scope,
                unit=unit,
                metric_key=metric_key,
                help_text=help_text,
                is_required=True,
                sort_order=item_order,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0002_inputitem"),
    ]

    operations = [
        # 되돌려도 이미 쓰이고 있을 수 있는 데이터는 지우지 않는다
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
