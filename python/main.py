import requests
import time
import os
import webbrowser
import keyboard
from datetime import datetime, timezone

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

def read_usernames(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_user_ids(usernames):
    user_map = {}
    response = requests.post(
        "https://users.roblox.com/v1/usernames/users",
        json={"usernames": usernames, "excludeBannedUsers": True}
    )
    for user in response.json()["data"]:
        user_map[user["name"]] = {
            "id": user["id"],
            "display_name": user["displayName"]
        }
    return user_map

def get_user_presence(user_ids):
    presence = {}
    response = requests.post(
        "https://presence.roblox.com/v1/presence/users",
        json={"userIds": user_ids}
    )
    for p in response.json()["userPresences"]:
        status = ["Offline", "Website", "In-Game"][p["userPresenceType"]]
        emoji = {"Offline": "🔴", "Website": "🔵", "In-Game": "🟢"}[status]
        presence[p["userId"]] = {
            "status": status,
            "emoji": emoji,
            "last_online": p["lastOnline"]
        }
    return presence

def get_mutual_friends(user_id, all_user_ids):
    friends = requests.get(
        f"https://friends.roblox.com/v1/users/{user_id}/friends"
    ).json().get("data", [])
    return [f for f in friends if f["id"] in all_user_ids]

def get_thumbnail(user_id):
    thumb_response = requests.get(
        f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png"
    )
    return thumb_response.json()["data"][0]["imageUrl"]

def format_last_online(timestamp):
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            try:
                dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f%z")
            except ValueError:
                return "Unknown format"
        now = datetime.now(timezone.utc)
        diff = now - dt
        if diff.days > 7:
            return dt.strftime("%Y-%m-%d %H:%M")
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "Just now"
    return "Unknown"

def print_simple_output(username, presence):
    print(f"{username} - {presence['emoji']} {presence['status']}")

def print_advanced_output(username, data, presence, thumbnail, mutuals):
    print(f"\n{username}:")
    print(f"Display: {data['display_name']}")
    print(f"Status: {presence['emoji']} {presence['status']}")
    print(f"Last Online: {format_last_online(presence['last_online'])}")
    print(f"Thumbnail: {thumbnail}")
    print("Mutual friends from list:")
    for i, friend in enumerate(mutuals, 1):
        print(f"{i} - {friend['name']} - {friend['id']}")

def generate_html(user_data, presence_data, thumbnails, mutuals):
    filename = "roblox_users.html"
    
    if os.path.exists(filename):
        os.remove(filename)
    
    html = """
    <html>
    <head>
        <title>Roblox User Info</title>
        <style>
            body { font-family: Arial, sans-serif; }
            .user { margin-bottom: 20px; border: 1px solid #ddd; padding: 10px; }
            .user img { width: 100px; height: 100px; float: left; margin-right: 10px; }
            .user-info { margin-left: 120px; }
            .mutuals { margin-top: 10px; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
            #search-bar { margin-bottom: 20px; }
            #search-input { width: 300px; padding: 5px; }
            #search-button { padding: 5px 10px; }
        </style>
        <script>
            function scrollToUser(userId) {
                const element = document.getElementById(userId);
                element.scrollIntoView({behavior: "smooth", block: "start"});
            }
            function searchUsers() {
                const input = document.getElementById('search-input').value.toLowerCase();
                const users = document.getElementsByClassName('user');
                for (let user of users) {
                    const username = user.getElementsByTagName('h2')[0].textContent.toLowerCase();
                    if (username.includes(input)) {
                        user.style.display = '';
                    } else {
                        user.style.display = 'none';
                    }
                }
            }
        </script>
    </head>
    <body>
        <div id="search-bar">
            <input type="text" id="search-input" placeholder="Search users...">
            <button id="search-button" onclick="searchUsers()">Search</button>
        </div>
    """
    for username, data in user_data.items():
        user_id = data["id"]
        presence = presence_data.get(user_id, {"status": "Unknown", "emoji": "❓", "last_online": None})
        html += f"""
        <div class="user" id="{user_id}">
            <img src="{thumbnails[user_id]}" alt="{username}">
            <div class="user-info">
                <h2><a href="https://www.roblox.com/users/{user_id}/profile" target="_blank">{username}</a></h2>
                <p>Display: {data['display_name']}</p>
                <p>Status: {presence['emoji']} {presence['status']}</p>
                <p>Last Online: {format_last_online(presence['last_online'])}</p>
                <div class="mutuals">
                    <h3>Mutual friends:</h3>
                    <ul>
        """
        for friend in mutuals[user_id]:
            html += f'<li><a href="javascript:scrollToUser({friend["id"]})">{friend["name"]}</a> - {friend["id"]}</li>'
        html += """
                    </ul>
                </div>
            </div>
        </div>
        """
    html += "</body></html>"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    webbrowser.open('file://' + os.path.realpath(filename), new=2)
    
    print(f"HTML file generated and opened in browser: {os.path.abspath(filename)}")

def wait_for_esc():
    print("\nPress Esc to exit...")
    keyboard.wait('esc')

def main():
    print(watermark())
    print()

    usernames = read_usernames("usernames.txt")
    user_data = get_user_ids(usernames)
    all_user_ids = {v["id"] for v in user_data.values()}
    
    presence_data = get_user_presence(list(all_user_ids))
    
    output_type = input("Choose output type simple/advanced/web (s/a/w): ").lower().strip()
    
    thumbnails = {}
    mutuals = {}
    
    for username, data in user_data.items():
        user_id = data["id"]
        presence = presence_data.get(user_id, {"status": "Unknown", "emoji": "❓", "last_online": None})
        
        if output_type == "s":
            print_simple_output(username, presence)
        else:
            thumbnails[user_id] = get_thumbnail(user_id)
            mutuals[user_id] = get_mutual_friends(user_id, all_user_ids)
            
            if output_type == "a":
                print_advanced_output(username, data, presence, thumbnails[user_id], mutuals[user_id])
        
        time.sleep(0.5)
    
    if output_type == "w":
        for username, data in user_data.items():
            user_id = data["id"]
            if user_id not in thumbnails:
                thumbnails[user_id] = get_thumbnail(user_id)
            if user_id not in mutuals:
                mutuals[user_id] = get_mutual_friends(user_id, all_user_ids)
        generate_html(user_data, presence_data, thumbnails, mutuals)
    else:
        wait_for_esc()

if __name__ == "__main__":
    main()
