"""지표 계산에 쓸 `SUBMITTED` 데이터를 월별로 집계해 `MonthFacts`로 만든다 [05 §1]."""

from django.db.models import Count, Sum

from reports.models import MonthlyReport, ReportValue

from .metrics import PROJECT_KEYS, MonthFacts


def load_facts(year, last_month):
    """`year`년 1월~`last_month`의 제출 완료 데이터. {월: MonthFacts} (모든 월 포함).

    - 임시 저장(DRAFT)은 제외한다 [A-25].
    - 비활성 항목·삭제된 부서의 과거 값도 포함한다 [A-06, A-50]. 연동 키가 없는 항목은 계산에 쓰지 않는다 [A-07].
    """
    facts = {month: MonthFacts(month=month) for month in range(1, last_month + 1)}
    reports = MonthlyReport.objects.filter(
        year=year, month__lte=last_month, status=MonthlyReport.Status.SUBMITTED
    )
    for month in reports.values_list("month", flat=True).distinct():
        facts[month].has_report = True

    values = ReportValue.objects.filter(
        report__year=year,
        report__month__lte=last_month,
        report__status=MonthlyReport.Status.SUBMITTED,
        item__metric_key__isnull=False,
    )
    for row in values.values("report__month", "item__metric_key").annotate(total=Sum("value"), n=Count("id")):
        month_facts = facts[row["report__month"]]
        month_facts.sums[row["item__metric_key"]] = row["total"]
        month_facts.counts[row["item__metric_key"]] = row["n"]

    project_values = (
        values.exclude(project_name="")
        .filter(item__metric_key__in=PROJECT_KEYS)
        .values("report__month", "project_name", "item__metric_key")
        .annotate(total=Sum("value"))
    )
    for row in project_values:
        project = facts[row["report__month"]].projects.setdefault(row["project_name"], {})
        project[row["item__metric_key"]] = row["total"]
    return facts
