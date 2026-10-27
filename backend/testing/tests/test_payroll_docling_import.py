import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.modules import finance


class PayrollUpload:
    filename = "payroll.csv"

    async def read(self, _limit):
        return b"employee,hourly_cost,currency,valid_from\n"

    async def close(self):
        return None


def test_payroll_import_uses_docling_markdown_as_the_parsed_source(monkeypatch):
    conversion = AsyncMock(return_value={
        "markdown": "| employee | hourly_cost | currency | valid_from |\n| --- | --- | --- | --- |\n| tester-1 | 125 | VND | 2026-01-01 |",
        "structure": [],
        "unprocessed_blocks": [],
    })
    monkeypatch.setattr(finance.ai_automation_client, "convert_attachment", conversion)
    monkeypatch.setattr(
        finance.settings,
        "MAX_UPLOAD_SIZE_BYTES",
        1000,
    )

    headers, rows = asyncio.run(finance._parse_sheet(PayrollUpload()))

    conversion.assert_awaited_once_with("payroll.csv", b"employee,hourly_cost,currency,valid_from\n")
    assert headers == ["employee", "hourly_cost", "currency", "valid_from"]
    assert rows == [{
        "employee": "tester-1",
        "hourly_cost": "125",
        "currency": "VND",
        "valid_from": "2026-01-01",
    }]


def test_payroll_import_rejects_unprocessed_docling_content(monkeypatch):
    monkeypatch.setattr(
        finance.ai_automation_client,
        "convert_attachment",
        AsyncMock(return_value={
            "markdown": "| employee | hourly_cost | currency | valid_from |\n| --- | --- | --- | --- |\n| tester-1 | 125 | VND | 2026-01-01 |",
            "unprocessed_blocks": [{"reason_code": "TABLE_NOT_EXTRACTED"}],
        }),
    )
    monkeypatch.setattr(finance.settings, "MAX_UPLOAD_SIZE_BYTES", 1000)

    with pytest.raises(HTTPException) as raised:
        asyncio.run(finance._parse_sheet(PayrollUpload()))

    assert raised.value.status_code == 422
    assert raised.value.detail["code"] == "PAYROLL_DOCUMENT_HAS_UNPROCESSED_BLOCKS"


def test_markdown_parser_skips_separator_rows_and_keeps_table_values():
    headers, rows = finance._payroll_markdown_table(
        "| employee | hourly_cost |\n| --- | ---: |\n| tester-1 | 125.50 |"
    )

    assert headers == ["employee", "hourly_cost"]
    assert rows == [{"employee": "tester-1", "hourly_cost": "125.50"}]
