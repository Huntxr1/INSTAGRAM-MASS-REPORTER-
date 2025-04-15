import random
import time
import os
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
import requests
from fake_useragent import UserAgent
from queue import Queue

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

# Function to create empty proxy files if they don't exist
def create_proxy_files():
    proxy_files = ['http_proxies.txt', 'socks4_proxies.txt', 'socks5_proxies.txt']
    for filename in proxy_files:
        if not os.path.exists(filename):
            with open(filename, 'w') as file:
                pass  # Create empty file
            logging.info(f"Created empty {filename}")
        else:
            logging.info(f"{filename} already exists, using it")

# Function to load and validate proxies from all files
def load_all_proxies():
    proxies = []
    for file in ['http_proxies.txt', 'socks4_proxies.txt', 'socks5_proxies.txt']:
        if os.path.exists(file):
            with open(file, 'r') as f:
                file_proxies = [line.strip() for line in f if line.strip()]
                for proxy in file_proxies:
                    if ':' in proxy and len(proxy.split(':')) == 2:
                        proxies.append(proxy)
                    else:
                        logging.warning(f"Invalid proxy format in {file}: {proxy}")
            logging.info(f"Loaded {len(file_proxies)} proxies from {file}")
        else:
            logging.warning(f"{file} not found")
    return proxies

# Instagram Reporter class
class InstagramReporter:
    def __init__(self, username, password, proxies):
        self.username = username
        self.password = password
        self.proxies = proxies
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
        if self.proxies:
            proxy = random.choice(self.proxies)
            logging.info(f"{self.username} using proxy: {proxy}")
            session.proxies = {
                "http": f"http://{proxy}",
                "https": f"socks5://{proxy}" if "1080" in proxy else f"http://{proxy}",
            }
        else:
            logging.warning(f"No proxies available for {self.username}, proceeding without proxy")
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
def mass_report(target_username, accounts, proxies, num_reports_per_account=1, max_workers=5):
    create_proxy_files()
    if not proxies:
        logging.error("No proxies found in files. Need proxies to proceed.")
        return
    if len(proxies) < len(accounts):
        logging.warning(f"Only {len(proxies)} proxies available for {len(accounts)} accounts. Some accounts may share proxies.")

    report_queue = Queue()
    for i in range(len(accounts) * num_reports_per_account):
        report_queue.put(i + 1)

    reporters = [InstagramReporter(username, password, proxies) for username, password in accounts]

    logging.info(f"Starting {len(accounts) * num_reports_per_account} reports for {target_username} with {max_workers} threads")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for reporter in reporters:
            executor.submit(worker, reporter, target_username, report_queue)

    report_queue.join()
    logging.info("All reports completed")

# Hardcoded list of 30 Instagram accounts (replace with real credentials)
accounts = [
    ("user1_insta", "pass1234"), ("user2_insta", "secure567"), ("user3_insta", "mypwd890"),
    ("user4_insta", "instapass1"), ("user5_insta", "pass4321"), ("user6_insta", "login987"),
    ("user7_insta", "secret321"), ("user8_insta", "pwd654"), ("user9_insta", "insta111"),
    ("user10_insta", "pass222"), ("user11_insta", "login333"), ("user12_insta", "secure444"),
    ("user13_insta", "mypwd555"), ("user14_insta", "instapass6"), ("user15_insta", "pass777"),
    ("user16_insta", "login888"), ("user17_insta", "secret999"), ("user18_insta", "pwd000"),
    ("user19_insta", "instaabc"), ("user20_insta", "passdef"), ("user21_insta", "loginghi"),
    ("user22_insta", "securejkl"), ("user23_insta", "mypwdmno"), ("user24_insta", "instapqr"),
    ("user25_insta", "passstu"), ("user26_insta", "loginvwx"), ("user27_insta", "secretyz"),
    ("user28_insta", "pwd123abc"), ("user29_insta", "insta456def"), ("user30_insta", "pass789ghi")
]

# Main execution
if __name__ == "__main__":
    # Display ASCII art with animated background
    display_ascii_art()

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

    # Load proxies
    proxies = load_all_proxies()
    if not proxies:
        logging.error("No proxies available. Cannot report.")
        exit(1)

    # Proceed with reporting
    mass_report(target_user, accounts, proxies, num_reports_per_account=num_reports, max_workers=5)