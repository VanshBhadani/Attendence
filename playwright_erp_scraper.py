"""
Updated Playwright-based ERP Scraper for Geethanjali College
Handles two-step login process with browser automation
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaywrightERPScraper:
    def __init__(self):
        self.login_url = "https://geethanjali-erp.com/GCET/Login.aspx"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.authenticated = False
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_browser()
    
    async def initialize_browser(self):
        """Initialize Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            # Use Chromium for better compatibility with specific args for cloud deployment
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Set to True for production web app
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows'
                ]
            )
            
            # Create new page with realistic user agent
            self.page = await self.browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # Set viewport
            await self.page.set_viewport_size({"width": 1366, "height": 768})
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise
    
    async def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    async def login(self, roll_number: str) -> Dict[str, Any]:
        """
        Login to ERP using roll number as both username and password
        This ERP uses a two-step login process:
        1. Enter username and click Next
        2. Enter password on the next page
        
        Args:
            roll_number: Student roll number (used as both username and password)
            
        Returns:
            Dict containing success status and any relevant data
        """
        try:
            logger.info(f"Attempting two-step login for roll number: {roll_number}")
            
            # Navigate to login page
            await self.page.goto(self.login_url, wait_until='networkidle', timeout=30000)
            logger.info("Navigated to login page")
            
            # Wait for page to load completely
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Take a screenshot for debugging
            await self.page.screenshot(path='step1_login_page.png')
            logger.info("Screenshot saved as step1_login_page.png")
            
            # STEP 1: Enter username and click Next
            logger.info("STEP 1: Entering username...")
            
            # Wait for username field to be available
            try:
                await self.page.wait_for_selector('input[name="txtUserName"]', timeout=10000)
            except:
                logger.error("Username field not found")
                return {
                    'success': False,
                    'error': 'Username field not found on login page',
                    'url': self.page.url
                }
            
            # Fill username field
            await self.page.fill('input[name="txtUserName"]', roll_number)
            logger.info("Username field filled")
            
            # Click Next button
            await self.page.click('input[name="btnNext"]')
            logger.info("Next button clicked")
            
            # Wait for navigation to password page
            try:
                await self.page.wait_for_navigation(timeout=15000)
                logger.info("Navigated to password page")
            except:
                # Check if we got an error on the username step
                error_message = await self.check_for_errors()
                if error_message:
                    return {
                        'success': False,
                        'error': f'Username validation failed: {error_message}',
                        'url': self.page.url
                    }
                
                # Continue anyway, maybe the page didn't redirect
                logger.warning("No navigation detected, continuing...")
                await self.page.wait_for_timeout(3000)
            
            # Take screenshot after step 1
            await self.page.screenshot(path='step2_password_page.png')
            logger.info("Screenshot saved as step2_password_page.png")
            
            # STEP 2: Enter password
            logger.info("STEP 2: Entering password...")
            
            # Look for password field (it might have different names)
            password_selectors = [
                'input[name="txtPassword"]',
                'input[name="txtpassword"]', 
                'input[name="password"]',
                'input[name="pwd"]',
                'input[type="password"]'
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await self.page.query_selector(selector)
                    if password_input:
                        logger.info(f"Found password field with selector: {selector}")
                        break
                except:
                    continue
            
            if not password_input:
                # Maybe we're still on the first page, check for errors
                current_url = self.page.url
                
                logger.error(f"Password field not found. Current URL: {current_url}")
                
                # Check if there are any error messages
                error_message = await self.check_for_errors()
                if error_message:
                    return {
                        'success': False,
                        'error': f'Login failed at username step: {error_message}',
                        'url': current_url
                    }
                
                return {
                    'success': False,
                    'error': 'Password field not found - username may be invalid',
                    'url': current_url,
                    'debug_info': 'Check if the username is correct'
                }
            
            # Fill password field (same as username)
            await password_input.fill(roll_number)
            logger.info("Password field filled")
            
            # Look for login/submit button on password page
            login_button_selectors = [
                'input[type="submit"]',
                'input[name="btnLogin"]',
                'input[name="btnSubmit"]',
                'button[type="submit"]',
                'input[value*="Login"]',
                'input[value*="login"]'
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.query_selector(selector)
                    if login_button:
                        logger.info(f"Found login button with selector: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                logger.error("Login button not found on password page")
                return {
                    'success': False,
                    'error': 'Login button not found on password page',
                    'url': self.page.url
                }
            
            # Click login button
            await login_button.click()
            logger.info("Login button clicked")
            
            # Wait for final navigation
            try:
                await self.page.wait_for_navigation(timeout=15000)
                logger.info("Navigation detected after password submission")
            except:
                logger.info("No navigation detected, checking current page state")
                await self.page.wait_for_timeout(3000)
            
            # Take screenshot after login attempt
            await self.page.screenshot(path='after_final_login.png')
            logger.info("Post-login screenshot saved as after_final_login.png")
            
            # Check if login was successful
            login_result = await self.verify_login_success(roll_number)
            
            # If login successful, navigate directly to Overall Attendance page
            if login_result['success']:
                logger.info("Login successful, now navigating to Overall Attendance page...")
                attendance_success = await self.navigate_to_overall_attendance()
                if attendance_success:
                    logger.info("Successfully navigated to Overall Attendance page")
                else:
                    logger.warning("Could not navigate to Overall Attendance page")
            
            return login_result
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return {
                'success': False,
                'error': f'Login failed: {str(e)}',
                'url': self.page.url if self.page else 'unknown'
            }
    
    async def check_for_errors(self) -> str:
        """Check for error messages on the current page"""
        error_selectors = [
            '.error', '.alert-danger', '.text-danger',
            '[id*="error"]', '[class*="error"]',
            '[id*="Error"]', '[class*="Error"]',
            '.message', '.msg',
            'span[style*="color:red"]', 'span[style*="color: red"]',
            'div[style*="color:red"]', 'div[style*="color: red"]'
        ]
        
        error_message = ""
        for selector in error_selectors:
            try:
                error_elements = await self.page.query_selector_all(selector)
                for error_element in error_elements:
                    error_text = await error_element.text_content()
                    if error_text and error_text.strip():
                        error_message += error_text.strip() + " "
            except:
                continue
        
        return error_message.strip()
    
    async def verify_login_success(self, roll_number: str) -> Dict[str, Any]:
        """Verify if login was successful"""
        current_url = self.page.url
        page_title = await self.page.title()
        
        logger.info(f"Verifying login success - URL: {current_url}, Title: {page_title}")
        
        # Check for error messages first
        error_message = await self.check_for_errors()
        if error_message:
            logger.info(f"Found error message: {error_message}")
            return {
                'success': False,
                'error': error_message,
                'url': current_url,
                'page_title': page_title
            }
        
        # Look for positive indicators of successful login
        success_indicators = [
            'dashboard', 'home', 'student', 'portal', 'welcome',
            'attendance', 'marks', 'profile', 'main'
        ]
        
        # Check URL for success indicators
        url_success = any(indicator.lower() in current_url.lower() for indicator in success_indicators)
        
        # Check page title for success indicators  
        title_success = any(indicator.lower() in page_title.lower() for indicator in success_indicators)
        
        # Look for logout button or user info (indicates successful login)
        logout_selectors = [
            'a[href*="logout"], a:contains("Logout"), a:contains("Log out")',
            'button:contains("Logout"), button:contains("Log out")',
            '[id*="logout"], [class*="logout"]'
        ]
        
        has_logout = False
        for selector in logout_selectors:
            try:
                logout_element = await self.page.query_selector(selector)
                if logout_element:
                    has_logout = True
                    logger.info(f"Found logout element with selector: {selector}")
                    break
            except:
                continue
        
        # Look for student name or welcome message
        welcome_selectors = [
            '[id*="welcome"], [class*="welcome"]',
            '[id*="name"], [class*="name"]',
            '.student-name, .user-name',
            'span:contains("Welcome"), div:contains("Welcome")'
        ]
        
        has_welcome = False
        for selector in welcome_selectors:
            try:
                welcome_element = await self.page.query_selector(selector)
                if welcome_element:
                    welcome_text = await welcome_element.text_content()
                    if welcome_text and welcome_text.strip():
                        has_welcome = True
                        logger.info(f"Found welcome/name element: {welcome_text.strip()}")
                        break
            except:
                continue
        
        # Check if we're still on login page (negative indicator)
        login_indicators = ['login.aspx', '/login', 'signin', 'sign-in']
        still_on_login = any(indicator.lower() in current_url.lower() for indicator in login_indicators)
        
        # Determine success based on multiple factors
        if url_success or title_success or has_logout or has_welcome:
            self.authenticated = True
            logger.info(f"Login successful - Evidence: URL:{url_success}, Title:{title_success}, Logout:{has_logout}, Welcome:{has_welcome}")
            
            return {
                'success': True,
                'message': 'Login successful',
                'url': current_url,
                'page_title': page_title,
                'roll_number': roll_number,
                'evidence': {
                    'url_indicates_success': url_success,
                    'title_indicates_success': title_success,
                    'has_logout_button': has_logout,
                    'has_welcome_message': has_welcome
                }
            }
        elif still_on_login:
            logger.info("Still on login page - login likely failed")
            return {
                'success': False,
                'error': 'Still on login page - invalid credentials or login failed',
                'url': current_url,
                'page_title': page_title
            }
        else:
            # Uncertain - let's assume success if no obvious failure
            logger.info("Login status uncertain - assuming success based on navigation")
            self.authenticated = True
            
            return {
                'success': True,
                'message': 'Login appears successful (navigated away from login page)',
                'url': current_url,
                'page_title': page_title,
                'roll_number': roll_number,
                'note': 'Success inferred from navigation away from login page'
            }
    
    async def get_student_data(self) -> Dict[str, Any]:
        """
        Extract student data after successful login
        
        Returns:
            Dict containing student information and attendance data
        """
        if not self.authenticated:
            return {
                'success': False,
                'error': 'Not authenticated - login first'
            }
        
        try:
            logger.info("Extracting student data...")
            
            # Wait for page to load completely
            await self.page.wait_for_load_state('networkidle')
            
            # Extract basic student information
            student_info = {}
            
            # Common selectors for student information
            info_selectors = {
                'name': ['[id*="name"], [class*="name"], .student-name, #lblName, #Name',
                         '.info-name, [data-field="name"], span:contains("Name")'],
                'roll_number': ['[id*="roll"], [class*="roll"], .roll-number, #lblRoll, #RollNumber',
                               '.info-roll, [data-field="roll"], span:contains("Roll")'],
                'branch': ['[id*="branch"], [class*="branch"], .branch, #lblBranch, #Branch',
                          '.info-branch, [data-field="branch"], span:contains("Branch")'],
                'year': ['[id*="year"], [class*="year"], .year, #lblYear, #Year',
                        '.info-year, [data-field="year"], span:contains("Year")'],
                'semester': ['[id*="sem"], [class*="sem"], .semester, #lblSemester, #Semester',
                            '.info-semester, [data-field="semester"], span:contains("Semester")']
            }
            
            # Extract student information
            for field, selectors in info_selectors.items():
                for selector_group in selectors:
                    for selector in selector_group.split(', '):
                        try:
                            element = await self.page.query_selector(selector)
                            if element:
                                text = await element.text_content()
                                if text and text.strip():
                                    student_info[field] = text.strip()
                                    break
                        except:
                            continue
                    if field in student_info:
                        break
            
            # Look for attendance data
            attendance_data = await self.extract_attendance_data()
            
            # Look for marks/grades data
            marks_data = await self.extract_marks_data()
            
            result = {
                'success': True,
                'student_info': student_info,
                'attendance': attendance_data,
                'marks': marks_data,
                'extracted_at': datetime.now().isoformat(),
                'page_url': self.page.url
            }
            
            logger.info("Student data extracted successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting student data: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to extract data: {str(e)}'
            }
    
    async def extract_attendance_data(self) -> Dict[str, Any]:
        """Extract attendance information from the Overall Attendance page"""
        try:
            attendance_data = {}
            
            logger.info("Extracting attendance data from Overall Attendance page...")
            
            # Look specifically for the attendance grid (based on our debug findings)
            grid_selector = 'table[id*="grdOverallAtt"]'
            
            try:
                await self.page.wait_for_selector(grid_selector, timeout=10000)
                logger.info("Found attendance grid")
                
                # Extract the grid data using JavaScript evaluation for better reliability
                grid_data = await self.page.evaluate('''
                    () => {
                        const table = document.querySelector('table[id*="grdOverallAtt"]');
                        if (!table) return null;
                        
                        const rows = Array.from(table.querySelectorAll('tr'));
                        const data = [];
                        
                        rows.forEach((row, index) => {
                            const cells = Array.from(row.querySelectorAll('td, th'));
                            const rowData = cells.map(cell => {
                                const text = cell.textContent.trim();
                                // Filter out very long text (CSS/JS) and empty cells
                                return text.length > 50 ? '' : text;
                            }).filter(text => text !== '');
                            
                            if (rowData.length > 0) {
                                data.push(rowData);
                            }
                        });
                        
                        return data;
                    }
                ''')
                
                if grid_data and len(grid_data) > 0:
                    attendance_data['grid_data'] = grid_data
                    logger.info(f"Extracted grid data with {len(grid_data)} rows")
                    
                    # Process the grid data to extract meaningful attendance information
                    processed_data = self.process_attendance_grid(grid_data)
                    attendance_data.update(processed_data)
                
            except Exception as e:
                logger.warning(f"Could not find attendance grid: {str(e)}")
                
                # Fallback: Look for any tables with reasonable attendance data
                tables = await self.page.query_selector_all('table')
                
                for table in tables:
                    try:
                        # Extract table data with filtering
                        table_data = await table.evaluate(r'''
                            (table) => {
                                const rows = Array.from(table.querySelectorAll('tr'));
                                const data = [];
                                
                                rows.forEach(row => {
                                    const cells = Array.from(row.querySelectorAll('td, th'));
                                    const rowData = cells.map(cell => {
                                        const text = cell.textContent.trim();
                                        // Only include short, meaningful text
                                        if (text.length > 30 || text.includes('font-') || text.includes('css')) {
                                            return '';
                                        }
                                        return text;
                                    }).filter(text => text !== '');
                                    
                                    if (rowData.length > 2 && rowData.length < 10) {
                                        // Check if this looks like attendance data
                                        const hasNumbers = rowData.some(cell => /^\d+$/.test(cell));
                                        const hasPercentage = rowData.some(cell => /%/.test(cell));
                                        const hasMonth = rowData.some(cell => 
                                            /january|february|march|april|may|june|july|august|september|october|november|december/i.test(cell)
                                        );
                                        
                                        if (hasNumbers || hasPercentage || hasMonth) {
                                            data.push(rowData);
                                        }
                                    }
                                });
                                
                                return data;
                            }
                        ''')
                        
                        if table_data and len(table_data) > 0:
                            attendance_data['table_data'] = table_data
                            logger.info(f"Found fallback table with {len(table_data)} relevant rows")
                            
                            # Process this data as well
                            processed_data = self.process_attendance_grid(table_data)
                            attendance_data.update(processed_data)
                            break
                            
                    except Exception as e:
                        logger.debug(f"Error processing table: {str(e)}")
                        continue
            
            return attendance_data
            
        except Exception as e:
            logger.error(f"Error extracting attendance data: {str(e)}")
            return {'error': str(e)}
    
    def process_attendance_grid(self, grid_data):
        """Process the raw grid data to extract meaningful attendance metrics"""
        processed = {}
        
        if not grid_data or len(grid_data) < 2:
            return processed
        
        logger.info(f"Processing grid data: {grid_data}")
        
        # Look for headers to understand the structure
        headers = grid_data[0] if grid_data else []
        logger.info(f"Grid headers: {headers}")
        
        total_conducted = 0
        total_attended = 0
        monthly_records = []
        
        # Process each data row (skip header)
        for row in grid_data[1:]:
            if len(row) >= 3:  # At least month, conducted, attended
                try:
                    # Common patterns: [Month, Semester, Conducted, Attended, Percentage]
                    # or [Month/Semester, Conducted, Attended, Percentage]
                    
                    month_info = row[0] if row[0] else ""
                    
                    # Find conducted and attended numbers
                    conducted = 0
                    attended = 0
                    percentage = ""
                    
                    for cell in row[1:]:  # Skip first column (month)
                        cell_str = str(cell).strip()
                        
                        # Look for percentage
                        if '%' in cell_str:
                            percentage = cell_str
                        # Look for numbers that could be conducted/attended
                        elif cell_str.isdigit():
                            num = int(cell_str)
                            if 10 <= num <= 500:  # Reasonable range for class counts
                                if conducted == 0:
                                    conducted = num
                                elif attended == 0 and num <= conducted:
                                    attended = num
                    
                    # Only add if we have valid data and it's not a "Total" row
                    if conducted > 0 and attended > 0 and "total" not in month_info.lower():
                        monthly_records.append({
                            "month": month_info,
                            "conducted": conducted,
                            "attended": attended,
                            "percentage": percentage
                        })
                        total_conducted += conducted
                        total_attended += attended
                        logger.info(f"Added record: {month_info} - {conducted}/{attended} ({percentage})")
                
                except Exception as e:
                    logger.debug(f"Error processing row {row}: {str(e)}")
                    continue
        
        if total_conducted > 0 and total_attended > 0:
            overall_percentage = (total_attended / total_conducted) * 100
            processed.update({
                "total_classes_conducted": total_conducted,
                "total_classes_attended": total_attended,
                "overall_percentage": round(overall_percentage, 2),
                "monthly_records": monthly_records,
                "summary": f"Attendance: {total_attended}/{total_conducted} ({overall_percentage:.2f}%)"
            })
            logger.info(f"Processed attendance summary: {total_attended}/{total_conducted} ({overall_percentage:.2f}%)")
        
        return processed
    
    async def extract_marks_data(self) -> Dict[str, Any]:
        """Extract marks/grades information from the page"""
        try:
            marks_data = {}
            
            # Look for marks tables
            marks_selectors = [
                'table[id*="marks"], table[class*="marks"]',
                'table[id*="grade"], table[class*="grade"]',
                '.marks-table, .grades-table, .results-table'
            ]
            
            for selector in marks_selectors:
                tables = await self.page.query_selector_all(selector)
                
                for table in tables:
                    rows = await table.query_selector_all('tr')
                    table_data = []
                    
                    for row in rows:
                        cells = await row.query_selector_all('td, th')
                        row_data = []
                        
                        for cell in cells:
                            text = await cell.text_content()
                            if text:
                                row_data.append(text.strip())
                        
                        if row_data:
                            table_data.append(row_data)
                    
                    if table_data:
                        marks_data['table_data'] = table_data
                        break
            
            return marks_data
            
        except Exception as e:
            logger.error(f"Error extracting marks data: {str(e)}")
            return {'error': str(e)}
    
    async def navigate_to_attendance(self) -> bool:
        """Navigate to attendance page if available"""
        try:
            # Look for attendance links/buttons using XPath for text content
            attendance_selectors = [
                'a[href*="attendance"]',
                'a[href*="Attendance"]', 
                'button[id*="attendance"]',
                '[id*="attendance"]',
                '[class*="attendance"]'
            ]
            
            # Try CSS selectors first
            for selector in attendance_selectors:
                try:
                    links = await self.page.query_selector_all(selector)
                    for link in links:
                        await link.click()
                        await self.page.wait_for_load_state('networkidle')
                        logger.info("Navigated to attendance page via CSS selector")
                        return True
                except:
                    continue
            
            # Try XPath for text-based selection
            xpath_selectors = [
                "//a[contains(text(), 'Attendance')]",
                "//a[contains(text(), 'attendance')]", 
                "//button[contains(text(), 'Attendance')]",
                "//div[contains(text(), 'Attendance')]",
                "//span[contains(text(), 'Attendance')]"
            ]
            
            for xpath in xpath_selectors:
                try:
                    elements = await self.page.locator(xpath).all()
                    for element in elements:
                        await element.click()
                        await self.page.wait_for_load_state('networkidle')
                        logger.info("Navigated to attendance page via XPath")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to attendance: {str(e)}")
            return False
    
    async def navigate_to_marks(self) -> bool:
        """Navigate to marks/results page if available"""
        try:
            # Look for marks/results links using various selectors
            marks_selectors = [
                'a[href*="marks"]',
                'a[href*="result"]',
                'a[href*="grade"]',
                'button[id*="marks"]',
                '[id*="marks"]',
                '[class*="marks"]',
                '[class*="result"]'
            ]
            
            # Try CSS selectors first
            for selector in marks_selectors:
                try:
                    links = await self.page.query_selector_all(selector)
                    for link in links:
                        await link.click()
                        await self.page.wait_for_load_state('networkidle')
                        logger.info("Navigated to marks page via CSS selector")
                        return True
                except:
                    continue
            
            # Try XPath for text-based selection
            xpath_selectors = [
                "//a[contains(text(), 'Marks')]",
                "//a[contains(text(), 'marks')]",
                "//a[contains(text(), 'Results')]", 
                "//a[contains(text(), 'Grade')]",
                "//button[contains(text(), 'Marks')]",
                "//div[contains(text(), 'Marks')]"
            ]
            
            for xpath in xpath_selectors:
                try:
                    elements = await self.page.locator(xpath).all()
                    for element in elements:
                        await element.click()
                        await self.page.wait_for_load_state('networkidle')
                        logger.info("Navigated to marks page via XPath")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to marks: {str(e)}")
            return False

    async def navigate_to_student_dashboard(self) -> bool:
        """Navigate to Student Dashboard after login"""
        try:
            logger.info("Looking for Student Dashboard link...")
            
            # Take a screenshot to see available options
            await self.page.screenshot(path='post_login_options.png')
            logger.info("Screenshot saved as post_login_options.png")
            
            # Look for Student Dashboard link using various selectors
            dashboard_selectors = [
                'a[href*="dashboard"]',
                'a[href*="Dashboard"]',
                'a[href*="student"]',
                'a[href*="Student"]'
            ]
            
            # Try CSS selectors first
            for selector in dashboard_selectors:
                try:
                    links = await self.page.query_selector_all(selector)
                    for link in links:
                        link_text = await link.text_content()
                        if link_text and ('dashboard' in link_text.lower() or 'student' in link_text.lower()):
                            logger.info(f"Found dashboard link with text: {link_text}")
                            await link.click()
                            await self.page.wait_for_load_state('networkidle')
                            logger.info("Successfully clicked Student Dashboard link")
                            return True
                except:
                    continue
            
            # Try XPath for text-based selection - looking for "Student Dashboard" specifically
            xpath_selectors = [
                "//a[contains(text(), 'Student Dashboard')]",
                "//a[contains(text(), 'Student Dashbord')]",  # Handle potential typo
                "//a[contains(text(), 'Click Here to go Student Dashboard')]",
                "//a[contains(text(), 'Click Here to go Student Dashbord')]",
                "//a[contains(text(), 'Dashboard')]",
                "//a[contains(text(), 'dashboard')]",
                "//button[contains(text(), 'Student Dashboard')]",
                "//div[contains(text(), 'Student Dashboard')]"
            ]
            
            for xpath in xpath_selectors:
                try:
                    elements = await self.page.locator(xpath).all()
                    for element in elements:
                        element_text = await element.text_content()
                        logger.info(f"Found potential dashboard element: {element_text}")
                        await element.click()
                        await self.page.wait_for_load_state('networkidle')
                        logger.info("Successfully navigated to Student Dashboard via XPath")
                        
                        # Take screenshot after navigation
                        await self.page.screenshot(path='student_dashboard.png')
                        logger.info("Screenshot saved as student_dashboard.png")
                        return True
                except Exception as e:
                    logger.debug(f"XPath selector failed: {xpath}, error: {str(e)}")
                    continue
            
            # If no specific dashboard link found, look for any links that might lead to student info
            logger.info("Looking for any student-related navigation links...")
            
            # Get all links and check their text content
            all_links = await self.page.query_selector_all('a')
            for link in all_links:
                try:
                    link_text = await link.text_content()
                    if link_text:
                        link_text = link_text.strip().lower()
                        if any(keyword in link_text for keyword in ['student', 'dashboard', 'home', 'main', 'portal']):
                            logger.info(f"Found potential navigation link: {link_text}")
                            await link.click()
                            await self.page.wait_for_load_state('networkidle')
                            logger.info("Clicked potential student navigation link")
                            
                            # Take screenshot
                            await self.page.screenshot(path='after_navigation.png')
                            logger.info("Screenshot saved as after_navigation.png")
                            return True
                except:
                    continue
            
            logger.warning("No Student Dashboard link found")
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to Student Dashboard: {str(e)}")
            return False

    async def navigate_to_overall_attendance(self) -> bool:
        """Navigate directly to Overall Attendance page after login"""
        try:
            logger.info("Navigating directly to Overall Attendance page...")
            
            # Direct URL to Overall Attendance page
            attendance_url = "https://geethanjali-erp.com/GCET/StudentLogin/Student/StudentOverallAttendance.aspx"
            
            # Navigate directly to the attendance page
            await self.page.goto(attendance_url, wait_until='networkidle', timeout=30000)
            logger.info(f"Navigated to: {attendance_url}")
            
            # Wait for page to load completely
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Take screenshot of attendance page
            await self.page.screenshot(path='overall_attendance_page.png')
            logger.info("Screenshot saved as overall_attendance_page.png")
            
            # Verify we're on the correct page
            current_url = self.page.url
            page_title = await self.page.title()
            
            logger.info(f"Current URL: {current_url}")
            logger.info(f"Page Title: {page_title}")
            
            # Check if we successfully reached the attendance page
            if "StudentOverallAttendance" in current_url or "attendance" in page_title.lower():
                logger.info("Successfully reached Overall Attendance page")
                return True
            else:
                logger.warning("May not be on the correct attendance page")
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to Overall Attendance page: {str(e)}")
            
            # Fallback: Try navigation through dashboard menu
            logger.info("Trying fallback navigation through dashboard menu...")
            return await self.navigate_to_attendance_via_menu()

    async def navigate_to_attendance_via_menu(self) -> bool:
        """Fallback method: Navigate to attendance through dashboard menu"""
        try:
            logger.info("Attempting navigation through Academics menu...")
            
            # Look for Academics menu/link
            academics_selectors = [
                'a[href*="academic"]',
                'a[href*="Academic"]',
                '[id*="academic"]',
                '[class*="academic"]'
            ]
            
            # Try CSS selectors for Academics
            for selector in academics_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements:
                        element_text = await element.text_content()
                        if element_text and 'academic' in element_text.lower():
                            logger.info(f"Found Academics menu: {element_text}")
                            await element.click()
                            await self.page.wait_for_timeout(2000)
                            break
                except:
                    continue
            
            # Look for Overall Attendance link
            attendance_xpath_selectors = [
                "//a[contains(text(), 'Overall Attendance')]",
                "//a[contains(text(), 'Overall Attendence')]",  # Handle typo
                "//a[contains(text(), 'Attendance')]",
                "//a[contains(text(), 'attendance')]",
                "//button[contains(text(), 'Overall Attendance')]",
                "//div[contains(text(), 'Overall Attendance')]"
            ]
            
            for xpath in attendance_xpath_selectors:
                try:
                    elements = await self.page.locator(xpath).all()
                    for element in elements:
                        element_text = await element.text_content()
                        logger.info(f"Found attendance link: {element_text}")
                        await element.click()
                        await self.page.wait_for_load_state('networkidle')
                        
                        # Take screenshot
                        await self.page.screenshot(path='attendance_via_menu.png')
                        logger.info("Screenshot saved as attendance_via_menu.png")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error in fallback navigation: {str(e)}")
            return False

async def scrape_student_data(roll_number: str) -> Dict[str, Any]:
    """
    Main function to scrape student data using Playwright
    
    Args:
        roll_number: Student roll number
        
    Returns:
        Dict containing all extracted data
    """
    async with PlaywrightERPScraper() as scraper:
        # Login
        login_result = await scraper.login(roll_number)
        
        if not login_result['success']:
            return login_result
        
        # Extract basic data
        student_data = await scraper.get_student_data()
        
        if student_data['success']:
            # Try to get more detailed attendance data
            if await scraper.navigate_to_attendance():
                detailed_attendance = await scraper.extract_attendance_data()
                student_data['detailed_attendance'] = detailed_attendance
            
            # Try to get detailed marks data
            if await scraper.navigate_to_marks():
                detailed_marks = await scraper.extract_marks_data()
                student_data['detailed_marks'] = detailed_marks
        
        return student_data

# Test function
async def test_scraper():
    """Test function for development"""
    test_roll = "23R11A0590"  # Using provided roll number
    
    result = await scrape_student_data(test_roll)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    # Run test
    asyncio.run(test_scraper())
