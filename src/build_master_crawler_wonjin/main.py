from __future__ import annotations

import argparse
import html
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import gspread
import pandas as pd
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

KST = "Asia/Seoul"
SOURCE_DISPLAY = {
    "LH": "LH청약플러스",
    "i-SH": "SH인터넷청약시스템",
    "GH": "GH 토지분양시스템",
    "BMC": "부산도시공사",
    "UMCA": "울산도시공사",
    "DUDC": "대구도시개발공사",
    "DCCO": "대전도시공사",
    "SCTC": "세종도시교통공사",
    "JNDC": "전남개발공사",
}
SOURCE_BOARD_URL = {
    "LH": "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1062",
    "i-SH": "https://www.i-sh.co.kr/app/lay2/program/S48T561C564/www/brd/m_255/list.do?multi_itm_seq=8",
    "GH": "https://buy.gh.or.kr/land/svc/announce/land_announce_list.jsp?MenuId=SVC_ANN",
    "BMC": "https://www.bmc.busan.kr/board/list2.do?boardId=BBS_0000002&menuCd=DOM_000000101001002000&contentsSid=217&cpath=",
    "UMCA": "https://www.umca.co.kr/umca/bbs/list.do?bbsId=BBS_0000000000000003&mId=001001003000000000",
    "DUDC": "https://www.dudc.or.kr/ko/page.do?mnu_uid=101&appId=sale",
    "DCCO": "https://www.dcco.kr/web/board/list.do?mId=37&ts_categoryradio=1",
    "SCTC": "https://www.sctc.kr/bbs/BBSS2110052040247196",
    "JNDC": "https://www.jndc.co.kr/web/main/bbs/parcelout",
}
INDEX_TAB = "overall"
RUNLOG_TAB = "scheduler_run_logs"
SOURCE_TABS = {
    "LH": "LH",
    "i-SH": "iSH",
    "GH": "GH",
}
SOURCE_TAB_CATALOG = {
    **SOURCE_TABS,
    "BMC": "BMC",
    "UMCA": "UMCA",
    "DUDC": "DUDC",
    "DCCO": "DCCO",
    "SCTC": "SCTC",
    "JNDC": "JNDC",
}
ALLOWED_TABS = {INDEX_TAB, RUNLOG_TAB, "GUIDE", *SOURCE_TAB_CATALOG.values()}
DEFAULT_HOURLY_LOOKBACK_DAYS = 2
DEFAULT_BOOTSTRAP_DAYS = 365
PILOT_SOURCES = ("BMC", "UMCA", "DUDC", "DCCO", "SCTC", "JNDC")
DEFAULT_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "source_registry.json"


@dataclass(frozen=True)
class Notice:
    source: str
    notice_id: str
    raw_id_type: str
    raw_id_value: str
    id_sort_num: int
    title: str
    posted_at: str
    deadline_at: str
    status: str
    detail_url: str
    attachments: str
    area: str
    category: str
    views: str

    def key(self) -> tuple[str, str]:
        # Raw-coupled identity rule:
        # - never strip prefixes like BN-
        # - never cast to int for identity
        # - key is always source + raw id value
        return (self.source, self.raw_id_value)

    def to_row(self, collected_at_utc: str) -> list[str]:
        return [
            self.source,
            self.notice_id,
            self.raw_id_type,
            self.raw_id_value,
            self.id_sort_num,
            self.title,
            self.posted_at,
            self.deadline_at,
            self.status,
            self.detail_url,
            self.attachments,
            self.area,
            self.category,
            self.views,
            collected_at_utc,
        ]


def load_source_registry() -> list[dict[str, object]]:
    if not REGISTRY_PATH.exists():
        raise RuntimeError(f"Source registry is missing: {REGISTRY_PATH}")
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise RuntimeError("Source registry must contain a sources list")
    for source in sources:
        if not isinstance(source, dict) or not source.get("source_id"):
            raise RuntimeError("Every source registry entry needs a source_id")
        if source.get("enabled") is True and source.get("production_approved", True) is not True:
            raise RuntimeError(
                f"Source {source['source_id']} is enabled without production_approved=true"
            )
    return sources


def _parse_dot_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _clean_text(s: str) -> str:
    return " ".join((s or "").strip().split())


def _id_sort_num(source: str, raw_id: str) -> int:
    raw = (raw_id or "").strip()
    if not raw:
        return -1
    if source == "LH":
        m = re.search(r"(\d+)$", raw)
        return int(m.group(1)) if m else -1
    if source in ("i-SH", "GH"):
        digits = re.sub(r"\D", "", raw)
        return int(digits) if digits else -1
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else -1


def crawl_lh(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    session = requests.Session()
    url = "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1062"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    paging = soup.find("form", attrs={"name": "pagingForm"})
    payload = {}
    if paging:
        for inp in paging.select("input[name]"):
            payload[inp.get("name")] = inp.get("value", "")
    payload["mi"] = "1062"

    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    stop = False
    max_pages = 40

    for page in range(1, max_pages + 1):
        payload["currPage"] = str(page)
        r = session.post(
            "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do",
            data=payload,
            timeout=30,
        )
        r.raise_for_status()
        psoup = BeautifulSoup(r.text, "lxml")
        anchors = psoup.select("a.wrtancInfoBtn")
        if not anchors:
            break

        for a in anchors:
            tr = a.find_parent("tr")
            if tr is None:
                continue
            tds = tr.find_all("td")
            if len(tds) < 9:
                continue

            pan_id = a.get("data-id1", "")
            ccr = a.get("data-id2", "")
            upp = a.get("data-id3", "")
            ais = a.get("data-id4", "")
            title = _clean_text(a.get_text(" ", strip=True))
            area = _clean_text(tds[3].get_text(" ", strip=True)) if len(tds) > 3 else ""
            posted = _clean_text(tds[5].get_text(" ", strip=True)) if len(tds) > 5 else ""
            deadline = _clean_text(tds[6].get_text(" ", strip=True)) if len(tds) > 6 else ""
            status = _clean_text(tds[7].get_text(" ", strip=True)) if len(tds) > 7 else ""
            views = _clean_text(tds[8].get_text(" ", strip=True)) if len(tds) > 8 else ""

            pd = _parse_dot_date(posted)
            if pd and pd < from_date:
                stop = True
                continue

            notice_id = pan_id
            if not notice_id:
                continue
            key = ("LH", notice_id)
            if key in seen:
                continue
            seen.add(key)

            detail_url = (
                "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancInfo.do"
                f"?ccrCnntSysDsCd={ccr}&panId={pan_id}&uppAisTpCd={upp}&aisTpCd={ais}"
            )

            notices.append(
                Notice(
                    source="LH",
                    notice_id=notice_id,
                    raw_id_type="panId",
                    raw_id_value=notice_id,
                    id_sort_num=_id_sort_num("LH", notice_id),
                    title=title,
                    posted_at=posted,
                    deadline_at=deadline,
                    status=status,
                    detail_url=detail_url,
                    attachments="Y" if tr.select_one("a.listFileDown") else "",
                    area=area,
                    category="토지",
                    views=views,
                )
            )
            table_rows.append(
                {
                    "번호": _clean_text(tds[0].get_text(" ", strip=True)),
                    "구분": _clean_text(tds[1].get_text(" ", strip=True)),
                    "공고명": title,
                    "지역": area,
                    "첨부파일": "Y" if tr.select_one("a.listFileDown") else "",
                    "공고일": posted,
                    "마감일": deadline,
                    "상태": status,
                    "조회수": views,
                    "panId": pan_id,
                    "detail_url": detail_url,
                }
            )
        if stop:
            break
    return notices, table_rows


def crawl_ish(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    session = requests.Session()
    url = "https://www.i-sh.co.kr/app/lay2/program/S48T561C564/www/brd/m_255/list.do?multi_itm_seq=8"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    form = soup.find("form", attrs={"name": "mainform"})
    payload = {}
    if form:
        for inp in form.select("input[name]"):
            payload[inp.get("name")] = inp.get("value", "")
    payload["multi_itm_seq"] = payload.get("multi_itm_seq", "8") or "8"

    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    stop = False
    max_pages = 120

    for page in range(1, max_pages + 1):
        payload["page"] = str(page)
        r = session.post(
            "https://www.i-sh.co.kr/app/lay2/program/S48T561C564/www/brd/m_255/list.do",
            data=payload,
            timeout=30,
        )
        r.raise_for_status()
        psoup = BeautifulSoup(r.text, "lxml")
        anchors = psoup.select("a[onclick*='getDetailView']")
        if not anchors:
            break

        for a in anchors:
            tr = a.find_parent("tr")
            if tr is None:
                continue
            onclick = a.get("onclick", "")
            seq = ""
            if "getDetailView(" in onclick:
                seq = onclick.split("getDetailView(")[-1].split(")")[0].replace("'", "").strip()
            if not seq:
                continue

            tds = tr.find_all("td")
            posted = ""
            if tds:
                for td in reversed(tds):
                    txt = _clean_text(td.get_text(" ", strip=True))
                    if _parse_dot_date(txt):
                        posted = txt
                        break
            pd = _parse_dot_date(posted)
            if pd and pd < from_date:
                stop = True
                continue

            key = ("i-SH", seq)
            if key in seen:
                continue
            seen.add(key)

            title = _clean_text(a.get_text(" ", strip=True))
            detail_url = f"https://www.i-sh.co.kr/app/lay2/program/S48T561C564/www/brd/m_255/view.do?seq={seq}&multi_itm_seq=8"
            notices.append(
                Notice(
                    source="i-SH",
                    notice_id=seq,
                    raw_id_type="seq",
                    raw_id_value=seq,
                    id_sort_num=_id_sort_num("i-SH", seq),
                    title=title,
                    posted_at=posted,
                    deadline_at="",
                    status="",
                    detail_url=detail_url,
                    attachments="",
                    area="",
                    category="토지",
                    views="",
                )
            )
            if len(tds) >= 5:
                table_rows.append(
                    {
                        "번호": _clean_text(tds[0].get_text(" ", strip=True)),
                        "제목": title,
                        "담당부서": _clean_text(tds[2].get_text(" ", strip=True)),
                        "등록일": _clean_text(tds[3].get_text(" ", strip=True)),
                        "조회수": _clean_text(tds[4].get_text(" ", strip=True)),
                        "seq": seq,
                        "detail_url": detail_url,
                    }
                )
        if stop:
            break
    return notices, table_rows


def crawl_gh(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    session = requests.Session()
    base = "https://buy.gh.or.kr/land/svc/announce/land_announce_list.jsp?MenuId=SVC_ANN"
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    max_pages = 120
    stop = False

    for page in range(1, max_pages + 1):
        data = {"MenuId": "SVC_ANN", "strPageNo": str(page)}
        r = session.post(base, data=data, timeout=30)
        r.raise_for_status()
        r.encoding = "euc-kr"
        soup = BeautifulSoup(r.text, "lxml")
        rows = soup.select("tr.alignCenterHand")
        if not rows:
            break

        for tr in rows:
            a = tr.select_one("a[onclick*='goAnnounceView']")
            if not a:
                continue
            onclick = a.get("onclick", "")
            ann_seq = ""
            if "goAnnounceView(" in onclick:
                ann_seq = onclick.split("goAnnounceView(")[-1].split(")")[0].replace("'", "").strip()
            if not ann_seq:
                continue

            tds = tr.find_all("td")
            title = _clean_text(a.get_text(" ", strip=True))
            posted = ""
            deadline = ""
            status = ""
            views = ""
            no = ""
            if len(tds) >= 1:
                no = _clean_text(tds[0].get_text(" ", strip=True))
            if len(tds) >= 3:
                posted = _clean_text(tds[2].get_text(" ", strip=True))
            if len(tds) >= 4:
                deadline = _clean_text(tds[3].get_text(" ", strip=True))
            if len(tds) >= 5:
                status = _clean_text(tds[4].get_text(" ", strip=True))
            pd = _parse_dot_date(posted)
            if pd and pd < from_date:
                stop = True
                continue

            key = ("GH", ann_seq)
            if key in seen:
                continue
            seen.add(key)

            detail_url = f"https://buy.gh.or.kr/land/svc/announce/land_announce_view.jsp?annSeq={ann_seq}&MenuId=SVC_ANN"
            notices.append(
                Notice(
                    source="GH",
                    notice_id=ann_seq,
                    raw_id_type="annSeq",
                    raw_id_value=ann_seq,
                    id_sort_num=_id_sort_num("GH", ann_seq),
                    title=title,
                    posted_at=posted,
                    deadline_at=deadline,
                    status=status,
                    detail_url=detail_url,
                    attachments="",
                    area="",
                    category="토지",
                    views=views,
                )
            )
            table_rows.append(
                {
                    "번호": no,
                    "공고명": title,
                    "공고일": posted,
                    "마감일": deadline,
                    "상태": status,
                    "annSeq": ann_seq,
                    "detail_url": detail_url,
                }
            )
        if stop:
            break
    return notices, table_rows


def _date_from_row(tr: BeautifulSoup) -> str:
    """Return the last date-like cell in a board row."""
    for td in reversed(tr.find_all("td")):
        text = _clean_text(td.get_text(" ", strip=True))
        if _parse_dot_date(text):
            return text
    return ""


def _parse_ish_seoul_page(html: str) -> tuple[list[Notice], list[dict[str, str]]]:
    soup = BeautifulSoup(html, "lxml")
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    for a in soup.select("a[onclick*='getDetailView']"):
        tr = a.find_parent("tr")
        if tr is None:
            continue
        match = re.search(r"getDetailView\(['\"]([^'\"]+)", a.get("onclick", ""))
        seq = match.group(1).strip() if match else ""
        if not seq:
            continue
        tds = tr.find_all("td")
        posted = _date_from_row(tr)
        title = _clean_text(a.get_text(" ", strip=True))
        detail_url = (
            "https://www.i-sh.co.kr/main/lay2/program/S1T294C299/www/brd/m_255/view.do"
            f"?seq={seq}&multi_itm_seq=8"
        )
        notices.append(
            Notice(
                source="ISH_SEOUL_CANDIDATE",
                notice_id=seq,
                raw_id_type="seq",
                raw_id_value=seq,
                id_sort_num=_id_sort_num("i-SH", seq),
                title=title,
                posted_at=posted,
                deadline_at="",
                status="",
                detail_url=detail_url,
                attachments="Y" if tr.select_one("a[href*='download'], a[onclick*='download']") else "",
                area="서울",
                category="토지",
                views=_clean_text(tds[-1].get_text(" ", strip=True)) if tds else "",
            )
        )
        table_rows.append(
            {
                "번호": _clean_text(tds[0].get_text(" ", strip=True)) if tds else "",
                "제목": title,
                "등록일": posted,
                "seq": seq,
                "detail_url": detail_url,
            }
        )
    return notices, table_rows


def crawl_ish_seoul_pilot(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    session = requests.Session()
    session.headers.update(DEFAULT_BROWSER_HEADERS)
    list_url = "https://www.i-sh.co.kr/main/lay2/program/S1T294C299/www/brd/m_255/list.do?multi_itm_seq=8"
    resp = session.get(list_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    form = soup.find("form", attrs={"name": "mainform"})
    payload = {inp.get("name"): inp.get("value", "") for inp in form.select("input[name]")} if form else {}
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for page in range(1, 121):
        payload["page"] = str(page)
        r = session.post(list_url, data=payload, timeout=30)
        r.raise_for_status()
        page_notices, page_rows = _parse_ish_seoul_page(r.text)
        if not page_notices:
            break
        stop = False
        for notice, row in zip(page_notices, page_rows):
            posted_date = _parse_dot_date(notice.posted_at)
            if posted_date and posted_date < from_date:
                stop = True
                continue
            if notice.key() in seen:
                continue
            seen.add(notice.key())
            notices.append(notice)
            table_rows.append(row)
        if stop:
            break
    return notices, table_rows


def _parse_bmc_page(html: str) -> tuple[list[Notice], list[dict[str, str]]]:
    soup = BeautifulSoup(html, "lxml")
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    for tr in soup.select("table tbody tr"):
        a = tr.select_one("a[href*='view.do'][href*='dataSid=']")
        if a is None:
            continue
        query = parse_qs(urlparse(a.get("href", "")).query)
        data_sid = (query.get("dataSid") or [""])[0].strip()
        if not data_sid:
            continue
        title = _clean_text(a.get_text(" ", strip=True))
        posted = _date_from_row(tr)
        detail_url = urljoin("https://www.bmc.busan.kr", a.get("href", ""))
        tds = tr.find_all("td")
        views = _clean_text(tds[-1].get_text(" ", strip=True)) if tds else ""
        notices.append(
            Notice(
                source="BMC",
                notice_id=data_sid,
                raw_id_type="dataSid",
                raw_id_value=data_sid,
                id_sort_num=_id_sort_num("BMC", data_sid),
                title=title,
                posted_at=posted,
                deadline_at="",
                status="",
                detail_url=detail_url,
                attachments="Y" if tr.select_one("a[href*='file'], a[class*='file']") else "",
                area="부산",
                category="토지",
                views=views,
            )
        )
        table_rows.append(
            {
                "번호": _clean_text(tds[0].get_text(" ", strip=True)) if tds else "",
                "제목": title,
                "작성일": posted,
                "dataSid": data_sid,
                "detail_url": detail_url,
            }
        )
    return notices, table_rows


def crawl_bmc_pilot(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    session = requests.Session()
    session.headers.update(DEFAULT_BROWSER_HEADERS)
    base_url = "https://www.bmc.busan.kr/board/list2.do"
    params = {
        "boardId": "BBS_0000002",
        "menuCd": "DOM_000000101001002000",
        "contentsSid": "217",
        "cpath": "",
        "orderBy": "DATA_SID DESC",
        "paging": "ok",
    }
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for page in range(1, 41):
        params["startPage"] = str(page)
        r = session.get(base_url, params=params, timeout=30)
        r.raise_for_status()
        page_notices, page_rows = _parse_bmc_page(r.text)
        if not page_notices:
            break
        stop = False
        for notice, row in zip(page_notices, page_rows):
            posted_date = _parse_dot_date(notice.posted_at)
            if posted_date and posted_date < from_date:
                stop = True
                continue
            if notice.key() in seen:
                continue
            seen.add(notice.key())
            notices.append(notice)
            table_rows.append(row)
        if stop:
            break
    return notices, table_rows


def _parse_umca_page(html: str) -> tuple[list[Notice], list[dict[str, str]]]:
    soup = BeautifulSoup(html, "lxml")
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    for tr in soup.select("table tbody tr"):
        a = tr.select_one("a[onclick*='fn_view'], a[href*='dataId=']")
        if a is None:
            continue
        match = re.search(r"(?:fn_view\(['\"]|dataId=)(\d+)", a.get("onclick", "") + a.get("href", ""))
        data_id = match.group(1) if match else ""
        if not data_id:
            continue
        title = _clean_text(a.get_text(" ", strip=True))
        posted = _date_from_row(tr)
        detail_url = urljoin("https://www.umca.co.kr/umca/bbs/list.do", a.get("href", ""))
        tds = tr.find_all("td")
        notices.append(
            Notice(
                source="UMCA",
                notice_id=data_id,
                raw_id_type="dataId",
                raw_id_value=data_id,
                id_sort_num=_id_sort_num("UMCA", data_id),
                title=title,
                posted_at=posted,
                deadline_at="",
                status="",
                detail_url=detail_url,
                attachments="Y" if "첨부" in tr.get_text(" ", strip=True) else "",
                area="울산",
                category="토지",
                views=_clean_text(tds[2].get_text(" ", strip=True)) if len(tds) > 2 else "",
            )
        )
        table_rows.append(
            {
                "번호": _clean_text(tds[0].get_text(" ", strip=True)) if tds else "",
                "제목": title,
                "작성일": posted,
                "dataId": data_id,
                "detail_url": detail_url,
            }
        )
    return notices, table_rows


def crawl_umca_pilot(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    session = requests.Session()
    session.headers.update(DEFAULT_BROWSER_HEADERS)
    list_url = "https://www.umca.co.kr/umca/bbs/list.do?bbsId=BBS_0000000000000003&mId=001001003000000000"
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for page in range(1, 41):
        r = session.get(list_url, params={"page": page}, timeout=30)
        r.raise_for_status()
        page_notices, page_rows = _parse_umca_page(r.text)
        if not page_notices:
            break
        stop = False
        for notice, row in zip(page_notices, page_rows):
            posted_date = _parse_dot_date(notice.posted_at)
            if posted_date and posted_date < from_date:
                stop = True
                continue
            if notice.key() in seen:
                continue
            seen.add(notice.key())
            notices.append(notice)
            table_rows.append(row)
        if stop:
            break
    return notices, table_rows


def _parse_href_family_page(
    html: str,
    *,
    source: str,
    link_selector: str,
    id_pattern: str,
    raw_id_type: str,
    detail_base: str,
    area: str,
) -> tuple[list[Notice], list[dict[str, str]]]:
    soup = BeautifulSoup(html, "lxml")
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    for tr in soup.select("table tbody tr"):
        a = tr.select_one(link_selector)
        if a is None:
            continue
        link = a.get("href", "")
        match = re.search(id_pattern, link)
        raw_id = match.group(1).strip() if match else ""
        if not raw_id:
            continue
        title = _clean_text(a.get_text(" ", strip=True))
        posted = _date_from_row(tr)
        detail_url = urljoin(detail_base, link)
        tds = tr.find_all("td")
        views = _clean_text(tds[-1].get_text(" ", strip=True)) if tds else ""
        notices.append(
            Notice(
                source=source,
                notice_id=raw_id,
                raw_id_type=raw_id_type,
                raw_id_value=raw_id,
                id_sort_num=_id_sort_num(source, raw_id),
                title=title,
                posted_at=posted,
                deadline_at="",
                status="",
                detail_url=detail_url,
                attachments="Y" if tr.select_one("a[href*='file'], a[onclick*='file']") else "",
                area=area,
                category="토지",
                views=views,
            )
        )
        table_rows.append(
            {
                "번호": _clean_text(tds[0].get_text(" ", strip=True)) if tds else "",
                "제목": title,
                "작성일": posted,
                raw_id_type: raw_id,
                "detail_url": detail_url,
            }
        )
    return notices, table_rows


def _crawl_simple_family(
    *,
    source: str,
    url: str,
    params: dict[str, str],
    page_param: str,
    parser_kwargs: dict[str, str],
    from_date: date,
    max_pages: int = 40,
) -> tuple[list[Notice], list[dict[str, str]]]:
    session = requests.Session()
    session.headers.update(DEFAULT_BROWSER_HEADERS)
    notices: list[Notice] = []
    table_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for page in range(1, max_pages + 1):
        page_params = dict(params)
        page_params[page_param] = str(page)
        response = session.get(url, params=page_params, timeout=30)
        response.raise_for_status()
        page_notices, page_rows = _parse_href_family_page(response.text, **parser_kwargs)
        if not page_notices:
            break
        stop = False
        for notice, row in zip(page_notices, page_rows):
            posted_date = _parse_dot_date(notice.posted_at)
            if posted_date and posted_date < from_date:
                stop = True
                continue
            if notice.key() in seen:
                continue
            seen.add(notice.key())
            notices.append(notice)
            table_rows.append(row)
        if stop:
            break
    return notices, table_rows


def crawl_dudc(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    return _crawl_simple_family(
        source="DUDC",
        url="https://www.dudc.or.kr/ko/page.do",
        params={"mnu_uid": "101", "appId": "sale"},
        page_param="pageNo",
        parser_kwargs={
            "source": "DUDC",
            "link_selector": "a[href*='board_idx=']",
            "id_pattern": r"board_idx=(\d+)",
            "raw_id_type": "board_idx",
            "detail_base": "https://www.dudc.or.kr/ko/page.do",
            "area": "대구",
        },
        from_date=from_date,
    )


def crawl_dcco(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    return _crawl_simple_family(
        source="DCCO",
        url="https://www.dcco.kr/web/board/list.do",
        params={"mId": "37", "ts_categoryradio": "1"},
        page_param="pageIndex",
        parser_kwargs={
            "source": "DCCO",
            "link_selector": "a[href*='brdIdx=']",
            "id_pattern": r"brdIdx=(\d+)",
            "raw_id_type": "brdIdx",
            "detail_base": "https://www.dcco.kr/web/board/",
            "area": "대전",
        },
        from_date=from_date,
    )


def crawl_sctc(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    return _crawl_simple_family(
        source="SCTC",
        url="https://www.sctc.kr/bbs/BBSS2110052040247196",
        params={},
        page_param="page",
        parser_kwargs={
            "source": "SCTC",
            "link_selector": "a[href*='/bbs/view/']",
            "id_pattern": r"/(BBSW[^/?]+)/?",
            "raw_id_type": "bbs_id",
            "detail_base": "https://www.sctc.kr",
            "area": "세종",
        },
        from_date=from_date,
        max_pages=10,
    )


def crawl_jndc(from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    return _crawl_simple_family(
        source="JNDC",
        url="https://www.jndc.co.kr/web/main/bbs/parcelout",
        params={
            "sortOrder": "REG_DT",
            "sortDirection": "DESC",
            "bbsId": "parcelout",
            "pstNtcYn": "false",
        },
        page_param="cp",
        parser_kwargs={
            "source": "JNDC",
            "link_selector": "a[href*='/parcelout/']",
            "id_pattern": r"/parcelout/(\d+)",
            "raw_id_type": "post_id",
            "detail_base": "https://www.jndc.co.kr",
            "area": "전남",
        },
        from_date=from_date,
    )


def crawl_source(source_id: str, from_date: date) -> tuple[list[Notice], list[dict[str, str]]]:
    crawlers = {
        "LH": crawl_lh,
        "i-SH": crawl_ish,
        "GH": crawl_gh,
        "BMC": crawl_bmc_pilot,
        "UMCA": crawl_umca_pilot,
        "DUDC": crawl_dudc,
        "DCCO": crawl_dcco,
        "SCTC": crawl_sctc,
        "JNDC": crawl_jndc,
    }
    try:
        crawler = crawlers[source_id]
    except KeyError as exc:
        raise RuntimeError(f"No adapter is registered for source: {source_id}") from exc
    return crawler(from_date)


def to_df(records: Iterable[Notice]) -> pd.DataFrame:
    rows = [
        {
            "source": n.source,
            "notice_id": n.notice_id,
            "raw_id_type": n.raw_id_type,
            "raw_id_value": n.raw_id_value,
            "id_sort_num": n.id_sort_num,
            "title": n.title,
            "posted_at": n.posted_at,
            "deadline_at": n.deadline_at,
            "status": n.status,
            "detail_url": n.detail_url,
            "attachments": n.attachments,
            "area": n.area,
            "category": n.category,
            "views": n.views,
        }
        for n in records
    ]
    return pd.DataFrame(rows)


def _typed_df(rows: list[dict[str, str]], date_cols: list[str], int_cols: list[str]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", format="mixed")
    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_notices_from_xlsx(path: str) -> list[Notice]:
    x = pd.ExcelFile(path)
    out: list[Notice] = []

    if "LH" in x.sheet_names:
        df = pd.read_excel(path, sheet_name="LH")
        for _, row in df.iterrows():
            out.append(
                Notice(
                    source="LH",
                    notice_id=str(row.get("panId", "")).strip(),
                    raw_id_type="panId",
                    raw_id_value=str(row.get("panId", "")).strip(),
                    id_sort_num=_id_sort_num("LH", str(row.get("panId", "")).strip()),
                    title=str(row.get("공고명", "")).strip(),
                    posted_at="" if pd.isna(row.get("공고일")) else pd.to_datetime(row.get("공고일")).strftime("%Y-%m-%d"),
                    deadline_at="" if pd.isna(row.get("마감일")) else pd.to_datetime(row.get("마감일")).strftime("%Y-%m-%d"),
                    status=str(row.get("상태", "")).strip(),
                    detail_url=str(row.get("detail_url", "")).strip(),
                    attachments=str(row.get("첨부파일", "")).strip(),
                    area=str(row.get("지역", "")).strip(),
                    category=str(row.get("구분", "토지")).strip() or "토지",
                    views=str(row.get("조회수", "")).strip(),
                )
            )
    if "iSH" in x.sheet_names:
        df = pd.read_excel(path, sheet_name="iSH")
        for _, row in df.iterrows():
            out.append(
                Notice(
                    source="i-SH",
                    notice_id=str(row.get("seq", "")).strip(),
                    raw_id_type="seq",
                    raw_id_value=str(row.get("seq", "")).strip(),
                    id_sort_num=_id_sort_num("i-SH", str(row.get("seq", "")).strip()),
                    title=str(row.get("제목", "")).strip(),
                    posted_at="" if pd.isna(row.get("등록일")) else pd.to_datetime(row.get("등록일")).strftime("%Y-%m-%d"),
                    deadline_at="",
                    status="",
                    detail_url=str(row.get("detail_url", "")).strip(),
                    attachments="",
                    area="",
                    category="토지",
                    views=str(row.get("조회수", "")).strip(),
                )
            )
    if "GH" in x.sheet_names:
        df = pd.read_excel(path, sheet_name="GH")
        for _, row in df.iterrows():
            out.append(
                Notice(
                    source="GH",
                    notice_id=str(row.get("annSeq", "")).strip(),
                    raw_id_type="annSeq",
                    raw_id_value=str(row.get("annSeq", "")).strip(),
                    id_sort_num=_id_sort_num("GH", str(row.get("annSeq", "")).strip()),
                    title=str(row.get("공고명", "")).strip(),
                    posted_at="" if pd.isna(row.get("공고일")) else pd.to_datetime(row.get("공고일")).strftime("%Y-%m-%d"),
                    deadline_at="" if pd.isna(row.get("마감일")) else pd.to_datetime(row.get("마감일")).strftime("%Y-%m-%d"),
                    status=str(row.get("상태", "")).strip(),
                    detail_url=str(row.get("detail_url", "")).strip(),
                    attachments="",
                    area="",
                    category="토지",
                    views=str(row.get("조회수", "")).strip(),
                )
            )
    cleaned: list[Notice] = []
    seen: set[tuple[str, str]] = set()
    for r in out:
        if not r.notice_id:
            continue
        if r.key() in seen:
            continue
        seen.add(r.key())
        cleaned.append(r)
    return cleaned


def gsheet_client_from_env() -> gspread.Client:
    creds_raw = os.environ.get("GDRIVE_CREDS") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_raw:
        raise RuntimeError("Missing GDRIVE_CREDS or GOOGLE_SERVICE_ACCOUNT_JSON")
    creds_dict = json.loads(creds_raw)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def load_existing_keys(ws: gspread.Worksheet) -> set[tuple[str, str]]:
    vals = ws.get_all_values()
    if len(vals) <= 1:
        return set()

    header = vals[0]
    idx_source = 0
    idx_notice = 1
    idx_raw = 3
    if "source" in header:
        idx_source = header.index("source")
    if "notice_id" in header:
        idx_notice = header.index("notice_id")
    if "raw_id_value" in header:
        idx_raw = header.index("raw_id_value")

    out: set[tuple[str, str]] = set()
    for row in vals[1:]:
        if len(row) <= max(idx_source, idx_notice):
            continue
        src = row[idx_source].strip()
        if src == "source":
            continue
        raw = row[idx_raw].strip() if len(row) > idx_raw else ""
        # Backward compatibility: old seeded rows may be shifted and have posted_at in raw_id_value column.
        if _parse_dot_date(raw):
            raw = ""
        notice = row[idx_notice].strip()
        key_id = raw or notice
        if key_id in ("notice_id", "raw_id_value", "posted_at"):
            continue
        if src and key_id:
            out.add((src, key_id))
    return out


def _ensure_worksheet(
    sh: gspread.Spreadsheet,
    title: str,
    headers: list[str],
    *,
    create_if_missing: bool = False,
) -> gspread.Worksheet:
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        if not create_if_missing:
            raise RuntimeError(f"Required Google Sheet tab is missing: {title}")
        ws = sh.add_worksheet(title=title, rows=2000, cols=max(20, len(headers) + 2))
        ws.append_row(headers)
    return ws


def _validate_tab_names(index_tab: str, runlog_tab: str, source_tabs: dict[str, str]) -> None:
    used = [index_tab, runlog_tab, *source_tabs.values()]
    invalid = [name for name in used if name not in ALLOWED_TABS]
    if invalid:
        raise RuntimeError(
            "Invalid Google Sheet tab name(s): "
            + ", ".join(invalid)
            + f" | allowed={sorted(ALLOWED_TABS)}"
        )


def _open_sheet_from_env() -> gspread.Spreadsheet | None:
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        return None
    gc = gsheet_client_from_env()
    return gc.open_by_key(sheet_id)


def _get_last_run_kst_date(sh: gspread.Spreadsheet) -> date | None:
    try:
        ws = sh.worksheet(RUNLOG_TAB)
    except gspread.WorksheetNotFound:
        return None

    vals = ws.get_all_values()
    if len(vals) <= 1:
        return None

    header = vals[0]
    if "run_at_kst" not in header:
        return None
    idx = header.index("run_at_kst")

    for row in reversed(vals[1:]):
        if len(row) <= idx:
            continue
        raw = row[idx].strip()
        if not raw:
            continue
        try:
            return datetime.strptime(raw, "%Y-%m-%d %H:%M").date()
        except ValueError:
            continue
    return None


def resolve_from_date(
    explicit_from_date: str,
    mode: str,
    bootstrap_days: int,
    hourly_lookback_days: int,
) -> date:
    if explicit_from_date:
        return datetime.strptime(explicit_from_date, "%Y-%m-%d").date()

    today_kst = datetime.now(ZoneInfo(KST)).date()
    if mode == "bootstrap":
        return today_kst - timedelta(days=bootstrap_days)

    try:
        sh = _open_sheet_from_env()
    except Exception:
        sh = None

    if sh is not None:
        last_run_date = _get_last_run_kst_date(sh)
        if last_run_date is not None:
            # Dates on source boards are day-level, so keep a 1-day safety buffer.
            return last_run_date - timedelta(days=1)

    return today_kst - timedelta(days=hourly_lookback_days)


def sync_records_to_gsheet(
    records: list[Notice],
    dry_run: bool,
    source_ids: Iterable[str] | None = None,
) -> tuple[list[Notice], dict[str, str]]:
    run_utc = datetime.now(UTC).replace(microsecond=0)
    run_kst = run_utc.astimezone(ZoneInfo(KST))
    run_id = run_kst.strftime("%Y%m%d%H%M")
    meta = {
        "run_id": run_id,
        "run_at_kst": run_kst.strftime("%Y-%m-%d %H:%M"),
        "run_at_utc": run_utc.isoformat().replace("+00:00", "Z"),
    }

    if dry_run:
        return records, meta

    sh = _open_sheet_from_env()
    if sh is None:
        return records, meta

    index_tab = INDEX_TAB
    runlog_tab = RUNLOG_TAB
    requested_sources = list(source_ids or SOURCE_TABS.keys())
    source_tabs = {
        source_id: SOURCE_TAB_CATALOG[source_id]
        for source_id in requested_sources
        if source_id in SOURCE_TAB_CATALOG
    }
    _validate_tab_names(index_tab, runlog_tab, source_tabs)

    ws_index = _ensure_worksheet(
        sh,
        index_tab,
        [
            "source",
            "notice_id",
            "raw_id_type",
            "raw_id_value",
            "id_sort_num",
            "title",
            "posted_at",
            "deadline_at",
            "status",
            "detail_url",
            "attachments",
            "area",
            "category",
            "views",
            "first_seen_run_id",
            "first_seen_kst",
            "first_seen_utc",
        ],
    )
    ws_source = {
        src: _ensure_worksheet(
            sh,
            tab,
            [
                "source",
                "notice_id",
                "raw_id_type",
                "raw_id_value",
                "id_sort_num",
                "title",
                "posted_at",
                "deadline_at",
                "status",
                "detail_url",
                "attachments",
                "area",
                "category",
                "views",
                "run_id",
                "run_at_kst",
                "run_at_utc",
            ],
            create_if_missing=src not in SOURCE_TABS,
        )
        for src, tab in source_tabs.items()
    }
    metric_names = {"i-SH": "ish"}
    runlog_headers = [
        "run_id",
        "run_at_kst",
        "run_at_utc",
        "fetched_total",
        "new_total",
        *[
            f"fetched_{metric_names.get(source_id, source_id.lower().replace('-', '_'))}"
            for source_id in source_tabs
        ],
    ]
    ws_runlog = _ensure_worksheet(
        sh,
        runlog_tab,
        runlog_headers,
    )
    existing_runlog_headers = ws_runlog.row_values(1)
    if existing_runlog_headers:
        for column, header in enumerate(runlog_headers, start=1):
            if header not in existing_runlog_headers:
                ws_runlog.update_cell(1, column, header)

    # Build a global existing keyset from index + source archive tabs.
    existing = load_existing_keys(ws_index)
    for src in source_tabs:
        existing |= load_existing_keys(ws_source[src])
    # De-duplicate within this run first, then keep only keys not present in sheets.
    seen_in_run: set[tuple[str, str]] = set()
    unique_records: list[Notice] = []
    for r in records:
        k = r.key()
        if k in seen_in_run:
            continue
        seen_in_run.add(k)
        unique_records.append(r)

    new_records = [r for r in unique_records if r.key() not in existing]
    # Keep newest records at the top of tabs when writing to sheets.
    new_records = sorted(
        new_records,
        key=lambda x: (_parse_dot_date(x.posted_at) or date.min, x.id_sort_num, x.notice_id),
        reverse=True,
    )

    # Source archive should also store only newly discovered rows.
    if new_records:
        for src in source_tabs:
            src_rows = [r for r in new_records if r.source == src]
            if not src_rows:
                continue
            ws_source[src].insert_rows(
                [
                    [
                        r.source,
                        r.notice_id,
                        r.raw_id_type,
                        r.raw_id_value,
                        r.id_sort_num,
                        r.title,
                        r.posted_at,
                        r.deadline_at,
                        r.status,
                        r.detail_url,
                        r.attachments,
                        r.area,
                        r.category,
                        r.views,
                        meta["run_id"],
                        meta["run_at_kst"],
                        meta["run_at_utc"],
                    ]
                    for r in src_rows
                ],
                row=2,
                value_input_option="RAW",
            )

    if new_records:
        ws_index.insert_rows(
            [
                [
                    r.source,
                    r.notice_id,
                    r.raw_id_type,
                    r.raw_id_value,
                    r.id_sort_num,
                    r.title,
                    r.posted_at,
                    r.deadline_at,
                    r.status,
                    r.detail_url,
                    r.attachments,
                    r.area,
                    r.category,
                    r.views,
                    meta["run_id"],
                    meta["run_at_kst"],
                    meta["run_at_utc"],
                ]
                for r in new_records
            ],
            row=2,
            value_input_option="RAW",
        )

    counts = {src: 0 for src in source_tabs}
    for r in unique_records:
        counts[r.source] = counts.get(r.source, 0) + 1

    ws_runlog.append_row(
        [
            meta["run_id"],
            meta["run_at_kst"],
            meta["run_at_utc"],
            len(unique_records),
            len(new_records),
            *[counts.get(source_id, 0) for source_id in source_tabs],
        ],
        value_input_option="RAW",
    )
    return new_records, meta


def _telegram_post(token: str, chat_id: str, text: str, *, parse_mode: str = "HTML") -> None:
    for attempt in range(3):
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if response.status_code == 429 and attempt < 2:
            try:
                retry_after = int(response.json().get("parameters", {}).get("retry_after", 2))
            except (ValueError, TypeError, json.JSONDecodeError):
                retry_after = 2
            time.sleep(min(max(retry_after, 1), 30))
            continue
        response.raise_for_status()
        payload = response.json()
        if payload.get("ok") is not True:
            raise RuntimeError(f"Telegram API rejected message: {payload}")
        return
    raise RuntimeError("Telegram API rate limit retry exhausted")


def _chunk_telegram_lines(lines: list[str], max_chars: int = 3800) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        extra = len(line) + (1 if current else 0)
        if current and current_len + extra > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append("\n".join(current))
    return chunks or [""]


def send_telegram(records: list[Notice], dry_run: bool, run_meta: dict[str, str]) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if dry_run:
        return
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID for non-dry run")
    kst_now = datetime.now(ZoneInfo(KST))
    run_seq = kst_now.hour + 1
    run_time = run_meta.get("run_at_kst", kst_now.strftime("%Y-%m-%d %H:%M"))
    hour = kst_now.hour
    time_map = " ".join([f"[{h:02d}]" if h == hour else f"{h:02d}" for h in range(24)])

    header = (
        "<b>[크롤링 실행 알림]</b>\n"
        f"- 실행 회차: {run_seq}회\n"
        f"- 실행 시각: {run_time}\n"
        f"- 시간맵(현재): {time_map}\n"
        f"- 신규 건수: {len(records)}건"
    )
    _telegram_post(token, chat_id, header)

    lines: list[str] = ["<b>[크롤링 결과 요약]</b>", ""]
    if not records:
        lines.append("- 이번 실행 신규 게시물 없음")
        detail = "\n".join(lines).strip()
        _telegram_post(token, chat_id, detail)
        return

    for source in SOURCE_TAB_CATALOG:
        src_records = [r for r in records if r.source == source]
        if not src_records:
            continue
        src_records.sort(
            key=lambda x: (_parse_dot_date(x.posted_at) or date.min, x.id_sort_num, x.notice_id),
            reverse=True,
        )
        src_name = html.escape(SOURCE_DISPLAY.get(source, source))
        board_url = SOURCE_BOARD_URL.get(source, "")
        lines.append(f"<b>[{src_name}] 신규 {len(src_records)}건 (최신 5건)</b>")
        if board_url:
            lines.append(f"- 게시판 바로가기: <a href=\"{html.escape(board_url, quote=True)}\">[목록]</a>")
        for r in src_records[:5]:
            d = _parse_dot_date(r.posted_at)
            d_str = d.strftime("%m-%d") if d else "-"
            lines.append(
                f"- {html.escape(d_str)} | {html.escape(r.title)} | {src_name} | "
                f"<a href=\"{html.escape(r.detail_url, quote=True)}\">[열기]</a>"
            )
        lines.append("")

    for detail in _chunk_telegram_lines(lines):
        _telegram_post(token, chat_id, detail.strip())


def run(from_date: date, dry_run: bool, output_xlsx: str, include_pilots: bool = False) -> dict:
    registry = load_source_registry()
    enabled_sources = [
        str(item["source_id"])
        for item in registry
        if item.get("enabled") is True
    ]
    if include_pilots:
        if not dry_run:
            raise RuntimeError("Pilot sources are dry-run only until their Sheets tabs and alert contract are approved")
        enabled_sources.extend(source for source in PILOT_SOURCES if source not in enabled_sources)

    source_records: dict[str, list[Notice]] = {}
    source_rows: dict[str, list[dict[str, str]]] = {}
    for source_id in enabled_sources:
        records, rows = crawl_source(source_id, from_date)
        source_records[source_id] = records
        source_rows[source_id] = rows
    all_records = sorted(
        [record for records in source_records.values() for record in records],
        key=lambda x: (x.posted_at, x.source, x.notice_id),
    )

    out_path = output_xlsx.strip()
    if out_path:
        output_dir = os.path.dirname(out_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with pd.ExcelWriter(out_path, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
            source_export_specs = {
                "LH": (["공고일", "마감일"], ["번호", "조회수"]),
                "i-SH": (["등록일"], ["번호", "조회수", "seq"]),
                "GH": (["공고일", "마감일"], ["번호", "annSeq"]),
                "BMC": (["작성일"], ["번호", "조회수", "dataSid"]),
                "UMCA": (["작성일"], ["번호", "조회수", "dataId"]),
                "DUDC": (["작성일"], ["번호", "조회수", "board_idx"]),
                "DCCO": (["작성일"], ["번호", "조회수", "brdIdx"]),
                "SCTC": (["작성일"], ["번호", "조회수", "bbs_id"]),
                "JNDC": (["작성일"], ["번호", "조회수", "post_id"]),
            }
            for source_id, rows in source_rows.items():
                date_cols, int_cols = source_export_specs.get(source_id, ([], ["번호"]))
                _typed_df(rows, date_cols=date_cols, int_cols=int_cols).to_excel(
                    writer, sheet_name=SOURCE_TABS.get(source_id, source_id)[:31], index=False
                )

    new_records, run_meta = sync_records_to_gsheet(
        all_records,
        dry_run=dry_run,
        source_ids=enabled_sources,
    )
    send_telegram(new_records, dry_run=dry_run, run_meta=run_meta)

    return {
        "from_date": from_date.isoformat(),
        "counts": {**{source_id: len(records) for source_id, records in source_records.items()}, "ALL": len(all_records)},
        "new_count": len(new_records),
        "run_id": run_meta["run_id"],
        "run_at_kst": run_meta["run_at_kst"],
        "output_xlsx": out_path,
        "dry_run": dry_run,
        "include_pilots": include_pilots,
        "enabled_sources": enabled_sources,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Public notice crawler (LH/i-SH/GH)")
    parser.add_argument("--mode", choices=["hourly", "bootstrap"], default="hourly")
    parser.add_argument("--from-date", default="", help="YYYY-MM-DD")
    parser.add_argument("--bootstrap-days", type=int, default=DEFAULT_BOOTSTRAP_DAYS, help="bootstrap range in days")
    parser.add_argument(
        "--hourly-lookback-days",
        type=int,
        default=DEFAULT_HOURLY_LOOKBACK_DAYS,
        help="fallback hourly lookback in days when no prior run metadata exists",
    )
    parser.add_argument("--dry-run", action="store_true", help="skip sheets/telegram writes")
    parser.add_argument(
        "--include-pilots",
        action="store_true",
        help="crawl the selected pilot sources; requires --dry-run until Sheets tabs are approved",
    )
    parser.add_argument(
        "--seed-xlsx",
        default="",
        help="Seed gsheet index/archive from an existing workbook, then exit.",
    )
    parser.add_argument(
        "--output-xlsx",
        default="",
        help="optional local output workbook path",
    )
    args = parser.parse_args()

    fd = resolve_from_date(
        explicit_from_date=args.from_date,
        mode=args.mode,
        bootstrap_days=args.bootstrap_days,
        hourly_lookback_days=args.hourly_lookback_days,
    )

    if args.seed_xlsx:
        records = load_notices_from_xlsx(args.seed_xlsx)
        new_records, run_meta = sync_records_to_gsheet(records, dry_run=args.dry_run)
        result = {
            "seed_xlsx": args.seed_xlsx,
            "seed_total": len(records),
            "seed_new": len(new_records),
            "run_id": run_meta["run_id"],
            "run_at_kst": run_meta["run_at_kst"],
            "dry_run": args.dry_run,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    result = run(
        fd,
        dry_run=args.dry_run,
        output_xlsx=args.output_xlsx,
        include_pilots=args.include_pilots,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
