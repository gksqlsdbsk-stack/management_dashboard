import datetime
import io
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from accounts.models import User
from organization.models import Department, InputItem

from .models import MonthlyReport, ReportValue
from .tests import PREV_MONTH, PREV_YEAR, TODAY
from .upload import MAX_DATA_ROWS, MAX_FILE_SIZE, parse_decimal

HEADER = "항목명,프로젝트명,값\n"
# 06 §3 예시 (생산 부서)
SPEC_EXAMPLE = HEADER + (
    "프로젝트별 재료비,A프로젝트,1500000\n"
    "프로젝트별 재료비,B프로젝트,820000\n"
    "프로젝트별 노무비,A프로젝트,600000\n"
    "생산량,,320\n"
    "생산 능력(월 최대 생산량),,400\n"
)


def csv_file(text, name="upload.csv", bom=False):
    data = ("﻿" if bom else "") + text
    return SimpleUploadedFile(name, data.encode("utf-8"), content_type="text/csv")


def xlsx_file(rows, name="upload.xlsx", extra_sheet_rows=None):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    if extra_sheet_rows is not None:  # 두 번째 시트 (무시되어야 한다)
        second = workbook.create_sheet("두번째")
        for row in extra_sheet_rows:
            second.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="application/vnd.ms-excel")


class ParseDecimalTests(SimpleTestCase):
    def test_accepts_numbers(self):
        cases = {
            "1500000": "1500000.0000", "1,500,000": "1500000.0000", " 12.5 ": "12.5000", "-3": "-3.0000",
            "+3": "3.0000", "0": "0.0000", "1.50000": "1.5000", "0.0001": "0.0001",
            320: "320.0000", 12.5: "12.5000", Decimal("7.25"): "7.2500", 1e3: "1000.0000",
        }
        for raw, expected in cases.items():
            self.assertEqual(parse_decimal(raw), Decimal(expected), raw)

    def test_rejects_non_numbers(self):
        for raw in ["", "  ", "abc", "1500원", "₩1,000", "$5", "1e3", "NaN", "Infinity", "1,5", "12,34,567", ".5", "1.", "1 000", True, None, float("nan")]:
            with self.assertRaisesMessage(ValueError, "값이 숫자가 아닙니다."):
                parse_decimal(raw)

    def test_rejects_out_of_range(self):
        for raw in ["1.23456", "0.00001", "1" * 17, "9" * 30, 1e30, 0.30000000000000004]:
            with self.assertRaisesMessage(ValueError, "값이 허용 범위를 벗어났습니다."):
                parse_decimal(raw)

    def test_boundary_digits(self):
        self.assertEqual(parse_decimal("1" * 16), Decimal("1" * 16 + ".0000"))  # 정수 16자리 + 소수 4자리 = 20자리


class UploadTestCase(TestCase):
    def setUp(self):
        self.production = Department.objects.get(name="생산")
        self.sales = Department.objects.get(name="영업")
        self.admin = User.objects.create_user(username="A001", password="password1", name="대표", role=User.Role.ADMIN)
        self.emp = User.objects.create_user(username="P001", password="password1", name="홍길동", department=self.production)
        self.emp2 = User.objects.create_user(username="P002", password="password1", name="이생산", department=self.production)
        self.item = {i.name: i for i in InputItem.objects.filter(department=self.production)}
        self.client = APIClient()
        self.client.force_authenticate(user=self.emp)
        self.url = f"/api/my-report/{TODAY.year}/{TODAY.month}/upload/"

    def upload(self, file, url=None):
        return self.client.post(url or self.url, {"file": file}, format="multipart")

    def stored(self):
        return {(v.item.name, v.project_name): v.value for v in ReportValue.objects.select_related("item")}

    def assert_rows(self, response, expected):
        """행 오류 응답을 검증한다. expected: [(row, message), ...]"""
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["code"], "upload_invalid")
        self.assertEqual([(r["row"], r["message"]) for r in response.data["errors"]["rows"]], expected)
        self.assertEqual(ReportValue.objects.count(), 0)
        self.assertEqual(MonthlyReport.objects.count(), 0)

    def assert_file_error(self, response, fragment):
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["code"], "upload_invalid")
        self.assertEqual(response.data["errors"], {"rows": []})
        self.assertIn(fragment, response.data["detail"])
        self.assertEqual(MonthlyReport.objects.count(), 0)


class UploadSuccessTests(UploadTestCase):
    def test_spec_example_csv(self):
        response = self.upload(csv_file(SPEC_EXAMPLE))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["applied_count"], 5)
        report = response.data["report"]
        self.assertEqual(report["status"], "DRAFT")
        self.assertEqual(report["progress"], {"filled": 4, "required": 6, "percent": 66})
        self.assertEqual(len(report["values"]), 5)
        self.assertEqual(MonthlyReport.objects.get().status, "DRAFT")
        self.assertEqual(self.stored()[("프로젝트별 재료비", "B프로젝트")], 820000)
        # 화면이 쓰는 GET 본문과 같은 형태이며 새로 조회해도 동일하다
        get_url = self.url.replace("upload/", "")
        self.assertEqual(self.client.get(get_url).data["values"], report["values"])

    def test_spec_example_xlsx(self):
        rows = [
            ["항목명", "프로젝트명", "값"],
            ["프로젝트별 재료비", "A프로젝트", 1500000],
            ["프로젝트별 재료비", "B프로젝트", 820000],
            ["프로젝트별 노무비", "A프로젝트", 600000],
            ["생산량", None, 320],
            ["생산 능력(월 최대 생산량)", None, 400],
        ]
        response = self.upload(xlsx_file(rows))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["applied_count"], 5)
        self.assertEqual(response.data["report"]["progress"]["filled"], 4)
        self.assertEqual(self.stored()[("생산량", "")], 320)

    def test_csv_with_bom_crlf_reordered_columns_and_extra_column(self):
        text = "값,메모, 프로젝트명 ,항목명 \r\n320,비고,,생산량\r\n1500,,  A프로젝트 ,프로젝트별 재료비\r\n"
        response = self.upload(csv_file(text, bom=True))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.stored(), {("생산량", ""): 320, ("프로젝트별 재료비", "A프로젝트"): 1500})

    def test_thousand_separators_decimals_and_blank_rows(self):
        text = HEADER + '생산량,,"1,500,000"\n,,\n\n프로젝트별 재료비,A프로젝트,12.5\n  ,  ,  \n월말 인원수,,0\n'
        response = self.upload(csv_file(text))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["applied_count"], 3)
        self.assertEqual(self.stored()[("생산량", "")], 1500000)
        self.assertEqual(self.stored()[("프로젝트별 재료비", "A프로젝트")], Decimal("12.5"))
        self.assertEqual(self.stored()[("월말 인원수", "")], 0)

    def test_project_name_with_comma_and_trailing_spaces_in_names(self):
        response = self.upload(csv_file(HEADER + ' 프로젝트별 재료비 ,"A, B 프로젝트",100\n'))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn(("프로젝트별 재료비", "A, B 프로젝트"), self.stored())

    def test_xlsx_cell_types(self):
        rows = [
            ["항목명", "프로젝트명", "값"],
            ["프로젝트별 재료비", 2024, "1,500"],  # 숫자 프로젝트명, 콤마 문자열 값
            ["프로젝트별 노무비", "A", 12.5],
            ["생산량", None, 7.0],
        ]
        response = self.upload(xlsx_file(rows))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.stored(),
            {("프로젝트별 재료비", "2024"): 1500, ("프로젝트별 노무비", "A"): Decimal("12.5"), ("생산량", ""): 7},
        )

    def test_xlsx_reads_only_first_sheet(self):
        rows = [["항목명", "프로젝트명", "값"], ["생산량", None, 1]]
        garbage = [["항목명", "프로젝트명", "값"], ["없는항목", None, "abc"]]
        response = self.upload(xlsx_file(rows, extra_sheet_rows=garbage))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["applied_count"], 1)

    def test_file_names_are_case_insensitive(self):
        self.assertEqual(self.upload(csv_file(HEADER + "생산량,,1\n", name="DATA.CSV")).status_code, 200)

    def test_overwrites_same_keys_and_keeps_the_rest(self):
        self.client.put(
            self.url.replace("upload/", ""),
            {"values": [
                {"item_id": self.item["생산량"].id, "project_name": "", "value": 1},
                {"item_id": self.item["월말 인원수"].id, "project_name": "", "value": 9},
                {"item_id": self.item["프로젝트별 재료비"].id, "project_name": "A프로젝트", "value": 5},
            ]},
            format="json",
        )
        response = self.upload(csv_file(HEADER + "생산량,,320\n프로젝트별 재료비,B프로젝트,7\n"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["applied_count"], 2)  # 덮어쓴 1건 + 새로 만든 1건
        self.assertEqual(
            self.stored(),
            {("생산량", ""): 320, ("월말 인원수", ""): 9, ("프로젝트별 재료비", "A프로젝트"): 5, ("프로젝트별 재료비", "B프로젝트"): 7},
        )
        self.assertEqual(MonthlyReport.objects.count(), 1)
        self.assertEqual(ReportValue.objects.count(), 4)

    def test_values_of_inactive_items_are_kept(self):
        self.upload(csv_file(HEADER + "생산량,,1\n월말 인원수,,2\n"))
        headcount = self.item["월말 인원수"]
        headcount.is_active = False
        headcount.save()
        response = self.upload(csv_file(HEADER + "생산량,,5\n"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ReportValue.objects.filter(item=headcount, value=2).exists())

    def test_colleague_can_upload_to_the_same_report(self):
        self.upload(csv_file(HEADER + "생산량,,1\n"))
        self.client.force_authenticate(user=self.emp2)
        response = self.upload(csv_file(HEADER + "월말 인원수,,4\n"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MonthlyReport.objects.count(), 1)
        self.assertEqual(ReportValue.objects.count(), 2)

    def test_upload_targets_the_selected_month(self):
        url = f"/api/my-report/{PREV_YEAR}/{PREV_MONTH}/upload/"
        self.assertEqual(self.upload(csv_file(HEADER + "생산량,,1\n"), url).status_code, 200)
        report = MonthlyReport.objects.get()
        self.assertEqual((report.year, report.month), (PREV_YEAR, PREV_MONTH))

    def test_uploaded_full_report_can_be_submitted(self):
        text = SPEC_EXAMPLE + "프로젝트별 경비,A프로젝트,100\n월말 인원수,,12\n"
        self.assertEqual(self.upload(csv_file(text)).data["report"]["progress"]["percent"], 100)
        submit = self.client.post(self.url.replace("upload/", "submit/"))
        self.assertEqual(submit.status_code, 200)
        self.assertEqual(submit.data["status"], "SUBMITTED")

    def test_exactly_max_rows_with_blank_rows_is_allowed(self):
        lines = "".join(f"프로젝트별 재료비,P{n},1\n" for n in range(MAX_DATA_ROWS)) + "\n" * 500
        response = self.upload(csv_file(HEADER + lines))
        self.assertEqual(response.status_code, 200, response.data.get("detail"))
        self.assertEqual(response.data["applied_count"], MAX_DATA_ROWS)


class UploadRowErrorTests(UploadTestCase):
    def test_missing_headers(self):
        self.assert_rows(
            self.upload(csv_file("이름,수량\n생산량,1\n")),
            [(1, "헤더에 '항목명' 열이 없습니다."), (1, "헤더에 '프로젝트명' 열이 없습니다."), (1, "헤더에 '값' 열이 없습니다.")],
        )
        self.assert_rows(self.upload(csv_file("항목명,값\n생산량,1\n")), [(1, "헤더에 '프로젝트명' 열이 없습니다.")])

    def test_empty_file_reports_missing_headers(self):
        response = self.upload(csv_file(""))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data["errors"]["rows"]), 3)

    def test_unknown_item(self):
        self.assert_rows(
            self.upload(csv_file(HEADER + "생산량,,1\n기타비용,,5\n")), [(3, "3행: '기타비용' 항목을 찾을 수 없습니다.")]
        )

    def test_inactive_and_other_department_items_are_not_found(self):
        self.item["월말 인원수"].is_active = False
        self.item["월말 인원수"].save()
        self.assert_rows(
            self.upload(csv_file(HEADER + "월말 인원수,,1\n당월 수금액,,5\n")),
            [(2, "2행: '월말 인원수' 항목을 찾을 수 없습니다."), (3, "3행: '당월 수금액' 항목을 찾을 수 없습니다.")],
        )

    def test_item_name_must_match_exactly(self):
        self.assert_rows(
            self.upload(csv_file(HEADER + "생산 량,,1\n")), [(2, "2행: '생산 량' 항목을 찾을 수 없습니다.")]
        )

    def test_missing_item_name(self):
        self.assert_rows(self.upload(csv_file(HEADER + ",A프로젝트,5\n")), [(2, "2행: 항목명이 비어 있습니다.")])

    def test_project_name_rules_match_spec_messages(self):
        self.assert_rows(
            self.upload(csv_file(HEADER + "생산량,A프로젝트,1\n프로젝트별 재료비,,1\n프로젝트별 노무비,   ,1\n")),
            [
                (2, "2행: '생산량'은 프로젝트명을 입력하지 않는 항목입니다."),
                (3, "3행: '프로젝트별 재료비'는 프로젝트명이 필요합니다."),
                (4, "4행: '프로젝트별 노무비'는 프로젝트명이 필요합니다."),
            ],
        )

    def test_particle_fallback_for_names_ending_with_symbol(self):
        self.assert_rows(
            self.upload(csv_file(HEADER + "생산 능력(월 최대 생산량),A,1\n")),
            [(2, "2행: '생산 능력(월 최대 생산량)'은(는) 프로젝트명을 입력하지 않는 항목입니다.")],
        )

    def test_value_not_a_number(self):
        text = HEADER + "생산량,,\n생산량,,abc\n월말 인원수,,1500원\n프로젝트별 재료비,A,₩1000\n프로젝트별 노무비,A,1e3\n"
        self.assert_rows(
            self.upload(csv_file(text)),
            [(r, f"{r}행: 값이 숫자가 아닙니다.") for r in (2, 3, 4, 5, 6)],
        )

    def test_boolean_and_date_cells_in_xlsx(self):
        rows = [["항목명", "프로젝트명", "값"], ["생산량", None, True], ["월말 인원수", None, datetime.date(2026, 1, 1)]]
        self.assert_rows(
            self.upload(xlsx_file(rows)), [(2, "2행: 값이 숫자가 아닙니다."), (3, "3행: 값이 숫자가 아닙니다.")]
        )

    def test_duplicates_refer_to_the_first_row(self):
        text = HEADER + "생산량,,1\n프로젝트별 재료비,A,1\n생산량,,2\n프로젝트별 재료비, A ,3\n프로젝트별 재료비,B,4\n"
        self.assert_rows(
            self.upload(csv_file(text)),
            [(4, "4행: 2행과 중복된 항목입니다."), (5, "5행: 3행과 중복된 항목입니다.")],
        )

    def test_out_of_range_values(self):
        text = HEADER + f"생산량,,1.23456\n월말 인원수,,{'1' * 17}\n프로젝트별 재료비,A,1.50000\n"
        self.assert_rows(
            self.upload(csv_file(text)),
            [(2, "2행: 값이 허용 범위를 벗어났습니다."), (3, "3행: 값이 허용 범위를 벗어났습니다.")],
        )

    def test_project_name_too_long(self):
        self.assert_rows(
            self.upload(csv_file(HEADER + f"프로젝트별 재료비,{'가' * 101},1\n")), [(2, "2행: 프로젝트명이 너무 깁니다.")]
        )
        self.assertEqual(self.upload(csv_file(HEADER + f"프로젝트별 재료비,{'가' * 100},1\n")).status_code, 200)

    def test_multiple_errors_in_one_row_are_all_reported(self):
        response = self.upload(csv_file(HEADER + "생산량,A프로젝트,abc\n"))
        rows = response.data["errors"]["rows"]
        self.assertEqual([r["row"] for r in rows], [2, 2])
        self.assertEqual(response.data["detail"], "업로드 파일에 오류가 2건 있어 반영하지 않았습니다.")

    def test_one_bad_row_prevents_everything(self):
        self.client.put(self.url.replace("upload/", ""), {"values": [{"item_id": self.item["생산량"].id, "value": 7}]}, format="json")
        response = self.upload(csv_file(HEADER + "생산량,,320\n월말 인원수,,5\n기타,,1\n"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stored(), {("생산량", ""): 7})  # 기존 값 그대로, 새 값 미반영

    def test_xlsx_row_numbers_are_spreadsheet_rows(self):
        rows = [["항목명", "프로젝트명", "값"], ["생산량", None, 1], [None, None, None], ["기타", None, 1]]
        self.assert_rows(self.upload(xlsx_file(rows)), [(4, "4행: '기타' 항목을 찾을 수 없습니다.")])

    def test_rows_with_fewer_cells_than_header(self):
        self.assert_rows(self.upload(csv_file(HEADER + "생산량\n")), [(2, "2행: 값이 숫자가 아닙니다.")])


class UploadFileErrorTests(UploadTestCase):
    def test_no_file(self):
        self.assert_file_error(self.client.post(self.url, {}, format="multipart"), "파일을 선택")
        self.assert_file_error(self.client.post(self.url, {"file": "text"}, format="multipart"), "파일을 선택")
        self.assert_file_error(self.client.post(self.url, {"other": csv_file("a")}, format="multipart"), "파일을 선택")

    def test_json_body_is_not_a_file(self):
        self.assert_file_error(self.client.post(self.url, {"file": "x"}, format="json"), "파일을 선택")

    def test_unsupported_extensions(self):
        for name in ("data.xls", "data.txt", "data", "data.csv.exe", "data.xlsm"):
            self.assert_file_error(self.upload(csv_file(HEADER + "생산량,,1\n", name=name)), ".xlsx")

    def test_file_too_large(self):
        content = (HEADER + "생산량,,1\n").encode() + b" " * MAX_FILE_SIZE
        response = self.upload(SimpleUploadedFile("big.csv", content))
        self.assert_file_error(response, "5MB")

    def test_file_at_size_limit_is_read(self):
        head = (HEADER + "생산량,,1\n").encode()
        content = head + b"\n" * (MAX_FILE_SIZE - len(head))
        self.assertEqual(len(content), MAX_FILE_SIZE)
        self.assertEqual(self.upload(SimpleUploadedFile("edge.csv", content)).status_code, 200)

    def test_too_many_rows(self):
        lines = "".join(f"프로젝트별 재료비,P{n},1\n" for n in range(MAX_DATA_ROWS + 1))
        self.assert_file_error(self.upload(csv_file(HEADER + lines)), "1,000행")

    def test_non_utf8_csv(self):
        content = (HEADER + "생산량,,1\n").encode("cp949")
        self.assert_file_error(self.upload(SimpleUploadedFile("euckr.csv", content)), "UTF-8")

    def test_corrupt_xlsx(self):
        self.assert_file_error(self.upload(SimpleUploadedFile("broken.xlsx", b"this is not a zip file")), "읽을 수 없습니다")

    def test_header_only_and_blank_data_files(self):
        self.assert_file_error(self.upload(csv_file(HEADER)), "데이터 행이 없습니다")
        self.assert_file_error(self.upload(csv_file(HEADER + ",,\n\n")), "데이터 행이 없습니다")
        self.assert_file_error(self.upload(xlsx_file([["항목명", "프로젝트명", "값"]])), "데이터 행이 없습니다")

    def test_empty_xlsx(self):
        response = self.upload(xlsx_file([]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "upload_invalid")


class UploadAccessTests(UploadTestCase):
    def test_unauthenticated(self):
        response = APIClient().post(self.url, {"file": csv_file(SPEC_EXAMPLE)}, format="multipart")
        self.assertEqual(response.status_code, 401)

    def test_admin_is_forbidden(self):
        self.client.force_authenticate(user=self.admin)
        response = self.upload(csv_file(SPEC_EXAMPLE))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "forbidden")

    def test_employee_without_department(self):
        loner = User.objects.create_user(username="P900", password="password1", name="무소속")
        self.client.force_authenticate(user=loner)
        response = self.upload(csv_file(SPEC_EXAMPLE))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "forbidden")

    def test_future_month(self):
        url = f"/api/my-report/{TODAY.year + 1}/1/upload/"
        response = self.upload(csv_file(SPEC_EXAMPLE), url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "validation_error")

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_only_own_department_items_are_accepted(self):
        sales_emp = User.objects.create_user(username="S001", password="password1", name="김영업", department=self.sales)
        self.client.force_authenticate(user=sales_emp)
        response = self.upload(csv_file(HEADER + "생산량,,1\n"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["errors"]["rows"][0]["message"], "2행: '생산량' 항목을 찾을 수 없습니다.")
        self.assertEqual(self.upload(csv_file(HEADER + "당월 수금액,,1\n")).status_code, 200)


class UploadLockTests(UploadTestCase):
    def submit_full(self):
        text = SPEC_EXAMPLE + "프로젝트별 경비,A프로젝트,100\n월말 인원수,,12\n"
        self.upload(csv_file(text))
        self.client.post(self.url.replace("upload/", "submit/"))

    def test_upload_to_submitted_report_is_409(self):
        self.submit_full()
        before = self.stored()
        response = self.upload(csv_file(HEADER + "생산량,,999\n"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "report_locked")
        self.assertEqual(self.stored(), before)

    def test_lock_is_checked_before_file_validation(self):
        self.submit_full()
        for bad in (csv_file("이상한,파일\n"), SimpleUploadedFile("x.txt", b"x")):
            response = self.upload(bad)
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.data["code"], "report_locked")
        self.assertEqual(self.client.post(self.url).status_code, 409)  # 파일 없이도 잠금이 먼저

    def test_other_months_stay_open(self):
        self.submit_full()
        url = f"/api/my-report/{PREV_YEAR}/{PREV_MONTH}/upload/"
        self.assertEqual(self.upload(csv_file(HEADER + "생산량,,1\n"), url).status_code, 200)
