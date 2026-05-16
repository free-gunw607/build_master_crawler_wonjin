from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from io import StringIO
from typing import Iterable

import gspread
import pandas as pd
import requests
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials

KST = "Asia/Seoul"


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


def append_new_rows_to_sheet(records: list[Notice], dry_run: bool) -> list[Notice]:
    if dry_run:
        return records

    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    tab = os.environ.get("GOOGLE_SHEET_TAB", "notices_raw").strip()
    if not sheet_id:
        return records

    gc = gsheet_client_from_env()
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=1000, cols=20)
        ws.append_row(
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
                "collected_at_utc",
            ]
        )

    existing = load_existing_keys(ws)
    now_utc = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    new_records = [r for r in records if r.key() not in existing]
    if new_records:
        ws.append_rows([r.to_row(now_utc) for r in new_records], value_input_option="RAW")
    return new_records


def send_telegram(records: list[Notice], dry_run: bool) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if dry_run or not token or not chat_id:
        return
    if not records:
        return

    lines = [
        f"[공고 크롤링] 신규 {len(records)}건",
        "",
    ]
    for i, r in enumerate(records[:30], start=1):
        lines.append(f"{i}. ({r.source}) {r.title}")
        lines.append(f"- 공고일: {r.posted_at} | 링크: {r.detail_url}")
    if len(records) > 30:
        lines.append(f"... 외 {len(records)-30}건")

    payload = {"chat_id": chat_id, "text": "\n".join(lines)}
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, timeout=30)


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

    new_records = append_new_rows_to_sheet(all_records, dry_run=dry_run)
    send_telegram(new_records, dry_run=dry_run)

    return {
        "from_date": from_date.isoformat(),
        "counts": {"LH": len(lh), "iSH": len(ish), "GH": len(gh), "ALL": len(all_records)},
        "new_count": len(new_records),
        "output_xlsx": out_path,
        "dry_run": dry_run,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Public notice crawler (LH/i-SH/GH)")
    parser.add_argument("--from-date", default="", help="YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=365, help="fallback range in days")
    parser.add_argument("--dry-run", action="store_true", help="skip sheets/telegram writes")
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

    result = run(fd, dry_run=args.dry_run, output_xlsx=args.output_xlsx)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
