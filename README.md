# **AlertHouse 🚨** 

## Overview

**AlertHouse** is a secure application designed to transform any home into a smart house, offering alerts for rocket attacks in real-time. Developed to support Israelis during frequent rocket threats, AlertHouse notifies users through physical cues—such as flashing smart bulbs—and captures Iron Dome interceptions, streaming and storing the footage locally.

---

## Features

- **Real-Time Rocket Alerts:** Detects incoming alerts in specific cities and sends notifications directly to connected users.
- **Physical Alert System:** Integrates with Yeelight smart bulbs to flash when an alert is active, enhancing visibility and awareness.
- **Iron Dome Footage:** Captures and streams live footage of Iron Dome interceptions, with local storage for later viewing.
- **Secure Communication:** Employs encrypted, hashed communication for user data and interactions.
- **Client-Server Architecture:** Supports multiple client connections, utilizing multi-threaded operations and secure protocols.

---

## Architecture
AlertHouse operates on a **client-server model** to ensure efficient data handling and secure alert notifications.

- **Server**: Constantly monitors alerts from "Pikud HaOref" and notifies(if needed) the connected clients with real-time updates.
- **Client**: Runs on local devices, handling tasks such as camera recording, bulb flashing, and a graphical user interface for easy interaction.

---

## Tech Stack
- **Language:** Python
- **Client Interface:** Tkinter GUI
- **Networking:** Sockets with multithreading and secure data handling
- **Hardware:** Yeelight smart bulbs, camera (optional)

---

## Installation
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/balzer313/AlertHouse.git
   ```
2. **Navigate to the Project Directory:**
   ```bash
   cd AlertHouse
   ```
3. **Install Required Dependencies:**
   ```bash
   pip install pycryptodome pyDH opencv-python pillow yeelight requests
   ```

---

## Usage Tutorial
1. **start the server:**
   ```bash
   python server.py
   ```
2. **Connect a Client:**
   ```bash
   python client with gui.py
   ```
3. **Use the GUI:**

   - **Login Screen**: Enter your username and password to log in, or use the **"Register"** button to create a new account (opens the registration screen).
   
   - **Home Screen**: After logging in, you can:
     - View connected users with the **"LOGGED"** button.
     - Test an alert by pressing **"ALERT"**.
     - Access past alerts by navigating to **"Past Alerts"** to view previously recorded videos.
     - Configure **"Settings"** to connect devices like cameras and smart bulbs.
     - Press **"Logout"** to log out of the application.

---

## File Structure
**Server-Side Files:**
- **users.txt:** Stores user information.
- **server.log:** Server logs and activity tracking.
- **all_cities.json:** List of cities with potential alerts.
- **azakot.py:** Script for retrieving alerts from Pikud HaOref.

**Client-Side Files:**
- **Photos/:** Directory for user interface images.
- **Past_alerts/:** Folder storing previous alert videos.
- **all_cities.json:** A copy of city data for local alert checks.
