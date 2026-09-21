import csv
import io

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from .export import HEADER, INT, ONE, SECTION_ORDER, TREND_FIELDS, format_number, render_csv, safe_text
from .test_dashboard import PAST, DashboardTestCase, spec_example

SECTION_NAMES = [
    "데이터 상태", "종합 원가/이익률", "프로젝트별", "매입·매출·미수금", "자금 수지 예측", "BEP", "생산·가동률",
    "수주·파이프라인", "인당 생산성", "목표 달성률",
]


class FormatNumberTests(SimpleTestCase):
    def test_integers_round_half_away_from_zero(self):
        cases = {0.5: "1", 1.5: "2", 2.5: "3", -0.5: "-1", -2.5: "-3", 0.49: "0", -0.4: "0", 1234.5: "1235", -1234.5: "-1235"}
        for value, expected in cases.items():
            self.assertEqual(format_number(value, INT), expected, value)

    def test_one_decimal_round_half_away_from_zero(self):
        cases = {41.6667: "41.7", 12.25: "12.3", -12.25: "-12.3", 0.04: "0.0", -0.04: "0.0", 50: "50.0", 100 / 3: "33.3", 139.2857: "139.3"}
        for value, expected in cases.items():
            self.assertEqual(format_number(value, ONE), expected, value)

    def test_plain_notation_without_separators_or_exponent(self):
        self.assertEqual(format_number(10_800_000_000, INT), "10800000000")
        self.assertEqual(format_number(1.2e10, INT), "12000000000")
        self.assertEqual(format_number(10**19, INT), "10000000000000000000")
        self.assertEqual(format_number(-30_000_000, INT), "-30000000")
        self.assertEqual(format_number(1e-7, ONE), "0.0")

    def test_none_is_blank_and_zero_is_not(self):
        self.assertEqual(format_number(None, INT), "")
        self.assertEqual((format_number(0, INT), format_number(0, ONE), format_number(0.0, ONE)), ("0", "0.0", "0.0"))

    def test_float_is_rounded_by_its_exact_binary_value_like_the_screen(self):
        # 화면(JS toFixed)과 같다: 0.15 는 이진수로 0.1499999… 이므로 0.1, 0.25 는 정확히 0.25 이므로 0.3
        self.assertEqual(format_number(0.15, ONE), "0.1")
        self.assertEqual(format_number(0.25, ONE), "0.3")


class SafeTextTests(SimpleTestCase):
    def test_formula_prefixes_are_neutralized(self):
        for text in ("=1+1", "+1", "-1", "@SUM(A1)", "\t탭", "\r줄", '=HYPERLINK("http://x")', "-A프로젝트 (누적)"):
            self.assertEqual(safe_text(text), "'" + text, text)

    def test_normal_text_is_untouched(self):
        for text in ("", "A프로젝트", "누적", "1=1", "a-b", "'이미", "영업, 생산"):
            self.assertEqual(safe_text(text), text)


class RenderCsvTests(SimpleTestCase):
    def test_bom_crlf_header_and_quoting(self):
        content = render_csv([["섹션", "항목", "A, B", '따옴표"안', "줄\n바꿈"]])
        self.assertTrue(content.startswith("﻿".encode("utf-8")))
        text = content.decode("utf-8")
        self.assertTrue(text.startswith("﻿섹션,항목,구분,단위,값\r\n"))
        self.assertTrue(text.endswith("\r\n"))
        rows = list(csv.reader(io.StringIO(text.lstrip("﻿"), newline="")))
        self.assertEqual(rows[0], HEADER)
        self.assertEqual(rows[1], ["섹션", "항목", "A, B", '따옴표"안', "줄\n바꿈"])

    def test_decodes_with_utf8_sig(self):
        content = render_csv([["가", "나", "다", "라", "1"]])
        self.assertEqual(content.decode("utf-8-sig").splitlines()[0], "섹션,항목,구분,단위,값")

    def test_module_constants(self):
        self.assertEqual(HEADER, ["섹션", "항목", "구분", "단위", "값"])
        self.assertEqual(SECTION_ORDER[0], "data_status")
        self.assertEqual(set(TREND_FIELDS), {"cost_profit", "trade", "production", "orders", "productivity"})


class ExportTestCase(DashboardTestCase):
    def export(self, kind, month, year=PAST, extra="", **kwargs):
        return self.client.get(f"/api/{kind}/export/?year={year}&month={month}{extra}", **kwargs)

    def rows(self, kind, month, year=PAST, extra=""):
        response = self.export(kind, month, year, extra)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        text = response.content.decode("utf-8-sig")
        return list(csv.reader(io.StringIO(text, newline="")))

    def find(self, rows, section, item, category=None):
        return [r for r in rows[1:] if r[0] == section and r[1] == item and (category is None or r[2] == category)]

    def value(self, rows, section, item, category):
        (row,) = self.find(rows, section, item, category)
        return row[4]


class FileFormatTests(ExportTestCase):
    def test_headers_and_bom(self):
        spec_example(self, month=3)
        for kind, prefix in (("dashboard", "dashboard"), ("monthly-report", "monthly-report")):
            response = self.export(kind, 3)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
            self.assertEqual(response["Content-Disposition"], f'attachment; filename="{prefix}_{PAST}-03.csv"')
            self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(response.content.startswith("﻿섹션,항목,구분,단위,값\r\n".encode("utf-8")))

    def test_filename_pads_the_month(self):
        self.assertIn(f"dashboard_{PAST}-09.csv", self.export("dashboard", 9)["Content-Disposition"])
        self.assertIn(f"monthly-report_{PAST}-12.csv", self.export("monthly-report", 12)["Content-Disposition"])

    def test_every_row_has_five_columns_and_sections_are_in_order(self):
        spec_example(self, month=3)
        for kind in ("dashboard", "monthly-report"):
            rows = self.rows(kind, 3)
            self.assertEqual(rows[0], HEADER)
            self.assertTrue(all(len(row) == 5 for row in rows), kind)
            seen = []
            for row in rows[1:]:
                if row[0] not in seen:
                    seen.append(row[0])
            self.assertEqual(seen, SECTION_NAMES, kind)

    def test_accept_header_does_not_cause_406(self):
        response = self.export("dashboard", 1, HTTP_ACCEPT="text/csv")
        self.assertEqual(response.status_code, 200)
        error = self.client.get(f"/api/dashboard/export/?year={PAST}", HTTP_ACCEPT="text/csv")
        self.assertEqual(error.status_code, 400)
        self.assertEqual(error["Content-Type"], "application/json")


class DashboardCsvTests(ExportTestCase):
    def setUp(self):
        super().setUp()
        spec_example(self, month=1)
        self.rows_ = self.rows("dashboard", 1)

    def test_data_status_rows(self):
        self.assertEqual(self.find(self.rows_, "데이터 상태", "제출 부서"), [["데이터 상태", "제출 부서", f"{PAST}-01", "", "영업, 생산, 경영지원"]])
        self.assertEqual(self.find(self.rows_, "데이터 상태", "미제출 부서"), [["데이터 상태", "미제출 부서", f"{PAST}-01", "", "구매/자재"]])

    def test_cumulative_rows_match_the_spec_example(self):
        expected = {
            "매출액": ("원", "1000"), "재료비": ("원", "400"), "노무비": ("원", "200"), "경비": ("원", "50"), "총원가": ("원", "650"),
            "매출총이익": ("원", "350"), "판매관리비": ("원", "150"), "영업이익": ("원", "200"),
            "매출총이익률": ("%", "35.0"), "영업이익률": ("%", "20.0"),
        }
        for item, (unit, value) in expected.items():
            (row,) = self.find(self.rows_, "종합 원가/이익률", item, "누적")
            self.assertEqual((row[3], row[4]), (unit, value), item)
        self.assertEqual(self.value(self.rows_, "생산·가동률", "가동률", "누적"), "80.0")
        self.assertEqual(self.value(self.rows_, "BEP", "변동비", "누적"), "400")
        self.assertEqual(self.value(self.rows_, "BEP", "공헌이익률", "누적"), "60.0")
        self.assertEqual(self.value(self.rows_, "BEP", "BEP 매출액", "누적"), "667")
        self.assertEqual(self.value(self.rows_, "BEP", "BEP 달성률", "누적"), "150.0")
        self.assertEqual(self.value(self.rows_, "인당 생산성", "인당 매출액", "누적"), "100")
        self.assertEqual(self.value(self.rows_, "인당 생산성", "인당 생산량", "누적"), "8.0")
        self.assertEqual(self.find(self.rows_, "인당 생산성", "인당 생산량", "누적")[0][3], "개/명")
        self.assertEqual(self.find(self.rows_, "인당 생산성", "인원수", "누적")[0][3:], ["명", "10"])

    def test_no_month_columns_in_the_dashboard(self):
        categories = {row[2] for row in self.rows_[1:] if row[0] == "종합 원가/이익률"}
        self.assertIn("누적", categories)
        self.assertNotIn("당월", categories)

    def test_trend_rows_follow_the_cumulative_rows(self):
        spec_example(self, month=2)
        rows = self.rows("dashboard", 2)
        cost = [r for r in rows[1:] if r[0] == "종합 원가/이익률"]
        self.assertEqual([r[2] for r in cost[:10]], ["누적"] * 10)
        self.assertEqual([(r[1], r[2]) for r in cost[10:]], [
            ("매출액", f"{PAST}-01"), ("영업이익", f"{PAST}-01"), ("영업이익률", f"{PAST}-01"),
            ("매출액", f"{PAST}-02"), ("영업이익", f"{PAST}-02"), ("영업이익률", f"{PAST}-02"),
        ])
        self.assertEqual(self.value(rows, "종합 원가/이익률", "영업이익률", f"{PAST}-01"), "20.0")
        self.assertEqual(self.value(rows, "종합 원가/이익률", "매출액", f"{PAST}-01"), "1000")

    def test_trend_items_per_section(self):
        expected = {
            "매입·매출·미수금": ["매출액", "매입액", "미수금 잔액"], "생산·가동률": ["생산량", "가동률"],
            "수주·파이프라인": ["수주 잔고"], "인당 생산성": ["인당 매출액"],
        }
        for section, items in expected.items():
            trend = [r[1] for r in self.rows_[1:] if r[0] == section and r[2] == f"{PAST}-01"]
            self.assertEqual(trend, items, section)
        for section in ("BEP", "프로젝트별", "목표 달성률"):
            self.assertFalse([r for r in self.rows_[1:] if r[0] == section and r[2] == f"{PAST}-01"], section)

    def test_project_rows_use_the_project_name_as_category(self):
        rows = [r for r in self.rows_[1:] if r[0] == "프로젝트별"]
        self.assertEqual([r[1] for r in rows], ["매출액", "재료비", "노무비", "경비", "총원가", "매출총이익", "매출총이익률"])
        self.assertEqual({r[2] for r in rows}, {"A"})
        self.assertEqual([r[4] for r in rows], ["1000", "400", "200", "50", "650", "350", "35.0"])

    def test_goal_rows_are_three_per_metric(self):
        rows = [r for r in self.rows_[1:] if r[0] == "목표 달성률"]
        self.assertEqual(len(rows), 15)
        self.assertEqual([r[2] for r in rows[:3]], ["목표", "실적(누적)", "달성률"])
        self.assertEqual([r[1] for r in rows[::3]], ["매출액", "영업이익률", "가동률", "생산량", "신규 수주액"])
        self.assertEqual([r[3] for r in rows[:6]], ["원", "원", "%", "%", "%", "%"])
        self.assertEqual([r[4] for r in rows[:3]], ["", "1000", ""])  # 목표 미설정: 목표·달성률 빈 칸, 실적은 있음


class MonthlyReportCsvTests(ExportTestCase):
    def test_month_and_cumulative_pairs(self):
        spec_example(self, month=1)
        self.submit("영업", 2, [("프로젝트별 매출액", 500, "A"), ("프로젝트별 매출액", 200, "B")])
        rows = self.rows("monthly-report", 2)
        cost = [r for r in rows[1:] if r[0] == "종합 원가/이익률"]
        self.assertEqual(len(cost), 20)
        self.assertEqual([(r[1], r[2]) for r in cost[:4]], [("매출액", "당월"), ("매출액", "누적"), ("재료비", "당월"), ("재료비", "누적")])
        self.assertEqual((self.value(rows, "종합 원가/이익률", "매출액", "당월"), self.value(rows, "종합 원가/이익률", "매출액", "누적")), ("700", "1700"))
        self.assertFalse([r for r in cost if r[2].startswith("20")], "리포트에는 trend 행이 없다")
        for section in ("BEP", "생산·가동률", "인당 생산성"):
            self.assertEqual({r[2] for r in rows[1:] if r[0] == section}, {"당월", "누적"} | {r[2] for r in rows[1:] if r[0] == section and "기준" in r[2]})

    def test_project_rows_list_month_projects_then_cumulative_projects(self):
        spec_example(self, month=1)
        self.submit("영업", 2, [("프로젝트별 매출액", 500, "A"), ("프로젝트별 매출액", 200, "B")])
        rows = [r for r in self.rows("monthly-report", 2)[1:] if r[0] == "프로젝트별" and r[1] == "매출액"]
        self.assertEqual([(r[2], r[4]) for r in rows], [("A (당월)", "500"), ("B (당월)", "200"), ("A (누적)", "1500"), ("B (누적)", "200")])

    def test_dashboard_and_report_share_the_cash_and_goal_sections(self):
        for month in (7, 8, 9):
            self.submit("영업", month, [("당월 수금액", 100)])
            self.submit("경영지원", month, [("당월 판매관리비", 10), ("월말 현금 잔액", 100 + month)])
        dash = [r for r in self.rows("dashboard", 9)[1:] if r[0] in ("자금 수지 예측", "목표 달성률", "데이터 상태")]
        report = [r for r in self.rows("monthly-report", 9)[1:] if r[0] in ("자금 수지 예측", "목표 달성률", "데이터 상태")]
        self.assertEqual(dash, report)
        self.assertTrue(dash)


class StockCarryForwardCsvTests(ExportTestCase):
    """05 §5.2: 8월 영업 제출(미수금 500), 9월은 생산만 제출."""

    def setUp(self):
        super().setUp()
        self.submit("영업", 8, [("프로젝트별 매출액", 1000, "A"), ("미수금 잔액(월말)", 500)])
        self.submit("생산", 9, [("생산량", 10)])

    def test_as_of_suffix_on_carried_values(self):
        dash = self.rows("dashboard", 9)
        self.assertEqual(self.value(dash, "매입·매출·미수금", "미수금 잔액", "누적(8월 기준)"), "500")
        self.assertFalse(self.find(dash, "매입·매출·미수금", "미수금 잔액", "누적"))
        self.assertEqual(self.value(dash, "매입·매출·미수금", "매출액", "누적"), "1000")  # flow 에는 붙지 않는다
        report = self.rows("monthly-report", 9)
        self.assertEqual(self.value(report, "매입·매출·미수금", "미수금 잔액", "당월(8월 기준)"), "500")
        self.assertEqual(self.value(report, "매입·매출·미수금", "미수금 잔액", "누적(8월 기준)"), "500")
        self.assertEqual(self.value(report, "매입·매출·미수금", "미수금 비율", "당월"), "")  # 분모 0

    def test_trend_rows_have_no_suffix_and_blank_when_missing(self):
        dash = self.rows("dashboard", 9)
        self.assertEqual(self.value(dash, "매입·매출·미수금", "미수금 잔액", f"{PAST}-08"), "500")
        self.assertEqual(self.value(dash, "매입·매출·미수금", "미수금 잔액", f"{PAST}-09"), "")
        self.assertEqual(self.value(dash, "매입·매출·미수금", "매출액", f"{PAST}-05"), "")  # 제출 없는 달

    def test_no_suffix_when_the_value_is_from_the_base_month(self):
        self.submit("영업", 9, [("미수금 잔액(월말)", 700)])
        dash = self.rows("dashboard", 9)
        self.assertEqual(self.value(dash, "매입·매출·미수금", "미수금 잔액", "누적"), "700")

    def test_no_suffix_when_there_is_no_value_at_all(self):
        dash = self.rows("dashboard", 9)
        self.assertEqual(self.value(dash, "수주·파이프라인", "수주 잔고", "누적"), "")


class CashForecastCsvTests(ExportTestCase):
    def setUp(self):
        super().setUp()
        for month in (7, 8, 9):
            self.submit("영업", month, [("당월 수금액", 100)])
            self.submit("구매/자재", month, [("당월 매입액", 100)])
            self.submit("생산", month, [("프로젝트별 노무비", 30, "A"), ("프로젝트별 경비", 10, "A")])
            values = [("당월 판매관리비", 10)]
            if month == 9:
                values.append(("월말 현금 잔액", 120))
            self.submit("경영지원", month, values)

    def test_summary_history_and_forecast_rows(self):
        rows = [r for r in self.rows("dashboard", 9)[1:] if r[0] == "자금 수지 예측"]
        self.assertEqual(rows[:4], [
            ["자금 수지 예측", "기준 현금 잔액", "기준 월", "원", "120"],
            ["자금 수지 예측", "참조 개월 수", "참조 기간", "개월", "3"],
            ["자금 수지 예측", "월평균 유입", "참조 기간 평균", "원", "100"],
            ["자금 수지 예측", "월평균 유출", "참조 기간 평균", "원", "150"],
        ])
        history = rows[4:13]
        self.assertEqual([r[2] for r in history], [f"{PAST}-{m:02d}" for m in range(1, 10)])
        self.assertEqual({r[1] for r in history}, {"현금 잔액(실적)"})
        self.assertEqual([r[4] for r in history], [""] * 8 + ["120"])
        forecast = rows[13:]
        self.assertEqual(len(forecast), 12)  # 3개월 × 4항목
        self.assertEqual([(r[1], r[2], r[4]) for r in forecast[:8]], [
            ("예상 유입", f"{PAST}-10", "100"), ("예상 유출", f"{PAST}-10", "150"), ("순현금흐름", f"{PAST}-10", "-50"), ("예상 잔액", f"{PAST}-10", "70"),
            ("예상 유입", f"{PAST}-11", "100"), ("예상 유출", f"{PAST}-11", "150"), ("순현금흐름", f"{PAST}-11", "-50"), ("예상 잔액", f"{PAST}-11", "20"),
        ])
        self.assertEqual(forecast[-1], ["자금 수지 예측", "예상 잔액", f"{PAST}-12", "원", "-30"])

    def test_negative_numbers_are_not_quoted_as_text(self):
        content = self.export("dashboard", 9).content.decode("utf-8-sig")
        self.assertIn(f"자금 수지 예측,예상 잔액,{PAST}-12,원,-30\r\n", content)
        self.assertNotIn("'-30", content)

    def test_horizon_controls_the_number_of_months(self):
        rows = [r for r in self.rows("dashboard", 9, extra="&horizon=5")[1:] if r[0] == "자금 수지 예측" and r[1] == "예상 잔액"]
        self.assertEqual([r[2] for r in rows], [f"{PAST}-10", f"{PAST}-11", f"{PAST}-12", f"{PAST + 1}-01", f"{PAST + 1}-02"])

    def test_year_rollover_labels(self):
        for month in (10, 11):
            self.submit("영업", month, [("당월 수금액", 100)])
        rows = [r for r in self.rows("dashboard", 11)[1:] if r[0] == "자금 수지 예측" and r[1] == "예상 유입"]
        self.assertEqual([r[2] for r in rows], [f"{PAST}-12", f"{PAST + 1}-01", f"{PAST + 1}-02"])

    def test_carried_base_cash_is_marked(self):
        InputCash = "월말 현금 잔액"
        from organization.models import InputItem
        from reports.models import MonthlyReport, ReportValue

        report = MonthlyReport.objects.get(department=self.dept["경영지원"], year=PAST, month=9)
        ReportValue.objects.filter(report=report, item=InputItem.objects.get(name=InputCash)).delete()
        self.submit("경영지원", 6, [(InputCash, 300)])
        rows = self.rows("dashboard", 9)
        self.assertEqual(self.value(rows, "자금 수지 예측", "기준 현금 잔액", "기준 월(6월 기준)"), "300")

    def test_no_reference_months_leaves_blanks_but_keeps_the_structure(self):
        rows = [r for r in self.rows("dashboard", 5)[1:] if r[0] == "자금 수지 예측"]
        self.assertEqual(rows[1], ["자금 수지 예측", "참조 개월 수", "참조 기간", "개월", "0"])
        self.assertEqual(rows[2][4:], [""])
        self.assertEqual(len([r for r in rows if r[1] == "예상 잔액"]), 3)
        self.assertEqual({r[4] for r in rows if r[1] in ("예상 유입", "예상 유출", "예상 잔액")}, {""})


class BlankAndInjectionTests(ExportTestCase):
    def test_period_without_data_has_the_same_structure_with_blank_values(self):
        spec_example(self, month=3)
        full = self.rows("dashboard", 3)
        empty = self.rows("dashboard", 2, year=PAST - 1)  # 제출이 전혀 없는 해
        self.assertTrue(all(len(r) == 5 for r in empty))
        numeric_rows = [r for r in empty[1:] if r[0] not in ("데이터 상태", "프로젝트별")]
        self.assertTrue(numeric_rows)
        self.assertEqual({r[4] for r in numeric_rows if r[1] != "참조 개월 수"}, {""})
        self.assertEqual([r for r in empty[1:] if r[0] == "프로젝트별"], [])
        self.assertEqual(self.find(empty, "데이터 상태", "미제출 부서")[0][4], "영업, 생산, 구매/자재, 경영지원")
        self.assertEqual(len(full[0]), 5)

    def test_project_names_that_look_like_formulas_are_neutralized(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 100, '=HYPERLINK("http://evil","x")'), ("프로젝트별 매출액", 50, "-A"), ("프로젝트별 매출액", 10, "@B"), ("프로젝트별 매출액", 5, "정상")])
        content = self.export("dashboard", 1).content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(content, newline="")))
        categories = {r[2] for r in rows[1:] if r[0] == "프로젝트별"}
        self.assertEqual(categories, {"'=HYPERLINK(\"http://evil\",\"x\")", "'-A", "'@B", "정상"})
        for row in rows[1:]:
            for cell in row[:4]:
                self.assertFalse(cell.startswith(("=", "+", "-", "@", "\t", "\r")), row)
        report = self.rows("monthly-report", 1)
        self.assertIn("'-A (당월)", {r[2] for r in report[1:] if r[0] == "프로젝트별"})

    def test_numeric_negative_values_stay_numeric(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 100, "A")])
        self.submit("생산", 1, [("프로젝트별 재료비", 300, "A")])
        rows = self.rows("dashboard", 1)
        self.assertEqual(self.value(rows, "종합 원가/이익률", "매출총이익", "누적"), "-200")
        self.assertEqual(self.value(rows, "종합 원가/이익률", "매출총이익률", "누적"), "-200.0")

    def test_project_name_with_comma_and_quote_roundtrips(self):
        self.submit("영업", 1, [("프로젝트별 매출액", 100, 'A, "특수" 프로젝트')])
        rows = self.rows("dashboard", 1)
        self.assertIn('A, "특수" 프로젝트', {r[2] for r in rows[1:] if r[0] == "프로젝트별"})


class ExportParamTests(ExportTestCase):
    URLS = ("/api/dashboard/export/", "/api/monthly-report/export/")

    def test_same_validation_as_the_json_endpoints(self):
        for base in self.URLS:
            for query in ("", f"?year={PAST}", "?month=1", f"?year=abc&month=1", f"?year={PAST}&month=0", f"?year={PAST}&month=13", f"?year=0&month=1", f"?year={PAST}&month=1&horizon=2", f"?year={PAST}&month=1&horizon=7", f"?year={PAST}&month=1&horizon=abc"):
                response = self.client.get(base + query)
                self.assertEqual(response.status_code, 400, base + query)
                self.assertEqual(response.data["code"], "validation_error")
                self.assertEqual(response["Content-Type"], "application/json")

    def test_future_month_is_rejected(self):
        from .test_dashboard import TODAY, YEAR

        next_year, next_month = (YEAR + 1, 1) if TODAY.month == 12 else (YEAR, TODAY.month + 1)
        for base in self.URLS:
            self.assertEqual(self.client.get(f"{base}?year={next_year}&month={next_month}").status_code, 400)
            self.assertEqual(self.client.get(f"{base}?year={YEAR}&month={TODAY.month}").status_code, 200)

    def test_permissions(self):
        for base in self.URLS:
            url = f"{base}?year={PAST}&month=1"
            self.assertEqual(APIClient().get(url).status_code, 401)
            self.client.force_authenticate(user=self.emp)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "forbidden")
            self.assertEqual(response["Content-Type"], "application/json")
            self.client.force_authenticate(user=self.admin)

    def test_post_is_not_allowed(self):
        for base in self.URLS:
            self.assertEqual(self.client.post(f"{base}?year={PAST}&month=1").status_code, 405)

    def test_export_reflects_the_same_numbers_as_the_json_api(self):
        spec_example(self, month=1)
        self.submit("영업", 2, [("프로젝트별 매출액", 333, "A"), ("프로젝트별 매출액", 111, "B")])
        self.submit("생산", 2, [("프로젝트별 재료비", 77, "A"), ("생산량", 7), ("생산 능력(월 최대 생산량)", 9)])
        data = self.dashboard(2).data
        rows = self.rows("dashboard", 2)
        rounded = lambda v, k: "" if v is None else (f"{v:.1f}" if k == "one" else str(int(v + 0.5)))
        cost = data["cost_profit"]["cumulative"]
        for item, field, kind in (("매출액", "revenue", "int"), ("영업이익", "operating_profit", "int"), ("영업이익률", "operating_margin", "one")):
            self.assertEqual(self.value(rows, "종합 원가/이익률", item, "누적"), rounded(cost[field], kind), item)
        self.assertEqual(self.value(rows, "생산·가동률", "가동률", "누적"), rounded(data["production"]["cumulative"]["utilization_rate"], "one"))
        for point in data["cost_profit"]["trend"]:
            self.assertEqual(self.value(rows, "종합 원가/이익률", "매출액", f"{PAST}-{point['month']:02d}"), rounded(point["revenue"], "int"))
