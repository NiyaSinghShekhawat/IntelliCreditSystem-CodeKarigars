from config import (
    GDELT_API_URL, GDELT_MAX_RECORDS, GDELT_TIMESPAN_DAYS,
    NEGATIVE_KEYWORDS, INDIAN_NEWS_DOMAINS, DEBUG_MODE
)
from src.schemas import ResearchFindings, NewsItem
from typing import List
import requests
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


class ResearchAgent:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (IntelliCredit Research Agent)"
        })
        print("Research Agent ready.")

    def research(self, company_name: str,
                 promoter_name: str = "") -> ResearchFindings:
        print(f"Researching: {company_name}")
        findings = ResearchFindings(company_name=company_name)

        # print("  Searching news (GDELT)...")
        # news_items = self._search_gdelt(company_name)
        # if promoter_name:
        #     news_items.extend(self._search_gdelt(promoter_name))
        print("  Searching news (Google News + GDELT)...")
        # Try Google News first (more reliable)
        news_items = self._search_google_news(company_name)

        # Search for specific risk categories
        risk_queries = [
            f"{company_name} fraud OR scam OR arrest",
            f"{company_name} GST violation OR notice OR penalty",
            f"{company_name} court case OR FIR OR defaulter",
        ]
        positive_queries = [
            f"{company_name} new project OR expansion OR contract",
            f"{company_name} award OR certification OR export",
        ]

        for q in risk_queries:
            news_items.extend(self._search_google_news(q))
        for q in positive_queries:
            news_items.extend(self._search_google_news(q))

        # Also try promoter name
        if promoter_name:
            news_items.extend(self._search_google_news(promoter_name))

        # Fallback to GDELT if Google News got nothing
        if not news_items:
            print("  Google News empty, trying GDELT...")
            news_items = self._search_gdelt(company_name)
            if promoter_name:
                news_items.extend(self._search_gdelt(promoter_name))

        # Deduplicate by title
        seen_titles = set()
        unique_items = []
        for item in news_items:
            if item.title not in seen_titles:
                seen_titles.add(item.title)
                unique_items.append(item)
        news_items = unique_items

        for item in news_items:
            if item.is_negative:
                findings.negative_news.append(item)
            else:
                findings.positive_news.append(item)

        total_news = len(news_items)
        neg_count = len(findings.negative_news)
        if total_news > 0:
            findings.news_risk_score = round((neg_count / total_news) * 10, 1)

        print("  Checking MCA filings...")
        findings.mca_charges = self._check_mca(company_name)

        print("  Checking e-Courts...")
        findings.litigation_details = self._check_ecourts(company_name)
        findings.litigation_found = len(findings.litigation_details) > 0

        print("  Checking RBI/SEBI...")
        findings.rbi_sebi_actions = self._check_rbi_sebi(company_name)

        findings.research_summary = self._build_summary(findings)

        print(f"  Research complete: {neg_count} negative news, "
              f"litigation={findings.litigation_found}")
        return findings

    def research_with_mock(self, company_name: str,
                           risk_level: str = "medium") -> ResearchFindings:
        findings = ResearchFindings(company_name=company_name)

        if risk_level == "low":
            findings.negative_news = []
            findings.positive_news = [
                NewsItem(
                    title=f"{company_name} wins export order worth Rs 12 Cr",
                    url="https://economictimes.com",
                    date="20240115",
                    source="economictimes.indiatimes.com",
                    is_negative=False,
                    keywords_found=[]
                ),
                NewsItem(
                    title=f"{company_name} receives ISO 9001 certification",
                    url="https://business-standard.com",
                    date="20240210",
                    source="business-standard.com",
                    is_negative=False,
                    keywords_found=[]
                )
            ]
            findings.news_risk_score = 1.0
            findings.litigation_found = False
            findings.litigation_details = []
            findings.mca_charges = []
            findings.rbi_sebi_actions = []

        elif risk_level == "high":
            findings.negative_news = [
                NewsItem(
                    title=f"{company_name} under ED investigation for fraud",
                    url="https://economictimes.com",
                    date="20240301",
                    source="economictimes.indiatimes.com",
                    is_negative=True,
                    keywords_found=["fraud", "investigation"]
                ),
                NewsItem(
                    title=f"{company_name} directors arrested in GST scam",
                    url="https://livemint.com",
                    date="20240215",
                    source="livemint.com",
                    is_negative=True,
                    keywords_found=["arrest", "scam"]
                ),
                NewsItem(
                    title=f"{company_name} declared wilful defaulter by SBI",
                    url="https://moneycontrol.com",
                    date="20240110",
                    source="moneycontrol.com",
                    is_negative=True,
                    keywords_found=["wilful defaulter", "NPA"]
                )
            ]
            findings.positive_news = []
            findings.news_risk_score = 8.5
            findings.litigation_found = True
            findings.litigation_details = [
                "Civil suit filed by HDFC Bank — Rs 2.3 Cr recovery",
                "Criminal complaint under IPC 420 — cheating",
                "GST tribunal case — disputed ITC of Rs 85 Lakhs"
            ]
            findings.mca_charges = [
                {
                    "type": "Unsatisfied Charge",
                    "source": "MCA21",
                    "details": "Charge of Rs 5 Cr in favour of Axis Bank",
                    "risk_level": "High"
                }
            ]
            findings.rbi_sebi_actions = [
                f"RBI penalty of Rs 10 Lakh imposed on {company_name} "
                f"for KYC violations — Jan 2024"
            ]

        else:
            findings.negative_news = [
                NewsItem(
                    title=f"{company_name} faces GST notice for ITC mismatch",
                    url="https://economictimes.com",
                    date="20240201",
                    source="economictimes.indiatimes.com",
                    is_negative=True,
                    keywords_found=["GST"]
                )
            ]
            findings.positive_news = [
                NewsItem(
                    title=f"{company_name} reports 15% revenue growth in Q3",
                    url="https://business-standard.com",
                    date="20240115",
                    source="business-standard.com",
                    is_negative=False,
                    keywords_found=[]
                )
            ]
            findings.news_risk_score = 3.5
            findings.litigation_found = False
            findings.litigation_details = []
            findings.mca_charges = []
            findings.rbi_sebi_actions = []

        findings.research_summary = self._build_summary(findings)
        return findings

    def _search_gdelt(self, query: str) -> List[NewsItem]:
        items = []
        try:
            params = {
                "query": f'"{query}" sourcelang:eng',
                "mode": "artlist",
                "maxrecords": GDELT_MAX_RECORDS,
                "timespan": f"{GDELT_TIMESPAN_DAYS}d",
                "format": "json",
                "sort": "datedesc"
            }
            response = self.session.get(
                GDELT_API_URL, params=params, timeout=10
            )
            if response.status_code != 200:
                return items
            data = response.json()
            for article in data.get("articles", []):
                title = article.get("title", "")
                title_lower = title.lower()
                found_keywords = [
                    kw for kw in NEGATIVE_KEYWORDS if kw in title_lower
                ]
                items.append(NewsItem(
                    title=title,
                    url=article.get("url", ""),
                    date=article.get("seendate", "")[:8],
                    source=article.get("domain", ""),
                    is_negative=len(found_keywords) > 0,
                    keywords_found=found_keywords
                ))
        except requests.exceptions.Timeout:
            print("  GDELT timeout — skipping news search")
        except Exception as e:
            if DEBUG_MODE:
                print(f"  GDELT error: {e}")
        return items

    def _search_google_news(self, query: str) -> List[NewsItem]:
        """
        Search Google News RSS for real-time news.
        Free, no API key, works reliably.
        """
        items = []
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                if DEBUG_MODE:
                    print(f"  Google News returned {response.status_code}")
                return items

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, "xml")
            articles = soup.find_all("item")[:15]

            for article in articles:
                title = article.find("title")
                title = title.text if title else ""
                link = article.find("link")
                link = link.text if link else ""
                pub_date = article.find("pubDate")
                pub_date = pub_date.text[:10] if pub_date else ""
                source = article.find("source")
                source = source.text if source else "Google News"

                title_lower = title.lower()
                found_keywords = [
                    kw for kw in NEGATIVE_KEYWORDS
                    if kw in title_lower
                ]
                is_negative = len(found_keywords) > 0

                if title:
                    items.append(NewsItem(
                        title=title,
                        url=link,
                        date=pub_date,
                        source=source,
                        is_negative=is_negative,
                        keywords_found=found_keywords
                    ))

            if DEBUG_MODE:
                print(f"  Google News: {len(items)} articles for '{query}'")

        except requests.exceptions.Timeout:
            print("  Google News timeout")
        except Exception as e:
            if DEBUG_MODE:
                print(f"  Google News error: {e}")

        return items

    def _check_mca(self, company_name: str) -> List[dict]:
        charges = []
        try:
            url = "https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do"
            response = self.session.get(
                url, params={"companyName": company_name}, timeout=8
            )
            if response.status_code == 200:
                text = response.text.lower()
                if "charge" in text and "satisfied" not in text:
                    charges.append({
                        "type": "Unsatisfied Charge",
                        "source": "MCA21",
                        "details": "Charge registered — verify amount",
                        "risk_level": "Medium"
                    })
        except Exception as e:
            if DEBUG_MODE:
                print(f"  MCA error: {e}")
        return charges

    def _check_ecourts(self, company_name: str) -> List[str]:
        cases = []
        try:
            url = "https://services.ecourts.gov.in/ecourtindia_v6/"
            response = self.session.get(url, timeout=8)
            if response.status_code == 200:
                if company_name.lower() in response.text.lower():
                    cases.append(
                        f"Potential case found for {company_name}"
                    )
        except Exception as e:
            if DEBUG_MODE:
                print(f"  e-Courts error: {e}")
        return cases

    def _check_rbi_sebi(self, company_name: str) -> List[str]:
        actions = []
        try:
            url = "https://www.rbi.org.in/Scripts/EnforcementActions.aspx"
            response = self.session.get(url, timeout=8)
            if response.status_code == 200:
                if company_name.lower() in response.text.lower():
                    actions.append(
                        f"RBI enforcement action found for {company_name}"
                    )
        except Exception as e:
            if DEBUG_MODE:
                print(f"  RBI error: {e}")
        try:
            url = "https://www.sebi.gov.in/enforcement/orders.html"
            response = self.session.get(url, timeout=8)
            if response.status_code == 200:
                if company_name.lower() in response.text.lower():
                    actions.append(
                        f"SEBI order found for {company_name}"
                    )
        except Exception as e:
            if DEBUG_MODE:
                print(f"  SEBI error: {e}")
        return actions

    def _build_summary(self, findings: ResearchFindings) -> str:
        lines = []
        total_news = (
            len(findings.negative_news) + len(findings.positive_news)
        )
        if total_news == 0:
            lines.append("No significant news coverage found.")
        else:
            lines.append(
                f"Found {total_news} articles: "
                f"{len(findings.negative_news)} negative, "
                f"{len(findings.positive_news)} positive. "
                f"News risk score: {findings.news_risk_score}/10."
            )
            if findings.negative_news:
                lines.append(
                    f"Top negative: '{findings.negative_news[0].title[:80]}'"
                )
        if findings.litigation_found:
            lines.append(
                f"Litigation: {len(findings.litigation_details)} case(s)."
            )
        else:
            lines.append("No litigation found.")
        if findings.mca_charges:
            lines.append(f"MCA: {len(findings.mca_charges)} charge(s).")
        else:
            lines.append("No MCA charges.")
        if findings.rbi_sebi_actions:
            lines.append(
                f"ALERT: {len(findings.rbi_sebi_actions)} RBI/SEBI action(s)."
            )
        else:
            lines.append("No RBI/SEBI actions.")
        return " ".join(lines)


if __name__ == "__main__":
    agent = ResearchAgent()

    print("="*50)
    print("TEST 1: Live Research")
    print("="*50)
    findings = agent.research("Reliance Industries")
    print(f"News Risk Score: {findings.news_risk_score}/10")
    print(f"Summary: {findings.research_summary}")

    print("\n" + "="*50)
    print("TEST 2: Mock Research (High Risk)")
    print("="*50)
    mock = agent.research_with_mock("XYZ Industries Pvt Ltd", "high")
    print(f"News Risk Score: {mock.news_risk_score}/10")
    print(f"Negative News:  {len(mock.negative_news)}")
    print(f"Litigation:     {mock.litigation_found}")
    print(f"MCA Charges:    {len(mock.mca_charges)}")
    print(f"RBI/SEBI:       {len(mock.rbi_sebi_actions)}")
    print(f"Summary: {mock.research_summary}")
