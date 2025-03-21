import requests
import time
import os
import webbrowser
import keyboard
import sys
from requests.exceptions import RequestException
from threading import Thread
from colorama import init, Fore, Style
from itertools import cycle
import threading

init(autoreset=True)

def watermark():
    return """\n$$\                           $$\                                           $$$\   
$$ |                          $$ |                                           \$$\  
$$$$$$$\   $$$$$$\  $$$$$$$\  $$ |  $$\  $$$$$$\   $$$$$$\        $$\         \$$\ 
$$  __$$\ $$  __$$\ $$  __$$\ $$ | $$  |$$  __$$\ $$  __$$\       \__|         $$ |
$$ |  $$ |$$ /  $$ |$$ |  $$ |$$$$$$  / $$$$$$$$ |$$ |  \__|                   $$ |
$$ |  $$ |$$ |  $$ |$$ |  $$ |$$  _$$<  $$   ____|$$ |            $$\         $$  |
$$$$$$$  |\$$$$$$  |$$ |  $$ |$$ | \$$\ \$$$$$$$\ $$ |            \__|      $$$  / 
\_______/  \______/ \__|  \__|\__|  \__| \_______|\__|                      \___/  
                                                                                   
                                                                                   
                                                                                   """

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def read_usernames(file_path):
    try:
        if not os.path.exists(file_path):
            print(f"Error: '{file_path}' not found!")
            print("Please create a file named 'usernames.txt' and add Roblox usernames (one per line)")
            input("Press Enter to exit...")
            sys.exit(1)
            
        with open(file_path, 'r') as f:
            usernames = [line.strip() for line in f if line.strip() and not line.strip().startswith('[')]
            
        if not usernames:
            print("Error: 'usernames.txt' is empty!")
            print("Please add Roblox usernames to the file (one per line)")
            input("Press Enter to exit...")
            sys.exit(1)
            
        return usernames
    except Exception as e:
        print(f"Error reading usernames file: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)

def get_user_ids(usernames):
    try:
        response = requests.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": usernames, "excludeBannedUsers": True}
        )
        response.raise_for_status()
        data = response.json()["data"]
        
        if not data:
            print("Error: None of the provided usernames were found!")
            input("Press Enter to exit...")
            sys.exit(1)
            
        user_map = {}
        not_found = []
        for username in usernames:
            found = False
            for user in data:
                if user["name"].lower() == username.lower():
                    user_map[user["name"]] = {
                        "id": user["id"],
                        "display_name": user["displayName"]
                    }
                    found = True
                    break
            if not found:
                not_found.append(username)
        
        if not_found:
            print("\nWarning: The following users were not found:")
            for username in not_found:
                print(f"- {username}")
            print()
            
        return user_map
    except RequestException as e:
        print(f"Network Error: Could not connect to Roblox API")
        print(f"Details: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"Error getting user IDs: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)

def spinner(stop_event):
    spinner = cycle(['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷'])
    while not stop_event.is_set():
        sys.stdout.write(f"\r{Fore.CYAN}Loading {next(spinner)} ")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write('\r' + ' ' * 20 + '\r')

def with_loading(message):
    def decorator(func):
        def wrapper(*args, **kwargs):
            stop_event = threading.Event()
            spinner_thread = threading.Thread(target=spinner, args=(stop_event,))
            print(f"\n{Fore.CYAN}{message}")
            spinner_thread.start()
            try:
                result = func(*args, **kwargs)
            finally:
                stop_event.set()
                spinner_thread.join()
            return result
        return wrapper
    return decorator

@with_loading("Fetching presence data")
def get_user_presence(user_ids):
    try:
        response = requests.post(
            "https://presence.roblox.com/v1/presence/users",
            json={"userIds": user_ids}
        )
        response.raise_for_status()
        return {p["userId"]: {
            "status": ["Offline", "Website", "In-Game"][p["userPresenceType"]],
            "emoji": {"Offline": "🔴", "Website": "🔵", "In-Game": "🟢"}[["Offline", "Website", "In-Game"][p["userPresenceType"]]]
        } for p in response.json()["userPresences"]}
    except RequestException as e:
        print(f"Network Error: Could not fetch user presence")
        print(f"Details: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"Error getting user presence: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)

def get_mutual_friends(user_id, all_user_ids):
    try:
        time.sleep(0.5)
        
        response = requests.get(
            f"https://friends.roblox.com/v1/users/{user_id}/friends",
            headers={'Cache-Control': 'no-cache'}
        )
        
        if response.status_code == 429:
            print(f"{Fore.YELLOW}Rate limited, waiting 5 seconds...{Style.RESET_ALL}")
            time.sleep(5)
            response = requests.get(
                f"https://friends.roblox.com/v1/users/{user_id}/friends",
                headers={'Cache-Control': 'no-cache'}
            )
        
        response.raise_for_status()
        return [f for f in response.json().get("data", []) if f["id"] in all_user_ids]
    except RequestException as e:
        if "429" in str(e):
            print(f"{Fore.YELLOW}Warning: Rate limited while fetching mutual friends. Some data may be missing.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Warning: Could not fetch mutual friends for user {user_id}{Style.RESET_ALL}")
        return []

def get_mutual_friends_with_cache(user_id, all_user_ids, cache=None):
    if cache is None:
        cache = {}
    
    if user_id in cache:
        return cache[user_id]
        
    try:
        response = requests.get(
            f"https://friends.roblox.com/v1/users/{user_id}/friends",
            headers={'Cache-Control': 'no-cache'}
        )
        
        if response.status_code == 429:
            return None
        
        response.raise_for_status()
        mutuals = [f for f in response.json().get("data", []) if f["id"] in all_user_ids]
        cache[user_id] = mutuals
        return mutuals
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not fetch mutual friends for {user_id} ({str(e)}){Style.RESET_ALL}")
        cache[user_id] = []
        return []

def get_thumbnail(user_id):
    try:
        response = requests.get(
            f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png"
        )
        response.raise_for_status()
        return response.json()["data"][0]["imageUrl"]
    except Exception:
        return "https://tr.rbxcdn.com/53eb9b17fe1432a809c73a13889b5006/720/720/AvatarHeadshot/Png"

def print_simple_output(username, presence, display_name):
    status_colors = {
        "Offline": Fore.RED,
        "Website": Fore.BLUE,
        "In-Game": Fore.GREEN
    }
    display_bracket = f"({display_name:^25})"
    print(f"{Fore.YELLOW}{username:<20}{Style.RESET_ALL} {Fore.CYAN}{display_bracket}{Style.RESET_ALL} - {presence['emoji']} {status_colors[presence['status']]}{presence['status']}{Style.RESET_ALL}")

def print_advanced_output(username, data, presence, thumbnail, mutuals):
    print(f"\n{Fore.YELLOW}{username}:{Style.RESET_ALL}")
    print(f"Display: {Fore.CYAN}{data['display_name']}{Style.RESET_ALL}")
    print(f"Status: {presence['emoji']} {presence['status']}")
    if mutuals:
        print(f"\n{Fore.GREEN}Mutual friends:{Style.RESET_ALL}")
        for i, friend in enumerate(mutuals, 1):
            print(f"  {i}. {friend['name']} ({friend['id']})")
    else:
        print(f"\n{Fore.RED}No mutual friends{Style.RESET_ALL}")
    print("─" * 40)

def generate_html(user_data, presence_data, thumbnails, mutuals):
    filename = "roblox_users.html"
    
    if os.path.exists(filename):
        os.remove(filename)
    
    html = """
    <html>
    <head>
        <title>Roblox User Info</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {
                --background-color: white;
                --text-color: #333;
                --card-bg: white;
                --card-border: #ddd;
                --offline-color: #ff6b6b;
                --website-color: #4dabf7;
                --ingame-color: #51cf66;
                --accent-color: #339af0;
                --btn-text-color: #333; /* Added for button text color */
            }
            
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: var(--background-color);
                color: var(--text-color);
                transition: all 0.3s ease;
            }
            
            .dark-mode {
                --background-color: #1a1a1a;
                --text-color: #f0f0f0;
                --card-bg: #2d2d2d;
                --card-border: #444;
                --offline-color: #c92a2a;
                --website-color: #1c7ed6;
                --ingame-color: #2b8a3e;
                --accent-color: #1864ab;
                --btn-text-color: #f0f0f0; /* Added for button text color in dark mode */
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 1px solid var(--card-border);
                flex-wrap: wrap;
            }
            
            .controls {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            
            #search-input {
                padding: 8px 12px;
                border: 1px solid var(--card-border);
                border-radius: 4px;
                flex-grow: 1;
                min-width: 200px;
                background-color: var(--card-bg);
                color: var(--text-color);
            }
            
            button {
                padding: 8px 15px;
                background-color: var(--accent-color);
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            
            button:hover {
                background-color: #2174c7;
            }
            
            .stats {
                margin-bottom: 20px;
                padding: 10px;
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 4px;
                display: flex;
                gap: 15px;
                flex-wrap: wrap;
            }
            
            .stat-item {
                display: flex;
                align-items: center;
                gap: 5px;
            }
            
            .status-dot {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                display: inline-block;
            }
            
            .offline { background-color: var(--offline-color); }
            .website { background-color: var(--website-color); }
            .ingame { background-color: var(--ingame-color); }
            
            .user-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 20px;
            }
            
            .user {
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                border-radius: 8px;
                padding: 15px;
                transition: transform 0.2s, box-shadow 0.2s;
                position: relative;
                overflow: hidden;
            }
            
            .user:hover {
                transform: translateY(-3px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }
            
            .status-indicator {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 5px;
            }
            
            .status-Offline { background-color: var(--offline-color); }
            .status-Website { background-color: var(--website-color); }
            .status-In-Game { background-color: var(--ingame-color); }
            
            .user-header {
                display: flex;
                align-items: center;
                gap: 15px;
                padding-top: 5px;
            }
            
            .user img {
                width: 70px;
                height: 70px;
                border-radius: 50%;
                object-fit: cover;
            }
            
            .user-name h2 {
                margin: 0;
                font-size: 18px;
            }
            
            .user-name p {
                margin: 5px 0;
                color: #888;
            }
            
            .user-details {
                margin-top: 15px;
            }
            
            .mutuals {
                margin-top: 15px;
            }
            
            .mutuals h3 {
                font-size: 16px;
                margin-bottom: 10px;
            }
            
            .mutuals ul {
                max-height: 150px;
                overflow-y: auto;
                padding-left: 20px;
                margin: 0;
            }
            
            .mutuals li {
                margin-bottom: 5px;
            }
            
            .filter-buttons {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            
            .filter-btn {
                padding: 5px 10px;
                border-radius: 20px;
                background-color: var(--card-bg);
                border: 1px solid var(--card-border);
                cursor: pointer;
                color: var(--btn-text-color); /* Added to ensure text visibility */
                font-weight: bold; /* Make text more readable */
            }
            
            .filter-btn.active {
                background-color: var(--accent-color);
                color: white; /* Keeps active button text white for contrast */
            }
            
            .toggle-theme {
                background-color: transparent;
                color: var(--text-color);
                border: 1px solid var(--card-border);
            }
            
            .timestamp {
                margin-top: 20px;
                text-align: center;
                font-size: 14px;
                color: #888;
            }
            
            @media (max-width: 600px) {
                .user-grid {
                    grid-template-columns: 1fr;
                }
                .header {
                    flex-direction: column;
                    align-items: flex-start;
                }
                .controls {
                    width: 100%;
                }
            }
        </style>
        <script>
            function scrollToUser(userId) {
                const element = document.getElementById(userId);
                element.scrollIntoView({behavior: "smooth", block: "start"});
                // Highlight the user card briefly
                element.style.boxShadow = '0 0 0 3px var(--accent-color)';
                setTimeout(() => {
                    element.style.boxShadow = '';
                }, 2000);
            }
            
            function searchUsers() {
                const input = document.getElementById('search-input').value.toLowerCase();
                const users = document.getElementsByClassName('user');
                let visible = 0;
                
                for (let user of users) {
                    const username = user.querySelector('.user-name h2').textContent.toLowerCase();
                    const displayName = user.querySelector('.display-name').textContent.toLowerCase();
                    const mutuals = user.querySelector('.mutuals').textContent.toLowerCase();
                    
                    if (username.includes(input) || displayName.includes(input) || mutuals.includes(input)) {
                        user.style.display = '';
                        visible++;
                    } else {
                        user.style.display = 'none';
                    }
                }
                
                document.getElementById('visible-count').textContent = visible;
            }
            
            function filterByStatus(status) {
                const users = document.getElementsByClassName('user');
                const buttons = document.getElementsByClassName('filter-btn');
                let visible = 0;
                
                // Update active button
                for (let btn of buttons) {
                    btn.classList.remove('active');
                }
                document.getElementById('btn-' + status).classList.add('active');
                
                for (let user of users) {
                    if (status === 'all') {
                        user.style.display = '';
                        visible++;
                    } else {
                        const userStatus = user.getAttribute('data-status');
                        if (userStatus === status) {
                            user.style.display = '';
                            visible++;
                        } else {
                            user.style.display = 'none';
                        }
                    }
                }
                
                document.getElementById('visible-count').textContent = visible;
            }
            
            function toggleTheme() {
                document.body.classList.toggle('dark-mode');
                const button = document.getElementById('theme-toggle');
                if (document.body.classList.contains('dark-mode')) {
                    button.textContent = '☀️ Light Mode';
                    localStorage.setItem('theme', 'dark');
                } else {
                    button.textContent = '🌙 Dark Mode';
                    localStorage.setItem('theme', 'light');
                }
            }
            
            // Apply saved theme when page loads
            window.onload = function() {
                const savedTheme = localStorage.getItem('theme');
                if (savedTheme === 'dark') {
                    document.body.classList.add('dark-mode');
                    document.getElementById('theme-toggle').textContent = '☀️ Light Mode';
                }
                
                // Set initial stats
                document.getElementById('total-count').textContent = document.getElementsByClassName('user').length;
                document.getElementById('visible-count').textContent = document.getElementsByClassName('user').length;
                
                const offlineUsers = document.querySelectorAll('[data-status="Offline"]').length;
                const websiteUsers = document.querySelectorAll('[data-status="Website"]').length;
                const ingameUsers = document.querySelectorAll('[data-status="In-Game"]').length;
                
                document.getElementById('offline-count').textContent = offlineUsers;
                document.getElementById('website-count').textContent = websiteUsers;
                document.getElementById('ingame-count').textContent = ingameUsers;
                
                // Add event listener for Enter key in search box
                document.getElementById('search-input').addEventListener('keypress', function(event) {
                    if (event.key === 'Enter') {
                        searchUsers();
                        event.preventDefault();
                    }
                });
            }
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Roblox User Tracker</h1>
                <button id="theme-toggle" class="toggle-theme" onclick="toggleTheme()">🌙 Dark Mode</button>
            </div>
            
            <div class="controls">
                <input type="text" id="search-input" placeholder="Search users, display names, or mutual friends...">
                <button onclick="searchUsers()">Search</button>
            </div>
            
            <div class="filter-buttons">
                <button id="btn-all" class="filter-btn active" onclick="filterByStatus('all')">All Users</button>
                <button id="btn-In-Game" class="filter-btn" onclick="filterByStatus('In-Game')">In-Game</button>
                <button id="btn-Website" class="filter-btn" onclick="filterByStatus('Website')">On Website</button>
                <button id="btn-Offline" class="filter-btn" onclick="filterByStatus('Offline')">Offline</button>
            </div>
            
            <div class="stats">
                <div class="stat-item">Total: <span id="total-count">0</span></div>
                <div class="stat-item">Visible: <span id="visible-count">0</span></div>
                <div class="stat-item"><span class="status-dot ingame"></span> In-Game: <span id="ingame-count">0</span></div>
                <div class="stat-item"><span class="status-dot website"></span> Website: <span id="website-count">0</span></div>
                <div class="stat-item"><span class="status-dot offline"></span> Offline: <span id="offline-count">0</span></div>
            </div>
            
            <div class="user-grid">
    """
    
    for username, data in user_data.items():
        user_id = data["id"]
        presence = presence_data.get(user_id, {"status": "Unknown", "emoji": "❓"})
        status_class = f"status-{presence['status']}"
        
        html += f"""
        <div class="user" id="{user_id}" data-status="{presence['status']}">
            <div class="status-indicator {status_class}"></div>
            <div class="user-header">
                <img src="{thumbnails[user_id]}" alt="{username}">
                <div class="user-name">
                    <h2><a href="https://www.roblox.com/users/{user_id}/profile" target="_blank">{username}</a></h2>
                    <p class="display-name">{data['display_name']}</p>
                </div>
            </div>
            <div class="user-details">
                <p>Status: {presence['emoji']} {presence['status']}</p>
                <p>User ID: {user_id}</p>
            </div>
            <div class="mutuals">
                <h3>Mutual friends ({len(mutuals[user_id])})</h3>
        """
        
        if mutuals[user_id]:
            html += "<ul>"
            for friend in mutuals[user_id]:
                html += f'<li><a href="javascript:scrollToUser({friend["id"]})">{friend["name"]}</a></li>'
            html += "</ul>"
        else:
            html += "<p>No mutual friends</p>"
            
        html += """
            </div>
        </div>
        """
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    html += f"""
            </div>
            <div class="timestamp">
                Data generated on {current_time}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    webbrowser.open('file://' + os.path.realpath(filename), new=2)
    
    print(f"HTML file generated and opened in browser: {os.path.abspath(filename)}")

def wait_for_esc():
    print("\nPress Esc to exit...")
    keyboard.wait('esc')

def add_usernames():
    clear_terminal()
    print(watermark())
    print("\nAdd Usernames")
    print("Enter one username per line. Press Enter twice to finish.")
    print("─" * 50 + "\n")
    new_usernames = []
    
    while True:
        username = input().strip()
        if not username:
            break
        new_usernames.append(username)
    
    if new_usernames:
        with open("usernames.txt", "a") as f:
            f.write('\n' + '\n'.join(new_usernames))
        print(f"\nAdded {len(new_usernames)} new username(s) to usernames.txt")
        time.sleep(1)
    clear_terminal()
    return bool(new_usernames)

def show_menu():
    clear_terminal()
    print(watermark())
    print(f"\n{Fore.CYAN}Roblox User Tracker{Style.RESET_ALL}")
    print("─" * 40)
    print(f"{Fore.GREEN}1{Style.RESET_ALL} - Simple Output {Fore.BLUE}(Status only){Style.RESET_ALL}")
    print(f"{Fore.GREEN}2{Style.RESET_ALL} - Advanced Output {Fore.BLUE}(Full details){Style.RESET_ALL}")
    print(f"{Fore.GREEN}3{Style.RESET_ALL} - Web Output {Fore.BLUE}(Browser view){Style.RESET_ALL}")
    print(f"{Fore.GREEN}4{Style.RESET_ALL} - Add Usernames")
    print(f"{Fore.RED}0{Style.RESET_ALL} - Exit")
    print("─" * 40)

def prefetch_data(usernames):
    print("Fetching data...")
    user_data = get_user_ids(usernames)
    all_user_ids = {v["id"] for v in user_data.values()}
    presence_data = get_user_presence(list(all_user_ids))
    return user_data, presence_data

def group_and_print_users(user_data, presence_data, show_counts=True):
    offline = []
    website = []
    ingame = []
    
    for username, data in user_data.items():
        user_id = data["id"]
        presence = presence_data.get(user_id, {"status": "Unknown", "emoji": "❓"})
        user_info = (username, presence, data["display_name"])
        
        if presence['status'] == 'Offline':
            offline.append(user_info)
        elif presence['status'] == 'Website':
            website.append(user_info)
        else:
            ingame.append(user_info)
    
    if ingame:
        print(f"\n{Fore.GREEN}In-Game ({len(ingame)}){Style.RESET_ALL}")
        for username, presence, display_name in sorted(ingame):
            print_simple_output(username, presence, display_name)
            
    if website:
        print(f"\n{Fore.BLUE}On Website ({len(website)}){Style.RESET_ALL}")
        for username, presence, display_name in sorted(website):
            print_simple_output(username, presence, display_name)
            
    if offline:
        print(f"\n{Fore.RED}Offline ({len(offline)}){Style.RESET_ALL}")
        for username, presence, display_name in sorted(offline):
            print_simple_output(username, presence, display_name)
    
    if show_counts:
        print("\n" + "─" * 50)
        print(f"{Fore.CYAN}Total Users: {len(user_data)}")
        print(f"Online: {len(ingame) + len(website)} | Offline: {len(offline)}{Style.RESET_ALL}")

def group_and_print_users_advanced(user_data, presence_data, thumbnails, mutuals):
    offline = []
    website = []
    ingame = []
    
    for username, data in user_data.items():
        user_id = data["id"]
        presence = presence_data.get(user_id, {"status": "Unknown", "emoji": "❓"})
        user_info = (username, data, presence, thumbnails[user_id], mutuals[user_id])
        
        if presence['status'] == 'Offline':
            offline.append(user_info)
        elif presence['status'] == 'Website':
            website.append(user_info)
        else:
            ingame.append(user_info)
    
    print(f"{Fore.YELLOW}Note: Mutual friends data may be incomplete due to Roblox rate limiting{Style.RESET_ALL}\n")
    
    if ingame:
        print(f"\n{Fore.GREEN}In-Game ({len(ingame)}){Style.RESET_ALL}")
        for info in sorted(ingame, key=lambda x: x[0].lower()):
            print_advanced_output(*info)
            
    if website:
        print(f"\n{Fore.BLUE}On Website ({len(website)}){Style.RESET_ALL}")
        for info in sorted(website, key=lambda x: x[0].lower()):
            print_advanced_output(*info)
            
    if offline:
        print(f"\n{Fore.RED}Offline ({len(offline)}){Style.RESET_ALL}")
        for info in sorted(offline, key=lambda x: x[0].lower()):
            print_advanced_output(*info)
    
    print("\n" + "─" * 50)
    print(f"{Fore.CYAN}Total Users: {len(user_data)}")
    print(f"Online: {len(ingame) + len(website)} | Offline: {len(offline)}{Style.RESET_ALL}")

def ask_for_refresh(is_advanced=False):
    print("\n" + "─" * 50)
    print(f"\n{Fore.CYAN}Would you like to enable auto-refresh?")
    print(f"{Fore.GREEN}Y{Style.RESET_ALL} - Yes")
    print(f"{Fore.RED}N{Style.RESET_ALL} - No")
    choice = input(f"\n{Fore.CYAN}Choice: {Style.RESET_ALL}").lower().strip()
    
    if choice == 'y':
        while True:
            try:
                min_interval = 20 if is_advanced else 5
                print(f"\n{Fore.CYAN}Enter refresh interval in seconds")
                if is_advanced:
                    print(f"{Fore.YELLOW}Note: Advanced mode requires minimum {min_interval}s to prevent rate limiting{Style.RESET_ALL}")
                interval = float(input(f"{Fore.CYAN}Interval (minimum {min_interval}s): {Style.RESET_ALL}"))
                if interval >= min_interval:
                    return interval
                print(f"{Fore.RED}Interval must be at least {min_interval} seconds{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Please enter a valid number{Style.RESET_ALL}")
    return None

def auto_refresh(usernames, refresh_interval, output_type):
    clear_terminal()
    try:
        user_data, presence_data = prefetch_data(usernames)
        thumbnails = {}
        mutuals = {}
        all_user_ids = {v["id"] for v in user_data.values()}
        
        if output_type == "a":
            for username, data in user_data.items():
                user_id = data["id"]
                thumbnails[user_id] = get_thumbnail(user_id)

        while True:
            clear_terminal()
            print(watermark())
            print(f"\n{Fore.CYAN}Auto-refreshing every {refresh_interval} seconds")
            print(f"{Fore.YELLOW}Press Esc between refreshes to return to menu{Style.RESET_ALL}")
            print("─" * 50)
            
            presence_data = get_user_presence(list(all_user_ids))
            
            if output_type == "a":
                for username, data in user_data.items():
                    user_id = data["id"]
                    mutuals[user_id] = get_mutual_friends(user_id, all_user_ids)
                group_and_print_users_advanced(user_data, presence_data, thumbnails, mutuals)
            else:
                group_and_print_users(user_data, presence_data)
            
            print(f"\n{Fore.YELLOW}Waiting {refresh_interval} seconds before next refresh...{Style.RESET_ALL}")
            start_time = time.time()
            while time.time() - start_time < refresh_interval:
                if keyboard.is_pressed('esc'):
                    return
                time.sleep(0.1)
                
    except Exception as e:
        print(f"\n{Fore.RED}Error during refresh: {str(e)}{Style.RESET_ALL}")
        input("\nPress Enter to return to menu...")

def load_advanced_data(user_data, presence_data):
    thumbnails = {}
    mutuals = {}
    mutual_cache = {}
    retry_queue = []
    total = len(user_data)
    successful = 0
    failed = 0
    all_user_ids = {v["id"] for v in user_data.values()}
    
    print(f"\n{Fore.CYAN}Loading user data...{Style.RESET_ALL}")
    print("─" * 50)
    
    for i, (username, data) in enumerate(user_data.items(), 1):
        user_id = data["id"]
        print(f"\r{' ' * 100}\r{Fore.CYAN}Progress: {successful}/{total} users completed {Fore.YELLOW}({failed} failed) {Fore.WHITE}| Processing: {username}{Style.RESET_ALL}", end="", flush=True)
        
        thumbnails[user_id] = get_thumbnail(user_id)
        mutuals[user_id] = []
        
        result = get_mutual_friends_with_cache(user_id, all_user_ids, mutual_cache)
        if result is None:
            retry_queue.append((username, user_id))
        else:
            mutuals[user_id] = result
            if result or result == []:
                successful += 1
            else:
                failed += 1
        
        time.sleep(0.5)
    
    if retry_queue:
        print(f"\n\n{Fore.YELLOW}Rate limited! Waiting 10 seconds to retry remaining {len(retry_queue)} users...")
        print(f"Currently at {successful}/{total} users completed ({failed} failed){Style.RESET_ALL}")
        time.sleep(10)
        
        for username, user_id in retry_queue:
            print(f"\r{' ' * 100}\r{Fore.CYAN}Retrying... {successful}/{total} completed {Fore.YELLOW}(Currently: {username}){Style.RESET_ALL}", end="", flush=True)
            result = get_mutual_friends_with_cache(user_id, all_user_ids, mutual_cache)
            if result is not None:
                mutuals[user_id] = result
                if result or result == []:
                    successful += 1
                else:
                    failed += 1
            else:
                failed += 1
            time.sleep(0.5)
    
    print(f"\n\n{Fore.GREEN}Completed! Successfully processed {successful}/{total} users")
    if failed > 0:
        print(f"{Fore.YELLOW}({failed} users failed to load mutual friends){Style.RESET_ALL}")
    print()
    
    return thumbnails, mutuals

def main():
    try:
        clear_terminal()
        print(watermark())
        print(f"\n{Fore.CYAN}Initializing Roblox User Tracker...{Style.RESET_ALL}")
        
        try:
            requests.get("https://www.roblox.com")
        except RequestException:
            print("Error: No internet connection detected!")
            print("Please check your internet connection and try again")
            input("Press Enter to exit...")
            sys.exit(1)

        while True:
            show_menu()
            choice = input(f"\n{Fore.CYAN}Select an option: {Style.RESET_ALL}").strip()
            
            if choice == "0":
                clear_terminal()
                print(f"\n{Fore.GREEN}Thank you for using Roblox User Tracker!{Style.RESET_ALL}")
                sys.exit(0)
            
            if choice == "4":
                if add_usernames():
                    print("Usernames added successfully!")
                continue
            
            if choice not in ["1", "2", "3"]:
                print("\nInvalid choice! Please select a valid option.")
                time.sleep(1)
                continue
            
            usernames = read_usernames("usernames.txt")
            output_type = {"1": "s", "2": "a", "3": "w"}[choice]
            
            if output_type in ["s", "a"]:
                clear_terminal()
                print(watermark())
                print("\nFetching initial data...")
                user_data, presence_data = prefetch_data(usernames)
                
                if output_type == "s":
                    clear_terminal()
                    print(watermark())
                    group_and_print_users(user_data, presence_data)
                else:
                    clear_terminal()
                    print(watermark())
                    thumbnails, mutuals = load_advanced_data(user_data, presence_data)
                    group_and_print_users_advanced(user_data, presence_data, thumbnails, mutuals)
                
                refresh_interval = ask_for_refresh(is_advanced=(output_type == "a"))
                if refresh_interval:
                    auto_refresh(usernames, refresh_interval, output_type)
                else:
                    print(f"\n{Fore.YELLOW}Press Esc to return to menu...{Style.RESET_ALL}")
                    keyboard.wait('esc')
            else:
                clear_terminal()
                print(watermark())
                print("\nGenerating web view...")
                user_data, presence_data = prefetch_data(usernames)
                thumbnails = {}
                mutuals = {}
                for username, data in user_data.items():
                    user_id = data["id"]
                    thumbnails[user_id] = get_thumbnail(user_id)
                    mutuals[user_id] = get_mutual_friends(user_id, {v["id"] for v in user_data.values()})
                generate_html(user_data, presence_data, thumbnails, mutuals)
                print(f"\n{Fore.YELLOW}Press Esc to return to menu...{Style.RESET_ALL}")
                keyboard.wait('esc')
        
    except KeyboardInterrupt:
        clear_terminal()
        print(f"\n{Fore.YELLOW}Operation cancelled by user{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        clear_terminal()
        print(f"\n{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
