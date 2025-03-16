# Roblox User Tracker 🕹️

## Overview
A simple Python script to retrieve and display detailed Roblox user information with multiple output modes.

## Features 🌟
- **Multiple Output Modes**
  - Simple: Quick username and status
  - Advanced: Detailed user information
  - Web: Interactive HTML page with search functionality

- **User Information Retrieval**
  - Username lookup
  - Display name
  - Online status
  - Thumbnail image
  - Mutual friends detection

## Installation 📥

### Method 1: Using the Executable
1. Go to the [Releases](https://github.com/yourusername/RUT-Roblox-User-Tracker/releases) page
2. Download the latest `executable.zip` file
3. Run the executable - no installation required!

### Method 2: Using the Source Code
1. Ensure you have Python 3.6 or higher installed
2. Download or clone this repository
3. Install the required dependencies:
   ```bash
   pip install requests keyboard colorama
   ```
4. Run the script:
   ```bash
   python main.py
   ```

## Usage 💻
1. **First Run**: 
   - Create a file named `usernames.txt` in the same directory as the program
   - Add Roblox usernames (one per line)

2. **Using the Program**:
   - Choose an output mode from the main menu:
     - Simple Output: Quick status overview
     - Advanced Output: Detailed information with mutual friends
     - Web Output: Interactive HTML page with search and filtering
   - Add more usernames directly from the program using option 4

3. **Web View Features**:
   - Search users by username, display name, or mutual friends
   - Filter by online status
   - Dark/light mode toggle
   - Click on mutual friends to quickly navigate between users

## Example Input (usernames.txt)
```
Username1
Username2
Username3
```

## Created By 👨‍💻
**Bonker (Bink-Lab)**