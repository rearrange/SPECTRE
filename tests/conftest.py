from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from playwright.async_api import Browser, Page, async_playwright

from agents.analyst_agent import AnalystAgent
from agents.browser_agent import BrowserAgent
from llm.anthropic_provider import AnthropicProvider


@pytest.fixture
def sample_test_case_login() -> str:
    return """
TEST CASE: TC-001 — User Login

Objective:
Verify that a registered user can successfully log in to the application using valid credentials,
and that appropriate error messages are shown for invalid credentials.

Preconditions:
- The application is accessible at https://app.example.com/login
- A valid user account exists with username: testuser@example.com and password: P@ssw0rd!
- The user is not currently logged in

Test Steps:
Step 1:
  Action: Navigate to https://app.example.com/login
  Expected Result: The login page is displayed with username and password fields visible

Step 2:
  Action: Enter "testuser@example.com" in the Username field
  Expected Result: The username field is populated with the entered value

Step 3:
  Action: Enter "P@ssw0rd!" in the Password field
  Expected Result: The password field is populated (characters masked)

Step 4:
  Action: Click the "Login" button
  Expected Result: User is redirected to the dashboard at /dashboard

Step 5:
  Action: Enter an invalid password "wrongpassword" and click "Login"
  Expected Result: An error message "Invalid username or password" is displayed and the user
  remains on the login page

Step 6:
  Action: Leave both fields blank and click "Login"
  Expected Result: Validation errors are shown for both required fields

Assertions:
- Successful login redirects to /dashboard
- Invalid credentials display error message "Invalid username or password"
- Empty form submission shows required field validation errors
- User session is created after successful login (auth cookie or token is set)
- Failed login does not create a session

Test Data:
  valid_username: testuser@example.com
  valid_password: P@ssw0rd!
  invalid_password: wrongpassword
  login_url: https://app.example.com/login
  dashboard_url: https://app.example.com/dashboard
"""


@pytest.fixture
def sample_test_case_search() -> str:
    return """
TEST CASE: TC-002 — Product Search

Objective:
Verify that users can search for products using the search bar and that results are accurate,
paginated, and filterable.

Preconditions:
- The user is logged in to the application
- The product catalogue contains at least 50 products
- At least 3 products exist with "wireless headphones" in their name or description

Test Steps:
Step 1:
  Action: Click on the search bar at the top of the page
  Expected Result: The search bar receives focus and a placeholder text "Search products..." is visible

Step 2:
  Action: Type "wireless headphones" in the search bar and press Enter
  Expected Result: The search results page loads displaying products matching "wireless headphones"

Step 3:
  Action: Verify that at least 3 results are displayed
  Expected Result: A minimum of 3 product cards are visible on the results page

Step 4:
  Action: Click the "Price: Low to High" sort option
  Expected Result: Products are reordered with the lowest-priced item appearing first

Step 5:
  Action: Apply the brand filter "Sony"
  Expected Result: Only Sony products remain in the search results

Step 6:
  Action: Clear all filters using the "Clear Filters" button
  Expected Result: All matching results for "wireless headphones" are restored

Step 7:
  Action: Search for a term that returns no results, e.g. "xyznonexistent"
  Expected Result: A "No results found" message is displayed with a suggestion to try different keywords

Assertions:
- Search results are relevant to the query "wireless headphones"
- At least 3 results are returned for the test query
- Sort by price reorders results correctly (ascending)
- Brand filter reduces results to the selected brand only
- Empty search results show a user-friendly "No results found" message
- Search results page displays the search term in the page title or breadcrumb

Test Data:
  search_query: wireless headphones
  no_results_query: xyznonexistent
  brand_filter: Sony
  sort_option: Price: Low to High
  min_expected_results: 3
"""


@pytest.fixture
def analyst_agent() -> AnalystAgent:
    llm = AnthropicProvider()
    return AnalystAgent(llm)


@pytest_asyncio.fixture
async def browser() -> AsyncGenerator[Browser]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest_asyncio.fixture
async def page(browser: Browser) -> AsyncGenerator[Page]:
    page = await browser.new_page()
    yield page
    await page.close()


@pytest_asyncio.fixture
async def browser_agent() -> BrowserAgent:
    llm = AnthropicProvider()
    return BrowserAgent(llm)
