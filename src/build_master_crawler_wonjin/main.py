from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Iterable

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
}
SOURCE_BOARD_URL = {
    "LH": "https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWrtancList.do?mi=1062",
    "i-SH": "https://www.i-sh.co.kr/app/lay2/program/S48T561C564/www/brd/m_255/list.do?multi_itm_seq=8",
    "GH": "https://buy.gh.or.kr/land/svc/announce/land_announce_list.jsp?MenuId=SVC_ANN",
}


@dataclass(frozen=True)
class Notice:
    source: str
    notice_id: str
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
        return (self.source, self.notice_id)

    def to_row(self, collected_at_utc: str) -> list[str]:
        return [
            self.source,
            self.notice_id,
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


def to_df(records: Iterable[Notice]) -> pd.DataFrame:
    rows = [
        {
            "source": n.source,
            "notice_id": n.notice_id,
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
    out: set[tuple[str, str]] = set()
    for row in vals[1:]:
        if len(row) < 2:
            continue
        src, nid = row[0].strip(), row[1].strip()
        if src and nid:
            out.add((src, nid))
    return out


def _ensure_worksheet(sh: gspread.Spreadsheet, title: str, headers: list[str]) -> gspread.Worksheet:
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=2000, cols=max(20, len(headers) + 2))
        ws.append_row(headers)
    return ws


def sync_records_to_gsheet(records: list[Notice], dry_run: bool) -> tuple[list[Notice], dict[str, str]]:
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

    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        return records, meta

    index_tab = os.environ.get("GOOGLE_SHEET_INDEX_TAB", "overall").strip()
    runlog_tab = os.environ.get("GOOGLE_SHEET_RUNLOG_TAB", "scheduler_run_logs").strip()
    source_tabs = {
        "LH": os.environ.get("GOOGLE_SHEET_TAB_LH", "LH").strip(),
        "i-SH": os.environ.get("GOOGLE_SHEET_TAB_ISH", "iSH").strip(),
        "GH": os.environ.get("GOOGLE_SHEET_TAB_GH", "GH").strip(),
    }

    gc = gsheet_client_from_env()
    sh = gc.open_by_key(sheet_id)

    ws_index = _ensure_worksheet(
        sh,
        index_tab,
        [
            "source",
            "notice_id",
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
        )
        for src, tab in source_tabs.items()
    }
    ws_runlog = _ensure_worksheet(
        sh,
        runlog_tab,
        [
            "run_id",
            "run_at_kst",
            "run_at_utc",
            "fetched_total",
            "new_total",
            "fetched_lh",
            "fetched_ish",
            "fetched_gh",
        ],
    )

    existing = load_existing_keys(ws_index)
    new_records = [r for r in records if r.key() not in existing]

    if records:
        for src in ("LH", "i-SH", "GH"):
            src_rows = [r for r in records if r.source == src]
            if not src_rows:
                continue
            ws_source[src].append_rows(
                [
                    [
                        r.source,
                        r.notice_id,
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
                value_input_option="RAW",
            )

    if new_records:
        ws_index.append_rows(
            [
                [
                    r.source,
                    r.notice_id,
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
            value_input_option="RAW",
        )

    counts = {"LH": 0, "i-SH": 0, "GH": 0}
    for r in records:
        counts[r.source] = counts.get(r.source, 0) + 1

    ws_runlog.append_row(
        [
            meta["run_id"],
            meta["run_at_kst"],
            meta["run_at_utc"],
            len(records),
            len(new_records),
            counts.get("LH", 0),
            counts.get("i-SH", 0),
            counts.get("GH", 0),
        ],
        value_input_option="RAW",
    )
    return new_records, meta


def send_telegram(records: list[Notice], dry_run: bool, run_meta: dict[str, str]) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if dry_run or not token or not chat_id:
        return
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
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": header, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=30,
    )

    lines: list[str] = ["<b>[크롤링 결과 요약]</b>", ""]
    if not records:
        lines.append("- 이번 실행 신규 게시물 없음")
        detail = "\n".join(lines).strip()
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": detail, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=30,
        )
        return

    for source in ("LH", "i-SH", "GH"):
        src_records = [r for r in records if r.source == source]
        if not src_records:
            continue
        src_records.sort(
            key=lambda x: (_parse_dot_date(x.posted_at) or date.min, x.notice_id),
            reverse=True,
        )
        src_name = SOURCE_DISPLAY[source]
        board_url = SOURCE_BOARD_URL[source]
        lines.append(f"<b>[{src_name}] 신규 {len(src_records)}건 (최신 5건)</b>")
        lines.append(f"- 게시판 바로가기: <a href=\"{board_url}\">[목록]</a>")
        for r in src_records[:5]:
            d = _parse_dot_date(r.posted_at)
            d_str = d.strftime("%m-%d") if d else "-"
            lines.append(
                f"- {d_str} | {r.title} | {src_name} | "
                f"<a href=\"{r.detail_url}\">[열기]</a>"
            )
        lines.append("")

    detail = "\n".join(lines).strip()
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": detail, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=30,
    )


def run(from_date: date, dry_run: bool, output_xlsx: str) -> dict:
    lh, lh_rows = crawl_lh(from_date)
    ish, ish_rows = crawl_ish(from_date)
    gh, gh_rows = crawl_gh(from_date)
    all_records = sorted(lh + ish + gh, key=lambda x: (x.posted_at, x.source, x.notice_id))

    out_path = output_xlsx
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl", datetime_format="yyyy-mm-dd") as writer:
        _typed_df(lh_rows, date_cols=["공고일", "마감일"], int_cols=["번호", "조회수"]).to_excel(
            writer, sheet_name="LH", index=False
        )
        _typed_df(ish_rows, date_cols=["등록일"], int_cols=["번호", "조회수", "seq"]).to_excel(
            writer, sheet_name="iSH", index=False
        )
        _typed_df(gh_rows, date_cols=["공고일", "마감일"], int_cols=["번호", "annSeq"]).to_excel(
            writer, sheet_name="GH", index=False
        )

    new_records, run_meta = sync_records_to_gsheet(all_records, dry_run=dry_run)
    send_telegram(new_records, dry_run=dry_run, run_meta=run_meta)

    return {
        "from_date": from_date.isoformat(),
        "counts": {"LH": len(lh), "iSH": len(ish), "GH": len(gh), "ALL": len(all_records)},
        "new_count": len(new_records),
        "run_id": run_meta["run_id"],
        "run_at_kst": run_meta["run_at_kst"],
        "output_xlsx": out_path,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Public notice crawler (LH/i-SH/GH)")
    parser.add_argument("--from-date", default="", help="YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=365, help="fallback range in days")
    parser.add_argument("--dry-run", action="store_true", help="skip sheets/telegram writes")
    parser.add_argument(
        "--seed-xlsx",
        default="",
        help="Seed gsheet index/archive from an existing workbook, then exit.",
    )
    parser.add_argument(
        "--output-xlsx",
        default=f"output/notices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        help="local output workbook path",
    )
    args = parser.parse_args()

    if args.from_date:
        fd = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    else:
        fd = date.today() - timedelta(days=args.days)

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

    result = run(fd, dry_run=args.dry_run, output_xlsx=args.output_xlsx)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
