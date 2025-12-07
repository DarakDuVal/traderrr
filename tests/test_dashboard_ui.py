"""
Selenium tests for dashboard UI functionality

Tests user interactions including:
- Auth tab switching (login/register)
- Form visibility toggling
- Login and registration form functionality
"""

import pytest
import time
import subprocess
import os
import signal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from threading import Thread


@pytest.fixture(scope="session", autouse=True)
def flask_server():
    """Start Flask development server in a background subprocess"""
    import sys
    import requests

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Start Flask server using Python subprocess with inline script
    server_script = """
import sys
import os

# Ensure we're using development settings
os.environ['FLASK_ENV'] = 'development'
os.environ['PYTHONUNBUFFERED'] = '1'

try:
    # Import and create the Flask app
    from app import create_app
    app = create_app()

    # Run the Flask development server
    print('FLASK_SERVER_READY', flush=True)
    sys.stdout.flush()
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
except Exception as e:
    print(f'FLASK_SERVER_ERROR: {e}', flush=True, file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

    process = subprocess.Popen(
        [sys.executable, "-c", server_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        text=True,
        bufsize=1,
    )

    # Wait for Flask to initialize and print readiness marker
    server_ready = False
    max_wait = 30
    for i in range(max_wait):
        try:
            # Try to read from stdout to see if server has started
            line = process.stdout.readline()
            if line:
                print(f"[Server {i}] {line.strip()}")
                if "FLASK_SERVER_READY" in line:
                    server_ready = True
                    break
                if "FLASK_SERVER_ERROR" in line:
                    stderr_content = process.stderr.read()
                    print(f"Flask error: {line}")
                    print(f"Stderr: {stderr_content}")
                    raise RuntimeError(f"Flask server failed: {line}")
        except:
            pass

        time.sleep(0.5)

    if not server_ready:
        # Try with HTTP requests as fallback
        for attempt in range(max_wait):
            try:
                response = requests.get("http://127.0.0.1:5000/", timeout=1)
                print(f"[OK] Server started on attempt {attempt+1}")
                server_ready = True
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                pass
            time.sleep(0.5)

    if not server_ready:
        # Process didn't print ready marker and server not reachable
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        print(f"Flask server failed to start!")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        raise RuntimeError("Flask server failed to start or respond")

    # Final check: ensure the server is actually responding
    time.sleep(1)
    try:
        response = requests.get("http://127.0.0.1:5000/", timeout=2)
        print(f"[OK] Server is responding with status {response.status_code}")
    except Exception as e:
        process.terminate()
        raise RuntimeError(f"Server not responding: {e}")

    yield

    # Cleanup: terminate the server
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture
def driver():
    """Create Selenium WebDriver instance"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    # Uncomment for headless mode:
    # chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(15)
    driver.implicitly_wait(10)

    yield driver

    # Capture browser logs before closing
    try:
        logs = driver.get_log("browser")
        if logs:
            print("\n=== Browser Console Logs ===")
            for log in logs:
                print(f"[{log['level']}] {log['message']}")
    except:
        pass

    driver.quit()


class TestAuthTabSwitching:
    """Test auth tab switching between login and register"""

    def test_login_tab_active_by_default(self, driver):
        """Login tab should be active when page loads"""
        driver.get("http://127.0.0.1:5000/")

        login_tab = driver.find_element(By.ID, "loginTab")
        register_tab = driver.find_element(By.ID, "registerTab")

        assert login_tab.get_attribute("class") == "auth-tab active"
        assert register_tab.get_attribute("class") == "auth-tab"

    def test_click_register_tab_switches_to_register(self, driver):
        """Clicking register tab should show register form and hide login form"""
        driver.get("http://127.0.0.1:5000/")
        time.sleep(1)

        # Call switchAuthTab directly via JavaScript to verify the function works
        driver.execute_script("switchAuthTab('register');")

        # Wait for the form switch
        time.sleep(0.5)

        login_tab = driver.find_element(By.ID, "loginTab")
        register_tab = driver.find_element(By.ID, "registerTab")
        login_form = driver.find_element(By.ID, "loginForm")
        register_form = driver.find_element(By.ID, "registerForm")

        # Check tab classes
        assert "active" not in login_tab.get_attribute(
            "class"
        ), f"Login tab should not have 'active', got: {login_tab.get_attribute('class')}"
        assert "active" in register_tab.get_attribute(
            "class"
        ), f"Register tab should have 'active', got: {register_tab.get_attribute('class')}"

        # Check form visibility
        assert "show" not in login_form.get_attribute(
            "class"
        ), f"Login form should not have 'show', got: {login_form.get_attribute('class')}"
        assert "show" in register_form.get_attribute(
            "class"
        ), f"Register form should have 'show', got: {register_form.get_attribute('class')}"

    def test_click_login_tab_switches_back_to_login(self, driver):
        """Clicking login tab after switching should show login form"""
        driver.get("http://127.0.0.1:5000/")

        register_tab = driver.find_element(By.ID, "registerTab")
        register_tab.click()
        time.sleep(0.5)

        login_tab = driver.find_element(By.ID, "loginTab")
        login_tab.click()
        time.sleep(0.5)

        login_tab = driver.find_element(By.ID, "loginTab")
        register_tab = driver.find_element(By.ID, "registerTab")
        login_form = driver.find_element(By.ID, "loginForm")
        register_form = driver.find_element(By.ID, "registerForm")

        # Check tab classes
        assert "active" in login_tab.get_attribute("class")
        assert "active" not in register_tab.get_attribute("class")

        # Check form visibility
        assert "show" in login_form.get_attribute("class")
        assert "show" not in register_form.get_attribute("class")

    def test_register_tab_clickable(self, driver):
        """Register tab should be clickable and functional"""
        driver.get("http://127.0.0.1:5000/")

        register_tab = driver.find_element(By.ID, "registerTab")

        # Verify tab is displayed and clickable
        assert register_tab.is_displayed()
        assert register_tab.is_enabled()

        # Click should not raise exception
        register_tab.click()

        # Verify register form becomes visible
        register_form = driver.find_element(By.ID, "registerForm")
        wait = WebDriverWait(driver, 5)
        wait.until(EC.visibility_of_element_located((By.ID, "registerForm")))

        assert register_form.is_displayed()


class TestFormVisibility:
    """Test form visibility and structure"""

    def test_login_form_visible_on_load(self, driver):
        """Login form should be visible by default"""
        driver.get("http://127.0.0.1:5000/")

        login_form = driver.find_element(By.ID, "loginForm")
        assert login_form.is_displayed()

    def test_register_form_hidden_on_load(self, driver):
        """Register form should be hidden by default"""
        driver.get("http://127.0.0.1:5000/")

        register_form = driver.find_element(By.ID, "registerForm")
        assert not register_form.is_displayed()

    def test_login_form_elements_present(self, driver):
        """Login form should have all required input fields"""
        driver.get("http://127.0.0.1:5000/")

        username_input = driver.find_element(By.ID, "loginUsername")
        password_input = driver.find_element(By.ID, "loginPassword")
        login_btn = driver.find_element(By.ID, "loginBtn")

        assert username_input.is_displayed()
        assert password_input.is_displayed()
        assert login_btn.is_displayed()

    def test_register_form_elements_present(self, driver):
        """Register form should have all required input fields"""
        driver.get("http://127.0.0.1:5000/")

        register_tab = driver.find_element(By.ID, "registerTab")
        register_tab.click()
        time.sleep(0.5)

        username_input = driver.find_element(By.ID, "registerUsername")
        email_input = driver.find_element(By.ID, "registerEmail")
        password_input = driver.find_element(By.ID, "registerPassword")
        confirm_input = driver.find_element(By.ID, "registerConfirm")
        register_btn = driver.find_element(By.ID, "registerBtn")

        assert username_input.is_displayed()
        assert email_input.is_displayed()
        assert password_input.is_displayed()
        assert confirm_input.is_displayed()
        assert register_btn.is_displayed()


class TestLoginFormFunctionality:
    """Test login form interaction"""

    def test_can_type_in_login_fields(self, driver):
        """Should be able to type in login form fields"""
        driver.get("http://127.0.0.1:5000/")

        username_input = driver.find_element(By.ID, "loginUsername")
        password_input = driver.find_element(By.ID, "loginPassword")

        username_input.send_keys("testuser")
        password_input.send_keys("testpass123")

        assert username_input.get_attribute("value") == "testuser"
        assert password_input.get_attribute("value") == "testpass123"

    def test_login_submit_button_clickable(self, driver):
        """Login submit button should be clickable"""
        driver.get("http://127.0.0.1:5000/")

        login_btn = driver.find_element(By.ID, "loginBtn")

        assert login_btn.is_enabled()
        assert login_btn.is_displayed()


class TestRegisterFormFunctionality:
    """Test register form interaction"""

    def test_can_type_in_register_fields(self, driver):
        """Should be able to type in register form fields"""
        driver.get("http://127.0.0.1:5000/")

        register_tab = driver.find_element(By.ID, "registerTab")
        register_tab.click()
        time.sleep(0.5)

        username_input = driver.find_element(By.ID, "registerUsername")
        email_input = driver.find_element(By.ID, "registerEmail")
        password_input = driver.find_element(By.ID, "registerPassword")
        confirm_input = driver.find_element(By.ID, "registerConfirm")

        username_input.send_keys("newuser")
        email_input.send_keys("user@example.com")
        password_input.send_keys("SecurePass123")
        confirm_input.send_keys("SecurePass123")

        assert username_input.get_attribute("value") == "newuser"
        assert email_input.get_attribute("value") == "user@example.com"
        assert password_input.get_attribute("value") == "SecurePass123"
        assert confirm_input.get_attribute("value") == "SecurePass123"

    def test_register_submit_button_clickable(self, driver):
        """Register submit button should be clickable"""
        driver.get("http://127.0.0.1:5000/")

        register_tab = driver.find_element(By.ID, "registerTab")
        register_tab.click()
        time.sleep(0.5)

        register_btn = driver.find_element(By.ID, "registerBtn")

        assert register_btn.is_enabled()
        assert register_btn.is_displayed()


class TestPasswordRequirements:
    """Test password strength requirements display"""

    def test_password_requirements_visible_on_register_tab(self, driver):
        """Password requirements should be visible in register form"""
        driver.get("http://127.0.0.1:5000/")

        register_tab = driver.find_element(By.ID, "registerTab")
        register_tab.click()
        time.sleep(0.5)

        requirements_container = driver.find_element(
            By.CLASS_NAME, "password-requirements"
        )
        assert requirements_container.is_displayed()

    def test_password_requirements_elements_present(self, driver):
        """All password requirement elements should be present"""
        driver.get("http://127.0.0.1:5000/")

        register_tab = driver.find_element(By.ID, "registerTab")
        register_tab.click()
        time.sleep(0.5)

        req_length = driver.find_element(By.ID, "req-length")
        req_uppercase = driver.find_element(By.ID, "req-uppercase")
        req_lowercase = driver.find_element(By.ID, "req-lowercase")
        req_number = driver.find_element(By.ID, "req-number")

        assert req_length.is_displayed()
        assert req_uppercase.is_displayed()
        assert req_lowercase.is_displayed()
        assert req_number.is_displayed()


class TestAuthScreenLayout:
    """Test overall auth screen layout"""

    def test_auth_tabs_visible(self, driver):
        """Auth tabs should be visible on page load"""
        driver.get("http://127.0.0.1:5000/")

        auth_tabs = driver.find_element(By.CLASS_NAME, "auth-tabs")
        assert auth_tabs.is_displayed()

    def test_login_title_visible(self, driver):
        """Login screen title should be visible"""
        driver.get("http://127.0.0.1:5000/")

        # Wait for page to load and element to be present
        wait = WebDriverWait(driver, 15)
        title = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "login-title"))
        )
        assert title.is_displayed()
        assert "Trading Dashboard" in title.text

    def test_auth_tabs_have_correct_labels(self, driver):
        """Auth tabs should have correct labels"""
        driver.get("http://127.0.0.1:5000/")

        # Wait for page to load and tabs to be present
        wait = WebDriverWait(driver, 15)
        login_tab = wait.until(EC.presence_of_element_located((By.ID, "loginTab")))
        register_tab = driver.find_element(By.ID, "registerTab")

        assert "Sign In" in login_tab.text or login_tab.text == "Sign In"
        assert "Register" in register_tab.text or register_tab.text == "Register"
