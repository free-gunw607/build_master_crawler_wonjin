import unittest
from unittest.mock import patch

from build_master_crawler_wonjin.main import (
    _parse_bmc_page,
    _parse_href_family_page,
    _parse_ish_seoul_page,
    _parse_umca_page,
    _id_sort_num,
    Notice,
    send_telegram,
)


class PilotParserTests(unittest.TestCase):
    @patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"}, clear=False)
    @patch("build_master_crawler_wonjin.main.requests.post")
    def test_telegram_escapes_titles_and_supports_new_sources(self, post):
        response = post.return_value
        response.status_code = 200
        response.json.return_value = {"ok": True}
        record = Notice(
            source="BMC",
            notice_id="800544",
            raw_id_type="dataSid",
            raw_id_value="800544",
            id_sort_num=800544,
            title="<공급> & 안내",
            posted_at="2026.07.10",
            deadline_at="",
            status="",
            detail_url="https://example.com/detail?a=1&b=2",
            attachments="",
            area="부산",
            category="토지",
            views="",
        )
        send_telegram([record], dry_run=False, run_meta={"run_at_kst": "2026-07-14 04:00"})
        self.assertEqual(post.call_count, 2)
        detail_text = post.call_args_list[1].kwargs["data"]["text"]
        self.assertIn("&lt;공급&gt; &amp; 안내", detail_text)
        self.assertIn("부산도시공사", detail_text)

    def test_generic_numeric_ids_are_sortable(self):
        self.assertEqual(_id_sort_num("BMC", "800544"), 800544)
        self.assertEqual(_id_sort_num("UMCA", "4436"), 4436)

    def test_ish_seoul_parser_extracts_seq_and_date(self):
        html = """
        <table><tbody><tr>
          <td>416</td><td><a href='#' onclick="javascript:getDetailView('305531');return false;">토지 공급 공고</a></td>
          <td>분양부</td><td>2026-06-12</td><td>846</td>
        </tr></tbody></table>
        """
        notices, rows = _parse_ish_seoul_page(html)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].raw_id_value, "305531")
        self.assertEqual(notices[0].posted_at, "2026-06-12")
        self.assertIn("seq=305531", notices[0].detail_url)
        self.assertEqual(rows[0]["번호"], "416")

    def test_bmc_parser_extracts_data_sid_from_href(self):
        html = """
        <table><tbody><tr>
          <td>396</td>
          <td data-label='제목'><a href='/board/view.do?boardId=BBS_0000002&amp;dataSid=800544'>부산 공급공고</a></td>
          <td data-label='작성일'>2026.07.10</td><td>84</td>
        </tr></tbody></table>
        """
        notices, rows = _parse_bmc_page(html)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].raw_id_value, "800544")
        self.assertEqual(notices[0].posted_at, "2026.07.10")
        self.assertTrue(notices[0].detail_url.endswith("dataSid=800544"))
        self.assertEqual(rows[0]["dataSid"], "800544")

    def test_umca_parser_extracts_data_id_from_onclick(self):
        html = """
        <table><tbody><tr>
          <td>195</td>
          <td><a href='./view.do?dataId=4436' onclick="fn_view('4436');return false;">울산 공급공고</a></td>
          <td>112</td><td>2026-07-09</td>
        </tr></tbody></table>
        """
        notices, rows = _parse_umca_page(html)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].raw_id_value, "4436")
        self.assertEqual(notices[0].posted_at, "2026-07-09")
        self.assertIn("dataId=4436", notices[0].detail_url)
        self.assertEqual(rows[0]["번호"], "195")

    def test_href_family_parser_extracts_board_identifiers(self):
        html = """
        <table><tbody><tr>
          <td>1</td><td><a href='view.do?brdIdx=24800'>대전 공급 공고</a></td>
          <td>2026-07-10</td><td>36</td>
        </tr></tbody></table>
        """
        notices, rows = _parse_href_family_page(
            html,
            source="DCCO",
            link_selector="a[href*='brdIdx=']",
            id_pattern=r"brdIdx=(\d+)",
            raw_id_type="brdIdx",
            detail_base="https://www.dcco.kr/web/board/",
            area="대전",
        )
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].raw_id_value, "24800")
        self.assertEqual(rows[0]["brdIdx"], "24800")

    def test_legacy_div_board_parser_extracts_ids(self):
        html = """
        <div class='notice'><a href='/main/bbs/bbsMsgDetail.do?msg_seq=172&bcd=sale_lease'>
          검단 토지 공급공고</a><span>2026-07-10</span></div>
        <div class='notice'><a href='/zboard/read.do?pd_pkid=6799&lmCode=BBSMSTR_000000000028'>
          용지공급 적용이율 변경 안내</a><span>2026.07.09</span></div>
        """
        notices, _ = _parse_href_family_page(
            html,
            source="IH",
            link_selector="a[href*='bbsMsgDetail.do?']",
            id_pattern=r"(?:^|[?&])msg_seq=(\d+)",
            raw_id_type="msg_seq",
            detail_base="https://www.ih.co.kr",
            area="인천",
        )
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].raw_id_value, "172")
        self.assertEqual(notices[0].posted_at, "2026-07-10")

    def test_onclick_family_parser_builds_detail_url(self):
        html = """
        <table><tbody><tr>
          <td>1</td><td><a href='#none' onclick="goView('26064430')">충남 공급공고</a></td>
          <td>2026-07-09</td>
        </tr></tbody></table>
        """
        notices, _ = _parse_href_family_page(
            html,
            source="CNDC",
            link_selector="a[onclick*='goView']",
            id_pattern=r"goView\(['\"](\d+)",
            raw_id_type="pstSn",
            detail_base="https://www.cndc.kr",
            detail_url_template="https://www.cndc.kr/bbs/view.do?key=2404080038&pstSn={raw_id}",
            link_attribute="onclick",
            area="충남",
        )
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0].raw_id_value, "26064430")
        self.assertIn("pstSn=26064430", notices[0].detail_url)


if __name__ == "__main__":
    unittest.main()
