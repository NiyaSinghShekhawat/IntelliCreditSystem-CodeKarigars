# src/extractor.py
from config import DEBUG_MODE
from src.schemas import (
    ParsedDocument, GSTData, BankStatementData,
    ITRData, DocumentType
)
import re
import sys
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


class FinancialExtractor:
    """
    Extracts structured financial data from parsed documents.
    Uses regex patterns optimized for Indian financial documents.
    """

    # ─── GST EXTRACTION ──────────────────────────────────────────────────────

    def extract_gst(self, parsed: ParsedDocument) -> GSTData:
        """Extract key fields from a GST return document"""
        text = parsed.raw_text
        tables = parsed.tables

        gst = GSTData()

        # GSTIN (15-character alphanumeric)
        gstin_match = re.search(
            r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b',
            text
        )
        if gstin_match:
            gst.gstin = gstin_match.group(1)

        # Company name (usually near GSTIN)
        name_match = re.search(
            r'(?:Legal Name|Trade Name|Business Name)[:\s]+([A-Z][A-Za-z\s&.,-]{3,60})',
            text, re.IGNORECASE
        )
        if name_match:
            gst.company_name = name_match.group(1).strip()

        # Tax period
        period_match = re.search(
            r'(?:Tax Period|Period|Month)[:\s]+([A-Za-z]+[\s\-]+\d{4}|\d{2}[-/]\d{4})',
            text, re.IGNORECASE
        )
        if period_match:
            gst.tax_period = period_match.group(1).strip()

        # Turnover / Total Value
        turnover_match = re.search(
            r'(?:Total Turnover|Aggregate Turnover|Total Value|Turnover)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if turnover_match:
            gst.turnover = self._parse_amount(turnover_match.group(1))

        # IGST
        igst_match = re.search(
            r'IGST[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if igst_match:
            gst.igst = self._parse_amount(igst_match.group(1))

        # CGST
        cgst_match = re.search(
            r'CGST[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if cgst_match:
            gst.cgst = self._parse_amount(cgst_match.group(1))

        # SGST
        sgst_match = re.search(
            r'SGST[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if sgst_match:
            gst.sgst = self._parse_amount(sgst_match.group(1))

        # Total tax
        gst.total_tax = gst.igst + gst.cgst + gst.sgst

        # ITC Claimed
        itc_match = re.search(
            r'(?:ITC|Input Tax Credit)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if itc_match:
            gst.itc_claimed = self._parse_amount(itc_match.group(1))

        # Filing date
        date_match = re.search(
            r'(?:Date of Filing|Filed on|Filing Date)[:\s]+(\d{2}[-/]\d{2}[-/]\d{4})',
            text, re.IGNORECASE
        )
        if date_match:
            gst.filing_date = date_match.group(1)

        # Try extracting from tables if regex missed values
        gst = self._extract_gst_from_tables(gst, tables)

        if DEBUG_MODE:
            print(f"GST Extracted: GSTIN={gst.gstin}, "
                  f"Turnover={gst.turnover}, Tax={gst.total_tax}")

        return gst

    def _extract_gst_from_tables(self, gst: GSTData, tables) -> GSTData:
        """Fallback: extract GST values from tables if regex missed them"""
        for table in tables:
            for row in table.rows:
                row_str = " ".join(str(cell) for cell in row).lower()

                if "turnover" in row_str or "total value" in row_str:
                    for cell in row:
                        amount = self._parse_amount(str(cell))
                        if amount > 0 and gst.turnover == 0:
                            gst.turnover = amount

                if "igst" in row_str:
                    for cell in row:
                        amount = self._parse_amount(str(cell))
                        if amount > 0 and gst.igst == 0:
                            gst.igst = amount

                if "cgst" in row_str:
                    for cell in row:
                        amount = self._parse_amount(str(cell))
                        if amount > 0 and gst.cgst == 0:
                            gst.cgst = amount

        return gst

    # ─── BANK STATEMENT EXTRACTION ───────────────────────────────────────────

    def extract_bank(self, parsed: ParsedDocument) -> BankStatementData:
        """Extract key fields from a bank statement"""
        text = parsed.raw_text
        tables = parsed.tables

        bank = BankStatementData()

        # Account number
        acc_match = re.search(
            r'(?:Account No|A/c No|Account Number)[.:\s]+([0-9]{9,18})',
            text, re.IGNORECASE
        )
        if acc_match:
            bank.account_number = acc_match.group(1)

        # Bank name
        bank_names = [
            "SBI", "HDFC", "ICICI", "Axis", "Kotak", "Punjab National",
            "Bank of Baroda", "Canara", "Union Bank", "IndusInd", "Yes Bank"
        ]
        for name in bank_names:
            if name.lower() in text.lower():
                bank.bank_name = name
                break

        # Opening balance
        opening_match = re.search(
            r'(?:Opening Balance|Balance B/F|Balance Brought Forward)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if opening_match:
            bank.opening_balance = self._parse_amount(opening_match.group(1))

        # Closing balance
        closing_match = re.search(
            r'(?:Closing Balance|Balance C/F|Balance Carried Forward)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if closing_match:
            bank.closing_balance = self._parse_amount(closing_match.group(1))

        # Total credits
        credit_match = re.search(
            r'(?:Total Credit|Total Deposits|Total CR)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if credit_match:
            bank.total_credits = self._parse_amount(credit_match.group(1))

        # Total debits
        debit_match = re.search(
            r'(?:Total Debit|Total Withdrawals|Total DR)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if debit_match:
            bank.total_debits = self._parse_amount(debit_match.group(1))

        # Extract transactions from tables
        bank = self._extract_bank_from_tables(bank, tables)

        # Calculate average monthly balance
        if bank.monthly_balances:
            bank.average_monthly_balance = sum(
                bank.monthly_balances) / len(bank.monthly_balances)
        elif bank.opening_balance > 0 and bank.closing_balance > 0:
            bank.average_monthly_balance = (
                bank.opening_balance + bank.closing_balance) / 2

        if DEBUG_MODE:
            print(f"Bank Extracted: Credits={bank.total_credits}, "
                  f"Debits={bank.total_debits}, "
                  f"Avg Balance={bank.average_monthly_balance}")

        return bank

    def _extract_bank_from_tables(
            self, bank: BankStatementData, tables) -> BankStatementData:
        """Extract transaction data from bank statement tables"""
        bounce_keywords = ["bounce", "return", "dishonour",
                           "insufficient", "unpaid", "ecs return"]
        monthly_credits = []
        monthly_debits = []
        bounce_count = 0
        large_transactions = []

        for table in tables:
            for row in table.rows:
                row_str = " ".join(str(cell) for cell in row).lower()

                # Count EMI bounces
                if any(kw in row_str for kw in bounce_keywords):
                    bounce_count += 1

                # Look for large unusual transactions (> 10 Lakhs)
                for cell in row:
                    amount = self._parse_amount(str(cell))
                    if amount > 1_000_000:  # > 10 Lakhs
                        large_transactions.append({
                            "amount": amount,
                            "description": row_str[:100]
                        })

                # Monthly credit/debit detection
                if "credit" in row_str or " cr" in row_str:
                    for cell in row:
                        amount = self._parse_amount(str(cell))
                        if 10_000 < amount < 100_000_000:
                            monthly_credits.append(amount)

        bank.emi_bounce_count = bounce_count
        bank.large_unusual_transactions = large_transactions[:10]

        if monthly_credits:
            bank.monthly_credits = monthly_credits
            if bank.total_credits == 0:
                bank.total_credits = sum(monthly_credits)

        return bank

    # ─── ITR EXTRACTION ──────────────────────────────────────────────────────

    def extract_itr(self, parsed: ParsedDocument) -> ITRData:
        """Extract key fields from an ITR document"""
        text = parsed.raw_text

        itr = ITRData()

        # PAN
        pan_match = re.search(
            r'\b([A-Z]{5}[0-9]{4}[A-Z]{1})\b',
            text
        )
        if pan_match:
            itr.pan = pan_match.group(1)

        # Assessment Year
        ay_match = re.search(
            r'(?:Assessment Year|A\.Y\.)[:\s]+(\d{4}-\d{2,4}|\d{4}-\d{2})',
            text, re.IGNORECASE
        )
        if ay_match:
            itr.assessment_year = ay_match.group(1)

        # Gross Total Income
        gross_match = re.search(
            r'(?:Gross Total Income|Total Income)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if gross_match:
            itr.gross_income = self._parse_amount(gross_match.group(1))

        # Net Income / Taxable Income
        net_match = re.search(
            r'(?:Net Income|Taxable Income|Total Taxable Income)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if net_match:
            itr.net_income = self._parse_amount(net_match.group(1))

        # Tax Paid
        tax_match = re.search(
            r'(?:Tax Paid|Total Tax Paid|Tax Liability)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if tax_match:
            itr.tax_paid = self._parse_amount(tax_match.group(1))

        # TDS
        tds_match = re.search(
            r'TDS[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if tds_match:
            itr.tds = self._parse_amount(tds_match.group(1))

        # Net Worth
        nw_match = re.search(
            r'(?:Net Worth|Networth)[:\s]*[₹Rs.]?\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if nw_match:
            itr.net_worth = self._parse_amount(nw_match.group(1))

        if DEBUG_MODE:
            print(f"ITR Extracted: PAN={itr.pan}, "
                  f"Gross Income={itr.gross_income}, "
                  f"Net Income={itr.net_income}")

        return itr

    # ─── AUTO EXTRACT ────────────────────────────────────────────────────────

    def extract(self, parsed: ParsedDocument):
        """
        Auto-detect document type and extract accordingly.
        Returns the appropriate data object.
        """
        doc_type = parsed.document_type

        if doc_type == DocumentType.GST_RETURN:
            return self.extract_gst(parsed)

        elif doc_type == DocumentType.BANK_STATEMENT:
            return self.extract_bank(parsed)

        elif doc_type == DocumentType.ITR:
            return self.extract_itr(parsed)

        else:
            # Try all extractors and return whichever gets most data
            if DEBUG_MODE:
                print(f"Unknown doc type, trying all extractors...")

            gst = self.extract_gst(parsed)
            bank = self.extract_bank(parsed)
            itr = self.extract_itr(parsed)

            # Return whichever got the most data
            gst_score = sum(1 for v in [
                gst.gstin, gst.turnover, gst.total_tax] if v)
            bank_score = sum(1 for v in [
                bank.account_number, bank.total_credits] if v)
            itr_score = sum(1 for v in [
                itr.pan, itr.gross_income] if v)

            if gst_score >= bank_score and gst_score >= itr_score:
                return gst
            elif bank_score >= itr_score:
                return bank
            else:
                return itr

    # ─── HELPER ──────────────────────────────────────────────────────────────

    def _parse_amount(self, value: str) -> float:
        """
        Convert Indian number format to float.
        Handles: 1,00,000 / 1,000,000 / 10.5L / Rs.500 etc.
        """
        if not value:
            return 0.0

        # Remove currency symbols and spaces
        cleaned = re.sub(r'[₹Rs.\s]', '', str(value))

        # Handle Lakh/Crore shorthand
        cleaned_lower = cleaned.lower()
        if 'cr' in cleaned_lower:
            num = re.sub(r'[^0-9.]', '', cleaned)
            return float(num) * 10_000_000 if num else 0.0
        if 'l' in cleaned_lower or 'lakh' in cleaned_lower:
            num = re.sub(r'[^0-9.]', '', cleaned)
            return float(num) * 100_000 if num else 0.0

        # Remove commas (Indian format: 1,00,000)
        cleaned = cleaned.replace(',', '')

        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    ROOT_DIR = Path(__file__).parent.parent
    sys.path.insert(0, str(ROOT_DIR))

    from src.parser import DocumentParser

    parser = DocumentParser()
    extractor = FinancialExtractor()

    test_file = input(
        "Enter path to a GST/Bank/ITR PDF to test: ").strip()

    if test_file and Path(test_file).exists():
        print("\nParsing...")
        parsed = parser.parse(test_file)

        print("Extracting...")
        result = extractor.extract(parsed)

        print(f"\n--- EXTRACTED DATA ({type(result).__name__}) ---")
        print(result.model_dump())
    else:
        print("No file provided. Extractor loaded successfully.")
