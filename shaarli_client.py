"""
Shaarli Selenium Module

A Python module for automating Shaarli link sharing service using Selenium WebDriver.
Provides functionality to log in and add URLs to a Shaarli instance.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShaarliClient:
    """
    A client for interacting with Shaarli using Selenium WebDriver.
    """
    
    def __init__(self, base_url: str, headless: bool = True, timeout: int = 10):
        """
        Initialize the Shaarli client.
        
        Args:
            base_url: Base URL of the Shaarli instance (e.g., 'https://your-shaarli.com')
            headless: Whether to run browser in headless mode
            timeout: Default timeout for web operations in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.driver = None
        self.is_logged_in = False
        
        # Set up Firefox options
        self.firefox_options = Options()
        if headless:
            self.firefox_options.add_argument('--headless')
        self.firefox_options.add_argument('--no-sandbox')
        self.firefox_options.add_argument('--disable-dev-shm-usage')
        # Firefox-specific options
        self.firefox_options.add_argument('--width=1920')
        self.firefox_options.add_argument('--height=1080')
        
    def __enter__(self):
        """Context manager entry."""
        self.start_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        
    def start_driver(self):
        """Initialize the WebDriver."""
        try:
            self.driver = webdriver.Firefox(options=self.firefox_options)
            self.driver.set_window_size(1920, 1080)
            logger.info("WebDriver started successfully")
        except Exception as e:
            logger.error(f"Failed to start WebDriver: {e}")
            raise
            
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")
            
    def test_connectivity(self) -> bool:
        """Test if the Shaarli server is reachable."""
        try:
            import requests
            response = requests.get(self.base_url, timeout=5)
            logger.info(f"Server responded with status: {response.status_code}")
            return response.status_code < 400
        except ImportError:
            logger.warning("requests library not available for connectivity test")
            # Fall back to selenium test
            try:
                self.driver.get(self.base_url)
                return "neterror" not in self.driver.current_url
            except Exception as e:
                logger.error(f"Connectivity test failed: {e}")
                return False
        except Exception as e:
            logger.error(f"Server not reachable: {e}")
            return False

    def wait_for_page_ready(self, timeout: int = 10):
        """Wait for page to be fully loaded and ready."""
        try:
            # Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Wait a bit more for any JavaScript to finish
            time.sleep(1)
            
            # Wait for jQuery if present
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda driver: driver.execute_script("return typeof jQuery === 'undefined' || jQuery.active === 0")
                )
            except:
                pass  # jQuery might not be present
                
            logger.info("Page is ready")
        except Exception as e:
            logger.warning(f"Page ready check failed: {e}")

    def check_for_iframes(self):
        """Check if there are any iframes on the page."""
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"Found {len(iframes)} iframe(s) on page")
                for i, iframe in enumerate(iframes):
                    src = iframe.get_attribute("src") or "no-src"
                    name = iframe.get_attribute("name") or "no-name"
                    logger.info(f"  Iframe {i}: src='{src}', name='{name}'")
                return iframes
            else:
                logger.info("No iframes found")
                return []
        except Exception as e:
            logger.error(f"Error checking iframes: {e}")
            return []

    def try_interact_with_element(self, element, action="click", text=None):
        """Try multiple ways to interact with an element."""
        if not element:
            return False
            
        try:
            # Method 1: Regular interaction
            if action == "click":
                element.click()
                return True
            elif action == "send_keys" and text:
                element.clear()
                element.send_keys(text)
                return True
        except Exception as e:
            logger.warning(f"Regular {action} failed: {e}, trying alternatives")
        
        try:
            # Method 2: Scroll into view and try again
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            
            if action == "click":
                element.click()
                return True
            elif action == "send_keys" and text:
                element.clear()
                element.send_keys(text)
                return True
        except Exception as e:
            logger.warning(f"Scroll + {action} failed: {e}, trying JavaScript")
        
        try:
            # Method 3: JavaScript interaction
            if action == "click":
                self.driver.execute_script("arguments[0].click();", element)
                return True
            elif action == "send_keys" and text:
                self.driver.execute_script("arguments[0].value = '';", element)
                self.driver.execute_script("arguments[0].value = arguments[1];", element, text)
                # Trigger input events
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", element)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", element)
                return True
        except Exception as e:
            logger.error(f"JavaScript {action} failed: {e}")
        
        return False

    def debug_page_elements(self):
        """Debug helper to print all form elements on the current page."""
        try:
            # Find all input elements
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            logger.info(f"Found {len(inputs)} input elements:")
            for i, inp in enumerate(inputs):
                try:
                    name = inp.get_attribute("name") or "no-name"
                    input_type = inp.get_attribute("type") or "no-type"
                    input_id = inp.get_attribute("id") or "no-id"
                    placeholder = inp.get_attribute("placeholder") or "no-placeholder"
                    logger.info(f"  Input {i}: name='{name}', type='{input_type}', id='{input_id}', placeholder='{placeholder}'")
                except Exception as e:
                    logger.info(f"  Input {i}: Error getting attributes - {e}")
            
            # Find all forms
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            logger.info(f"Found {len(forms)} form elements")
            
            # Print page source snippet for debugging
            page_source = self.driver.page_source
            if "login" in page_source.lower():
                logger.info("Page contains 'login' text")
            if "password" in page_source.lower():
                logger.info("Page contains 'password' text")
                
        except Exception as e:
            logger.error(f"Debug error: {e}")

    def login(self, username: str, password: str) -> bool:
        """
        Log in to Shaarli.
        
        Args:
            username: Shaarli username
            password: Shaarli password
            
        Returns:
            True if login successful, False otherwise
        """
        if not self.driver:
            raise RuntimeError("WebDriver not initialized. Call start_driver() first.")
            
        try:
            # Navigate to login page
            login_url = f"{self.base_url}/login"
            logger.info(f"Navigating to login page: {login_url}")
            self.driver.get(login_url)
            
            # Wait for page to fully load
            self.wait_for_page_ready()
            
            # Check for iframes
            iframes = self.check_for_iframes()
            
            logger.info("Debugging page elements...")
            self.debug_page_elements()
            
            # Wait for login form to load
            wait = WebDriverWait(self.driver, self.timeout)
            
            # First, try to find ANY input field to ensure the page is loaded
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
                logger.info("Page has loaded - input elements found")
            except TimeoutException:
                logger.error("No input elements found on page - page may not have loaded")
                return False
            
            # Try multiple approaches to find username field
            username_field = None
            
            # Approach 1: Try common selectors
            username_selectors = [
                (By.NAME, "login"),
                (By.NAME, "username"),
                (By.NAME, "user"),
                (By.ID, "login"),
                (By.ID, "username"),
                (By.ID, "user"),
                (By.CSS_SELECTOR, "input[name='login']"),
                (By.CSS_SELECTOR, "input[name='username']"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.XPATH, "//input[@name='login']"),
                (By.XPATH, "//input[@name='username']"),
                (By.XPATH, "//input[@type='text']"),
                (By.XPATH, "//input[contains(@placeholder, 'user')]"),
                (By.XPATH, "//input[contains(@placeholder, 'login')]"),
                (By.XPATH, "//input[contains(@class, 'user')]"),
                (By.XPATH, "//input[contains(@class, 'login')]")
            ]
            
            for selector_type, selector_value in username_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    if elements:
                        username_field = elements[0]  # Take the first match
                        logger.info(f"Found username field using {selector_type}: {selector_value}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector_type}:{selector_value} failed: {e}")
                    continue
            
            # Approach 2: If still not found, try to find the first text input in a form
            if not username_field:
                logger.info("Trying to find first text input in a form...")
                try:
                    forms = self.driver.find_elements(By.TAG_NAME, "form")
                    for form in forms:
                        text_inputs = form.find_elements(By.CSS_SELECTOR, "input[type='text'], input:not([type])")
                        if text_inputs:
                            username_field = text_inputs[0]
                            logger.info("Found username field as first text input in form")
                            break
                except Exception as e:
                    logger.debug(f"Form-based search failed: {e}")
            
            # Approach 3: Find any input that's not password type
            if not username_field:
                logger.info("Trying to find any non-password input...")
                try:
                    all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    for inp in all_inputs:
                        input_type = inp.get_attribute("type")
                        if input_type not in ["password", "submit", "button", "hidden"]:
                            username_field = inp
                            logger.info(f"Found potential username field with type: {input_type}")
                            break
                except Exception as e:
                    logger.debug(f"Generic input search failed: {e}")

                    
            if not username_field:
                logger.error("Could not find username field")
                # If we found iframes, try searching in them
                if iframes:
                    logger.info("Searching for username field in iframes...")
                    for i, iframe in enumerate(iframes):
                        try:
                            self.driver.switch_to.frame(iframe)
                            self.debug_page_elements()
                            
                            # Try to find username field in iframe
                            for selector_type, selector_value in username_selectors[:5]:  # Try first 5 selectors
                                try:
                                    elements = self.driver.find_elements(selector_type, selector_value)
                                    if elements:
                                        username_field = elements[0]
                                        logger.info(f"Found username field in iframe {i} using {selector_type}: {selector_value}")
                                        break
                                except:
                                    continue
                            
                            if username_field:
                                break
                                
                            self.driver.switch_to.default_content()
                        except Exception as e:
                            logger.warning(f"Error checking iframe {i}: {e}")
                            self.driver.switch_to.default_content()
                
                if not username_field:
                    return False
            
            # Scroll to username field and interact using robust method
            logger.info("Attempting to interact with username field...")
            if not self.try_interact_with_element(username_field, "send_keys", username):
                logger.error("Failed to enter username")
                return False
            
            # Try multiple selectors for password field
            password_field = None
            password_selectors = [
                (By.NAME, "password"),
                (By.ID, "password"),
                (By.CSS_SELECTOR, "input[name='password']"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.XPATH, "//input[@name='password']"),
                (By.XPATH, "//input[@type='password']")
            ]
            
            for selector_type, selector_value in password_selectors:
                try:
                    password_elements = self.driver.find_elements(selector_type, selector_value)
                    if password_elements:
                        password_field = password_elements[0]
                        logger.info(f"Found password field using {selector_type}: {selector_value}")
                        break
                except Exception as e:
                    logger.debug(f"Password selector failed: {e}")
                    continue
            
            # If still no password field, try to find any password type input
            if not password_field:
                try:
                    password_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
                    if password_inputs:
                        password_field = password_inputs[0]
                        logger.info("Found password field by type")
                except Exception as e:
                    logger.debug(f"Generic password search failed: {e}")
                    
            if not password_field:
                logger.error("Could not find password field")
                return False
                
            # Scroll to password field and interact using robust method
            logger.info("Attempting to interact with password field...")
            if not self.try_interact_with_element(password_field, "send_keys", password):
                logger.error("Failed to enter password")
                return False
            
            # Try multiple selectors for submit button
            submit_button = None
            submit_selectors = [
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[value*='Login']"),
                (By.CSS_SELECTOR, "input[value*='login']"),
                (By.CSS_SELECTOR, "input[value*='Log in']"),
                (By.CSS_SELECTOR, "button"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//input[contains(@value, 'Login')]"),
                (By.XPATH, "//button[contains(text(), 'Login')]")
            ]
            
            for selector_type, selector_value in submit_selectors:
                try:
                    submit_elements = self.driver.find_elements(selector_type, selector_value)
                    if submit_elements:
                        submit_button = submit_elements[0]
                        logger.info(f"Found submit button using {selector_type}: {selector_value}")
                        break
                except Exception as e:
                    logger.debug(f"Submit selector failed: {e}")
                    continue
                    
            if not submit_button:
                logger.error("Could not find submit button")
                # Try submitting the form using Enter key
                try:
                    if password_field:
                        password_field.send_keys("\n")
                        logger.info("Submitted form using Enter key")
                    else:
                        return False
                except:
                    return False
            else:
                # Submit using robust interaction method
                logger.info("Attempting to click submit button...")
                if not self.try_interact_with_element(submit_button, "click"):
                    logger.error("Failed to click submit button")
                    # Try Enter key as fallback
                    try:
                        if password_field:
                            password_field.send_keys("\n")
                            logger.info("Submitted form using Enter key as fallback")
                    except:
                        return False
            
            # Wait for redirect and check if login was successful
            time.sleep(3)
            
            # Check if we're redirected to the main page or if there's an error
            current_url = self.driver.current_url
            if "login" not in current_url or self._is_logged_in():
                self.is_logged_in = True
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed - still on login page")
                return False
                
        except TimeoutException:
            logger.error("Login timeout - page elements not found")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
            
    def _is_logged_in(self) -> bool:
        """Check if currently logged in by looking for logout link or admin elements."""
        try:
            # Look for common elements that appear when logged in
            logout_elements = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Logout")
            admin_elements = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Tools")
            add_elements = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Shaare")
            
            return len(logout_elements) > 0 or len(admin_elements) > 0 or len(add_elements) > 0
        except:
            return False
            
    def add_url(self, url: str, title: str = "", description: str = "", 
                tags: str = "", private: bool = False) -> bool:
        """
        Add a URL to Shaarli using the two-step process.
        
        Args:
            url: URL to add
            title: Title for the link (optional)
            description: Description for the link (optional)
            tags: Tags for the link, space-separated (optional)
            private: Whether the link should be private (optional)
            
        Returns:
            True if URL was added successfully, False otherwise
        """
        if not self.driver:
            raise RuntimeError("WebDriver not initialized")
            
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        try:
            # Step 1: Navigate to the add URL page
            add_url_page = f"{self.base_url}/admin/add-shaare"
            logger.info(f"Navigating to add URL page: {add_url_page}")
            self.driver.get(add_url_page)
            
            # Wait for page to load
            self.wait_for_page_ready()
            
            # Find the URL input field (first step)
            url_field = None
            url_selectors = [
                (By.NAME, "post"),
                (By.ID, "shaare"),
                (By.CSS_SELECTOR, "input[name='post']"),
                (By.CSS_SELECTOR, "input[type='url']"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.XPATH, "//input[@name='post']"),
                (By.XPATH, "//input[@id='shaare']"),
                (By.XPATH, "//input[@type='url']")
            ]
            
            for selector_type, selector_value in url_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    if elements:
                        url_field = elements[0]
                        logger.info(f"Found URL field using {selector_type}: {selector_value}")
                        break
                except Exception as e:
                    logger.debug(f"URL selector failed: {e}")
                    continue
                    
            if not url_field:
                logger.error("Could not find URL field on first page")
                self.debug_page_elements()
                return False
            
            # Enter the URL
            logger.info("Entering URL in first step...")
            if not self.try_interact_with_element(url_field, "send_keys", url):
                logger.error("Failed to enter URL")
                return False
            
            # Find and click the submit/next button for first step
            first_submit_button = None
            first_submit_selectors = [
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[value*='Add']"),
                (By.CSS_SELECTOR, "button"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//input[contains(@value, 'Add')]"),
                (By.XPATH, "//button[contains(text(), 'Add')]")
            ]
            
            for selector_type, selector_value in first_submit_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    if elements:
                        first_submit_button = elements[0]
                        logger.info(f"Found first submit button using {selector_type}: {selector_value}")
                        break
                except Exception as e:
                    logger.debug(f"First submit selector failed: {e}")
                    continue
            
            if first_submit_button:
                logger.info("Clicking submit button for first step...")
                if not self.try_interact_with_element(first_submit_button, "click"):
                    logger.error("Failed to click first submit button")
                    return False
            else:
                # Try submitting with Enter key
                logger.info("Trying Enter key to submit first step...")
                if not self.try_interact_with_element(url_field, "send_keys", "\n"):
                    logger.error("Could not submit first step")
                    return False
            
            # Wait for second page to load
            time.sleep(2)
            self.wait_for_page_ready()
            
            logger.info("Moving to second step - filling in details...")
            
            # Step 2: Fill in the details (title, description, tags)
            # Try multiple selectors for title field
            title_field = None
            title_selectors = [
                (By.NAME, "lf_title"),
                (By.NAME, "title"),
                (By.ID, "lf_title"),
                (By.ID, "title"),
                (By.CSS_SELECTOR, "input[name='lf_title']"),
                (By.CSS_SELECTOR, "input[name='title']"),
                (By.XPATH, "//input[@name='lf_title']"),
                (By.XPATH, "//input[@name='title']")
            ]
            
            for selector_type, selector_value in title_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    if elements:
                        title_field = elements[0]
                        logger.info(f"Found title field using {selector_type}: {selector_value}")
                        break
                except Exception as e:
                    logger.debug(f"Title selector failed: {e}")
                    continue
                    
            if not title_field:
                logger.error("Could not find title field on second page")
                self.debug_page_elements()
                return False
            
            # Fill in the title if provided
            if title:
                logger.info("Filling in title...")
                if not self.try_interact_with_element(title_field, "send_keys", title):
                    logger.warning("Failed to enter title, continuing...")
                
            # Description field
            if description:
                desc_selectors = [
                    (By.NAME, "lf_description"),
                    (By.NAME, "description"),
                    (By.ID, "lf_description"),
                    (By.ID, "description"),
                    (By.CSS_SELECTOR, "textarea[name='lf_description']"),
                    (By.CSS_SELECTOR, "textarea[name='description']"),
                    (By.XPATH, "//textarea[@name='lf_description']"),
                    (By.XPATH, "//textarea[@name='description']")
                ]
                
                for selector_type, selector_value in desc_selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector_value)
                        if elements:
                            desc_field = elements[0]
                            logger.info("Filling in description...")
                            self.try_interact_with_element(desc_field, "send_keys", description)
                            break
                    except Exception as e:
                        logger.debug(f"Description selector failed: {e}")
                        continue
                
            # Tags field
            if tags:
                tags_selectors = [
                    (By.NAME, "lf_tags"),
                    (By.NAME, "tags"),
                    (By.ID, "lf_tags"),
                    (By.ID, "tags"),
                    (By.CSS_SELECTOR, "input[name='lf_tags']"),
                    (By.CSS_SELECTOR, "input[name='tags']"),
                    (By.XPATH, "//input[@name='lf_tags']"),
                    (By.XPATH, "//input[@name='tags']")
                ]
                
                for selector_type, selector_value in tags_selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector_value)
                        if elements:
                            tags_field = elements[0]
                            logger.info("Filling in tags...")
                            self.try_interact_with_element(tags_field, "send_keys", tags)
                            break
                    except Exception as e:
                        logger.debug(f"Tags selector failed: {e}")
                        continue
                        
            # Private checkbox
            if private:
                private_selectors = [
                    (By.NAME, "lf_private"),
                    (By.NAME, "private"),
                    (By.ID, "lf_private"),
                    (By.ID, "private"),
                    (By.CSS_SELECTOR, "input[name='lf_private']"),
                    (By.CSS_SELECTOR, "input[name='private']"),
                    (By.XPATH, "//input[@name='lf_private']"),
                    (By.XPATH, "//input[@name='private']")
                ]
                
                for selector_type, selector_value in private_selectors:
                    try:
                        elements = self.driver.find_elements(selector_type, selector_value)
                        if elements:
                            private_checkbox = elements[0]
                            if not private_checkbox.is_selected():
                                logger.info("Setting private checkbox...")
                                self.try_interact_with_element(private_checkbox, "click")
                            break
                    except Exception as e:
                        logger.debug(f"Private selector failed: {e}")
                        continue
                        
            # Submit the final form with "Save" button
            save_selectors = [
                (By.CSS_SELECTOR, "input[type='submit'][value*='Save']"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
                (By.CSS_SELECTOR, "button"),
                (By.XPATH, "//input[@type='submit' and contains(@value, 'Save')]"),
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Save')]"),
                (By.XPATH, "//input[@type='submit']")
            ]
            
            save_button = None
            for selector_type, selector_value in save_selectors:
                try:
                    elements = self.driver.find_elements(selector_type, selector_value)
                    if elements:
                        save_button = elements[0]
                        logger.info(f"Found save button using {selector_type}: {selector_value}")
                        break
                except Exception as e:
                    logger.debug(f"Save selector failed: {e}")
                    continue
                    
            if save_button:
                logger.info("Clicking Save button...")
                if not self.try_interact_with_element(save_button, "click"):
                    logger.error("Failed to click save button")
                    return False
            else:
                logger.error("Could not find Save button")
                self.debug_page_elements()
                return False
            
            # Wait for redirect
            time.sleep(3)
            
            # Check if the URL was added successfully
            current_url = self.driver.current_url
            if "add-shaare" not in current_url and "admin" not in current_url:
                logger.info("URL added successfully")
                return True
            else:
                logger.error("Failed to add URL - still on add page")
                logger.info(f"Current URL: {current_url}")
                return False
                
        except TimeoutException:
            logger.error("Timeout while adding URL")
            return False
        except Exception as e:
            logger.error(f"Error adding URL: {e}")
            return False
            
    def get_links(self, limit: int = 10) -> list:
        """
        Get recent links from Shaarli (requires login).
        
        Args:
            limit: Maximum number of links to retrieve
            
        Returns:
            List of dictionaries containing link information
        """
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        try:
            # Navigate to main page
            logger.info("Navigating to main page to get links...")
            self.driver.get(self.base_url)
            
            # Wait for page to load
            self.wait_for_page_ready()
            
            logger.info("Debugging page elements to find link structure...")
            self.debug_page_elements()
            
            # Try multiple approaches to find links
            links = []
            
            # Approach 1: Try modern Shaarli selectors
            modern_selectors = [
                ".linklist .linklist-item",
                ".bookmark",
                ".shaare",
                ".link",
                "article",
                ".post"
            ]
            
            link_elements = []
            for selector in modern_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} link elements using selector: {selector}")
                        link_elements = elements[:limit]
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Approach 2: If no luck with CSS selectors, try finding by common link patterns
            if not link_elements:
                logger.info("Trying to find links by href patterns...")
                try:
                    # Look for any links that might be shaares
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    potential_links = []
                    
                    for link in all_links:
                        href = link.get_attribute("href")
                        if href and ("http" in href and self.base_url not in href):
                            # This looks like an external link (a shaare)
                            potential_links.append(link)
                    
                    if potential_links:
                        logger.info(f"Found {len(potential_links)} potential external links")
                        link_elements = potential_links[:limit]
                    
                except Exception as e:
                    logger.debug(f"Link pattern search failed: {e}")
            
            # Approach 3: Look for any container that might hold links
            if not link_elements:
                logger.info("Trying to find link containers...")
                container_selectors = [
                    ".main-content",
                    ".content",
                    "#content",
                    "main",
                    ".container"
                ]
                
                for container_selector in container_selectors:
                    try:
                        container = self.driver.find_element(By.CSS_SELECTOR, container_selector)
                        # Look for any elements with links inside this container
                        container_links = container.find_elements(By.TAG_NAME, "a")
                        if container_links:
                            logger.info(f"Found {len(container_links)} links in container: {container_selector}")
                            # Filter for external links
                            external_links = []
                            for link in container_links:
                                href = link.get_attribute("href")
                                if href and "http" in href and self.base_url not in href:
                                    external_links.append(link)
                            
                            if external_links:
                                link_elements = external_links[:limit]
                                break
                    except Exception as e:
                        logger.debug(f"Container {container_selector} failed: {e}")
                        continue
            
            if not link_elements:
                logger.warning("Could not find any link elements")
                logger.info("Page source snippet:")
                page_source = self.driver.page_source[:1000]  # First 1000 chars
                logger.info(page_source)
                return []
            
            # Extract information from found elements
            for i, element in enumerate(link_elements):
                try:
                    link_info = {}
                    
                    # Try to get the URL and title
                    if element.tag_name == "a":
                        # Element is a link itself
                        url = element.get_attribute("href")
                        title = element.text.strip() or element.get_attribute("title") or "No title"
                        link_info["url"] = url
                        link_info["title"] = title
                    else:
                        # Element is a container, find link inside
                        link_elem = None
                        link_selectors = [
                            "a[href*='http']",
                            ".linklist-link",
                            ".bookmark-title a",
                            ".shaare-title a",
                            "a"
                        ]
                        
                        for link_sel in link_selectors:
                            try:
                                found_links = element.find_elements(By.CSS_SELECTOR, link_sel)
                                if found_links:
                                    # Find the first external link
                                    for fl in found_links:
                                        href = fl.get_attribute("href")
                                        if href and "http" in href and self.base_url not in href:
                                            link_elem = fl
                                            break
                                    if link_elem:
                                        break
                            except:
                                continue
                        
                        if link_elem:
                            url = link_elem.get_attribute("href")
                            title = link_elem.text.strip() or link_elem.get_attribute("title") or "No title"
                            link_info["url"] = url
                            link_info["title"] = title
                        else:
                            logger.debug(f"Could not find link in element {i}")
                            continue
                    
                    # Try to get description
                    description = ""
                    desc_selectors = [
                        ".linklist-description",
                        ".bookmark-description",
                        ".shaare-description", 
                        ".description",
                        "p",
                        ".text"
                    ]
                    
                    # If element is a container, look for description inside
                    if element.tag_name != "a":
                        for desc_sel in desc_selectors:
                            try:
                                desc_elem = element.find_element(By.CSS_SELECTOR, desc_sel)
                                description = desc_elem.text.strip()
                                if description:
                                    break
                            except:
                                continue
                    
                    link_info["description"] = description
                    
                    # Try to get tags
                    tags = ""
                    tag_selectors = [
                        ".linklist-tags",
                        ".bookmark-tags",
                        ".shaare-tags",
                        ".tags",
                        ".tag"
                    ]
                    
                    if element.tag_name != "a":
                        for tag_sel in tag_selectors:
                            try:
                                tag_elems = element.find_elements(By.CSS_SELECTOR, tag_sel)
                                if tag_elems:
                                    tag_texts = [te.text.strip() for te in tag_elems if te.text.strip()]
                                    tags = " ".join(tag_texts)
                                    break
                            except:
                                continue
                    
                    link_info["tags"] = tags
                    
                    # Only add if we have at least a URL
                    if link_info.get("url"):
                        links.append(link_info)
                        logger.debug(f"Found link: {link_info['title'][:50]}... -> {link_info['url'][:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Error parsing link element {i}: {e}")
                    continue
            
            logger.info(f"Successfully retrieved {len(links)} links")
            return links
            
        except Exception as e:
            logger.error(f"Error getting links: {e}")
            return []


# Example usage
def main():
    """Example usage of the ShaarliClient."""
    
    # Configuration - UPDATE THESE VALUES FOR YOUR SETUP
    SHAARLI_URL = "http://192.168.0.26:8000"  # Change this to your actual Shaarli URL
    USERNAME = "helix"                  # Change this to your actual username
    PASSWORD = "nebulus"                  # Change this to your actual password
    
    # Example URL to add
    url_to_add = "https://example.com"
    title = "Example Website"
    description = "This is an example website"
    tags = "example web demo"
    
    # Use the client
    with ShaarliClient(SHAARLI_URL, headless=True) as client:
        # Log in
        if client.login(USERNAME, PASSWORD):
            print("Successfully logged in!")
            
            # Add a URL
            if client.add_url(url_to_add, title, description, tags):
                print(f"Successfully added URL: {url_to_add}")
            else:
                print("Failed to add URL")
                
            # Get recent links
            recent_links = client.get_links(5)
            print(f"Recent links: {len(recent_links)}")
            for link in recent_links:
                print(f"- {link['title']}: {link['url']}")
        else:
            print("Login failed!")


if __name__ == "__main__":
    main()