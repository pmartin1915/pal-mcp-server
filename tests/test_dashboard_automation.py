# This file was intended for c:/auction/tests/e2e/test_dashboard_automation.py
# Writing it to the current project's tests directory due to workspace restrictions.

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Generator

import pytest
from playwright.sync_api import Page, expect

# --- Configuration ---
STREAMLIT_APP_PATH = "c:/auction/streamlit_app/app.py"
STREAMLIT_PORT = 8501
BASE_URL = f"http://localhost:{STREAMLIT_PORT}"
SCREENSHOT_DIR = Path("tests/e2e/screenshots")

# Ensure the screenshot directory exists
SCREENSHOT_DIR.mkdir(exist_ok=True)


# --- Fixtures ---
@pytest.fixture(scope="session")
def streamlit_app() -> Generator[subprocess.Popen, None, None]:
    """
    Fixture to launch the Streamlit app as a subprocess.
    Handles cross-platform process management and graceful cleanup.
    """
    command = [
        "streamlit",
        "run",
        STREAMLIT_APP_PATH,
        f"--server.port={STREAMLIT_PORT}",
        "--server.headless=true",  # Run without opening a browser
    ]

    # Start the Streamlit app process
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    # Wait for the app to be accessible
    time.sleep(5)

    yield process

    # --- Cleanup ---
    if sys.platform == "win32":
        process.send_signal(signal.CTRL_C_EVENT)
    else:
        process.send_signal(signal.SIGINT)

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


# --- Test Class ---
@pytest.mark.e2e
class TestDashboard:
    """
    End-to-end tests for the Streamlit dashboard.
    """

    def test_dashboard_loads_successfully(
        self, page: Page, streamlit_app: subprocess.Popen
    ):
        """
        Tests if the dashboard loads without any client-side errors.
        """
        try:
            page.goto(BASE_URL, timeout=30000)
            expect(
                page.locator("text=Property Investment Dashboard")
            ).to_be_visible()
        except Exception as e:
            page.screenshot(
                path=str(SCREENSHOT_DIR / "dashboard_load_failure.png")
            )
            pytest.fail(f"Dashboard failed to load: {e}")

    def test_property_table_displays_data(
        self, page: Page, streamlit_app: subprocess.Popen
    ):
        """
        Tests if the main property table is visible and contains data.
        """
        try:
            page.goto(BASE_URL, timeout=30000)
            property_table = page.locator(".stDataFrame")
            expect(property_table).to_be_visible(timeout=15000)
            # Check for at least one row of data
            expect(property_table.locator("tbody tr")).to_have_count(
                lambda count: count > 0, timeout=10000
            )
        except Exception as e:
            page.screenshot(
                path=str(SCREENSHOT_DIR / "property_table_failure.png")
            )
            pytest.fail(f"Property table not visible or empty: {e}")

    def test_filter_by_county(self, page: Page, streamlit_app: subprocess.Popen):
        """
        Tests the functionality of filtering the property table by county.
        """
        try:
            page.goto(BASE_URL, timeout=30000)
            # Select a county to filter by (e.g., "King")
            page.select_option('select[aria-label="Select County"]', "King")
            # Wait for the table to update
            page.wait_for_timeout(2000)
            # Verify that all visible rows belong to the selected county
            rows = page.locator(".stDataFrame tbody tr").all()
            for row in rows:
                expect(row.locator("td").nth(1)).to_have_text("King")
        except Exception as e:
            page.screenshot(path=str(SCREENSHOT_DIR / "filter_county_failure.png"))
            pytest.fail(f"Filtering by county failed: {e}")

    def test_sort_by_investment_score(
        self, page: Page, streamlit_app: subprocess.Popen
    ):
        """
        Tests sorting the property table by the 'investment_score' column.
        """
        try:
            page.goto(BASE_URL, timeout=30000)
            # Click the 'investment_score' header to sort
            page.locator("text=investment_score").click()
            # Wait for the table to update
            page.wait_for_timeout(2000)
            # Get the investment scores from the first few rows
            scores = [
                float(cell.inner_text())
                for cell in page.locator(
                    ".stDataFrame tbody tr > td:last-child"
                ).all()[:5]
            ]
            # Assert that the scores are in descending order
            assert scores == sorted(
                scores, reverse=True
            ), "Scores are not sorted correctly"
        except Exception as e:
            page.screenshot(path=str(SCREENSHOT_DIR / "sort_score_failure.png"))
            pytest.fail(f"Sorting by investment score failed: {e}")

    def test_property_detail_view(self, page: Page, streamlit_app: subprocess.Popen):
        """
        Tests if clicking a property opens a detail view.
        (This is a placeholder assuming such functionality exists)
        """
        try:
            page.goto(BASE_URL, timeout=30000)
            # Click on the first property in the table
            page.locator(".stDataFrame tbody tr").first.click()
            # Check for a detail view element
            detail_view = page.locator("text=Property Details")
            expect(detail_view).to_be_visible(timeout=10000)
        except Exception as e:
            page.screenshot(
                path=str(SCREENSHOT_DIR / "detail_view_failure.png")
            )
            pytest.fail(f"Property detail view did not open: {e}")

    def test_export_functionality(self, page: Page, streamlit_app: subprocess.Popen):
        """
        Tests the data export functionality.
        """
        try:
            page.goto(BASE_URL, timeout=30000)
            with page.expect_download() as download_info:
                page.locator("text=Export Data").click()
            download = download_info.value
            assert (
                download.suggested_filename == "property_data.csv"
            ), "Download filename is incorrect"
            # Optional: Check file size or content
            assert download.size() > 0, "Downloaded file is empty"
        except Exception as e:
            page.screenshot(path=str(SCREENSHOT_DIR / "export_failure.png"))
            pytest.fail(f"Export functionality failed: {e}")
