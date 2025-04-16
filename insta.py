import random
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import requests
from fake_useragent import UserAgent
from queue import Queue
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to generate ANSI color codes for gradient effect
def get_gradient_color(step, total_steps):
    colors = [
        (0, 255, 0),    # Green
        (255, 255, 0),  # Yellow
        (255, 255, 255),# White
        (255, 105, 180),# Pink
        (0, 191, 255),  # Sky Blue
        (255, 165, 0),  # Orange
        (128, 0, 128)   # Purple
    ]
    idx = (step % total_steps) / total_steps * (len(colors) - 1)
    i = int(idx)
    frac = idx - i
    r1, g1, b1 = colors[i]
    r2, g2, b2 = colors[i + 1] if i + 1 < len(colors) else colors[i]
    r = int(r1 + (r2 - r1) * frac)
    g = int(g1 + (g2 - g1) * frac)
    b = int(b1 + (b2 - b1) * frac)
    return f"\033[48;2;{r};{g};{b}m"

# Function to display ASCII art with animated background
def display_ascii_art():
    ascii_art = """
█ █▄░█ █▀ ▀█▀ ▄▀█
█ █░▀█ ▄█ ░█░ █▀█

█▀█ █▀▀ █▀█ █▀█ █▀█ ▀█▀ █▀▀ █▀█
█▀▄ ██▄ █▀▀ █▄█ █▀▄ ░█░ ██▄ █▀▄

𝗜𝗡𝗦𝗧𝗔𝗚𝗥𝗔𝗠 𝗥𝗘𝗣𝗢𝗥𝗧𝗘𝗥

𝗦C𝗥𝗜𝗣𝗧 𝗕𝗬 𝗦𝗛𝗥𝗜𝗝𝗔𝗡 𝗧𝗜𝗪𝗔𝗥𝗜 
"""
    lines = ascii_art.split('\n')
    total_steps = 50  # Controls speed of color change
    try:
        for step in range(total_steps):
            os.system('cls' if os.name == 'nt' else 'clear')  # Clear terminal
            for line in lines:
                color = get_gradient_color(step, total_steps)
                reset = "\033[0m"
                # Pad line to ensure full background coverage
                padded_line = line.ljust(50)
                print(f"{color}{padded_line}{reset}")
            time.sleep(0.1)  # Animation speed
    except KeyboardInterrupt:
        pass
    finally:
        os.system('cls' if os.name == 'nt' else 'clear')  # Clear terminal after animation
        # Print static version for script continuation
        print(ascii_art)

# Function to load accounts from accounts.json
def load_accounts():
    accounts_file = 'accounts.json'
    if not os.path.exists(accounts_file):
        logging.error(f"{accounts_file} not found. Please create it with account credentials.")
        return []
    
    try:
        with open(accounts_file, 'r') as f:
            accounts_data = json.load(f)
            accounts = []
            for account in accounts_data:
                username = account.get('username')
                password = account.get('password')
                if username and password:
                    accounts.append((username, password))
                else:
                    logging.warning(f"Invalid account entry in {accounts_file}: {account}")
            logging.info(f"Loaded {len(accounts)} accounts from {accounts_file}")
            return accounts
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing {accounts_file}: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error reading {accounts_file}: {e}")
        return []

# Instagram Reporter class
class InstagramReporter:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.ua = UserAgent()
        self.base_url = "https://www.instagram.com"
        self.lock = threading.Lock()
        # Define possible reporting reasons
        self.report_reasons = [
            "spam",              # Automated or repetitive content
            "inappropriate",     # Offensive or harmful content
            "harassment",        # Bullying or abusive behavior
            "impersonation",     # Pretending to be someone else
            "scam",              # Fraudulent or deceptive content
            "hate_speech",       # Discriminatory or hateful content
            "violence",          # Threats or violent content
            "nudity",            # Explicit or adult content
        ]

    def get_session(self):
        session = requests.Session()
        session.headers.update({
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": self.base_url,
        })
        return session

    def login(self, session, retries=2):
        for attempt in range(retries):
            try:
                response = session.get(f"{self.base_url}/accounts/login/", timeout=5)
                csrf_token = response.cookies.get("csrftoken")
                if not csrf_token:
                    logging.error(f"No CSRF token for {self.username}")
                    time.sleep(1)
                    continue

                payload = {
                    "username": self.username,
                    "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{self.password}",
                    "queryParams": {},
                    "optIntoOneTap": "false"
                }
                headers = {
                    "X-CSRFToken": csrf_token,
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                login_url = f"{self.base_url}/accounts/login/ajax/"
                response = session.post(login_url, data=payload, headers=headers, timeout=5)
                if response.status_code == 200 and response.json().get("authenticated"):
                    logging.info(f"Logged in with {self.username}")
                    return session
                else:
                    logging.warning(f"Login attempt {attempt + 1} failed for {self.username}: {response.text}")
                    time.sleep(1)
            except Exception as e:
                logging.warning(f"Login error for {self.username} (attempt {attempt + 1}): {e}")
                time.sleep(1)
        logging.error(f"Login failed for {self.username} after {retries} attempts")
        return None

    def report_user(self, target_username, reason=None):
        session = self.get_session()
        session = self.login(session)
        if not session:
            return False

        # Select a random reason if none provided
        selected_reason = random.choice(self.report_reasons) if reason is None else reason
        if selected_reason not in self.report_reasons:
            logging.warning(f"Invalid reason '{selected_reason}' for {self.username}, defaulting to 'spam'")
            selected_reason = "spam"

        try:
            profile_url = f"{self.base_url}/{target_username}/"
            response = session.get(profile_url, timeout=5)
            if response.status_code != 200:
                logging.error(f"Failed to access {target_username}'s profile with {self.username}")
                return False

            user_id = None
            try:
                user_id = response.text.split('"id":"')[1].split('"')[0]
            except:
                logging.error(f"Failed to extract user ID for {target_username} with {self.username}")
                return False

            report_url = f"{self.base_url}/users/{user_id}/report/"
            payload = {
                "source_name": "",
                "reason": selected_reason,
                "frx_prompt_request_type": "1"
            }
            headers = {
                "X-CSRFToken": session.cookies.get("csrftoken"),
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            response = session.post(report_url, data=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                logging.info(f"Successfully reported {target_username} with {self.username} for '{selected_reason}'")
                return True
            else:
                logging.error(f"Report failed for {target_username} with {self.username} for '{selected_reason}': {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"Report error for {target_username} with {self.username} for '{selected_reason}': {e}")
            return False

# Worker function for multithreading
def worker(reporter, target_username, report_queue):
    while not report_queue.empty():
        report_count = report_queue.get()
        # Randomly select a reason for each report
        success = reporter.report_user(target_username, reason=None)
        with reporter.lock:
            if success:
                logging.info(f"Report #{report_count} completed by {reporter.username}")
            else:
                logging.warning(f"Report #{report_count} failed by {reporter.username}")
        report_queue.task_done()
        time.sleep(random.uniform(0.5, 1.5))

# Main function to manage reporting
def mass_report(target_username, accounts, num_reports_per_account=1, max_workers=5):
    report_queue = Queue()
    for i in range(len(accounts) * num_reports_per_account):
        report_queue.put(i + 1)

    reporters = [InstagramReporter(username, password) for username, password in accounts]

    logging.info(f"Starting {len(accounts) * num_reports_per_account} reports for {target_username} with {max_workers} threads")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for reporter in reporters:
            executor.submit(worker, reporter, target_username, report_queue)

    report_queue.join()
    logging.info("All reports completed")

# Main execution
if __name__ == "__main__":
    # Display ASCII art with animated background
    display_ascii_art()

    # Load accounts from accounts.json
    accounts = load_accounts()
    if not accounts:
        logging.error("No valid accounts loaded from accounts.json. Exiting.")
        exit(1)

    # Prompt for target username with retries
    for _ in range(3):
        target_user = input("Enter the Instagram username to report: ").strip()
        if target_user:
            break
        logging.warning("Username cannot be empty. Try again.")
    else:
        logging.error("No valid username provided after 3 attempts. Exiting.")
        exit(1)

    # Prompt for number of reports per account with retries
    for _ in range(3):
        try:
            num_reports = int(input("Enter the number of reports per account: ").strip())
            if num_reports < 1:
                logging.warning("Number of reports must be at least 1. Try again.")
                continue
            break
        except ValueError:
            logging.warning("Invalid number of reports. Please enter a number. Try again.")
    else:
        logging.error("No valid number of reports provided after 3 attempts. Exiting.")
        exit(1)

    # Proceed with reporting
    mass_report(target_user, accounts, num_reports_per_account=num_reports, max_workers=5)
