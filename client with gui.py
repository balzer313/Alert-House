import socket
import threading
import os
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
import cv2
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import json
from yeelight import *
import sys
import subprocess
from tkinter import font as tkfont
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import pyDH
import base64


class Client:
    def __init__(self, root, host, port):
        self.dh = pyDH.DiffieHellman()
        self.public_key = self.dh.gen_public_key()
        self.shared_secret = None
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        self.client_socket.send(str(self.public_key).encode())
        server_public_key = int(self.client_socket.recv(1024).decode())
        self.shared_secret = self.dh.gen_shared_key(server_public_key)
        self.message_types = ["LOGIN", "LOGOUT", "MESSAGE", "LOGGED", "ALERT", "REGISTER"]
        self.username = None
        self.password = None
        self.city = None
        self.light_ip = None
        self.new_light_ip = "192.168.110.66"
        self.current_bulb = tk.StringVar()
        self.current_camera = tk.StringVar()
        self.current_camera.set("Camera 0")  # default value for the camera Menu
        self.saved_videos_path = "past_alerts"  # where the alerts videos will be saved
        self.light_lock = False
        self.logged_in = False
        self.listen_thread = threading.Thread(target=self.listen_messages, daemon=True)
        self.listen_thread.start()

        self.root = root
        self.root.title("Alert House")
        logo = PhotoImage(file="photos/logo.png")
        self.root.iconphoto(False, logo)

        window_width = 800
        window_height = 500
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        root.resizable(False, False)  # cant change screen size
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.create_login_page()
        self.message_label = tk.Label(self.root, text="")
        self.error_label = tk.Label(self.root, text="")

    def encrypt_message(self, message):
        """encrypt the text"""
        cipher = AES.new(self.shared_secret[:32].encode('utf-8'), AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(message.encode('utf-8'), AES.block_size))
        return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')

    def decrypt_message(self, ciphertext):
        """decrypt the text"""
        ciphertext = base64.b64decode(ciphertext)
        iv = ciphertext[:16]
        ct = ciphertext[16:]
        cipher = AES.new(self.shared_secret[:32].encode('utf-8'), AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')

    def create_login_page(self):
        """GUI login page"""
        self.forget_screens()
        background_image = Image.open("photos/login_background.png")
        background_photo = ImageTk.PhotoImage(background_image)
        background_label = tk.Label(self.root, image=background_photo)
        background_label.image = background_photo
        background_label.place(relwidth=1, relheight=1)
        login_frame = tk.Frame(self.root, bg='white')

        login_frame.pack(padx=20, pady=125, expand=True)
        font_style = ("Helvetica", 18)
        self.username_entry = tk.Entry(login_frame, font=font_style, fg='grey', justify='center', bd=3)
        self.username_entry.insert(0, "username")
        self.username_entry.bind("<FocusIn>", self.on_entry_click_user)
        self.username_entry.bind("<FocusOut>", self.on_focus_out)
        self.username_entry.grid(row=1, column=1, pady=10, sticky=tk.W)

        self.password_entry = tk.Entry(login_frame, font=font_style, fg='grey', justify='center', bd=3)
        self.password_entry.insert(0, "password")  # Default text
        self.password_entry.bind("<FocusIn>", self.on_entry_click_pass)
        self.password_entry.bind("<FocusOut>", self.on_focus_out)
        self.password_entry.grid(row=2, column=1, pady=10, sticky=tk.W)

        with open("all_cities.json", 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            self.cities = [area["label"] for area in data]
            self.cities.sort()
        self.city_combobox = ttk.Combobox(login_frame, values=self.cities, font=font_style, width=19)
        self.city_combobox.grid(row=3, column=1, pady=5, sticky=tk.W)
        self.city_combobox.bind('<KeyRelease>', self.check_and_update)

        button_style = {"font": ("Helvetica", 9, "bold"), "bg": "#FF0009", "fg": "white", "bd": 3, "width": 10, "height": 2}
        login_button = tk.Button(login_frame, text="Login", command=self.login, **button_style)
        login_button.grid(row=5, column=0, columnspan=2, pady=(0, 3))

        register_button = tk.Button(login_frame, text="Register", command=self.register)
        register_button.grid(row=6, column=0, columnspan=2, pady=(0, 3))

        self.error_label = tk.Label(login_frame, text="", fg="red", font=font_style, bg='white')
        self.error_label.grid(row=7, column=0, columnspan=2, pady=(0, 0), sticky=tk.W)


    def check_and_update(self, event):
        str1 = self.city_combobox.get()
        if str1 == '':
            data = self.cities
        else:
            data = [item for item in self.cities if str1.lower() in item.lower()]
        self.city_combobox['values'] = data



    def on_entry_click_user(self, event):
        if self.username_entry.get() == "username":
            self.username_entry.delete(0, "end")
            self.username_entry.insert(0, "")
            self.username_entry.config(fg='black')

    def on_entry_click_pass(self, event):
        if self.password_entry.get() == "password":
            self.password_entry.delete(0, "end")
            self.password_entry.insert(0, "")
            self.password_entry.config(fg='black')

    def on_entry_click_register_user(self, event):
        if self.new_username_entry.get() == "username":
            self.new_username_entry.delete(0, "end")
            self.new_username_entry.config(fg='black')

    def on_entry_click_register_pass(self, event):
        if self.new_password_entry.get() == "password":
            self.new_password_entry.delete(0, "end")
            self.new_password_entry.config(fg='black', show='*')

    def on_focus_out(self, event):
        if not self.username_entry.get():
            self.username_entry.insert(0, "username")
            self.username_entry.config(fg='grey')
        if not self.password_entry.get():
            self.password_entry.insert(0, "password")
            self.password_entry.config(fg='grey')

    def on_focus_out_register_user(self, event):
        if self.new_username_entry.get() == '':
            self.new_username_entry.insert(0, "username")
            self.new_username_entry.config(fg='grey')

    def on_focus_out_register_pass(self, event):
        if self.new_password_entry.get() == '':
            self.new_password_entry.insert(0, "password")
            self.new_password_entry.config(fg='grey', show='')

    def forget_screens(self):
        """forget all the pages"""
        for widget in self.root.winfo_children():
            widget.place_forget()
            widget.pack_forget()

    def home_page(self):
        """GUI home page"""
        self.forget_screens()
        # ==========background============
        home_background_image = Image.open("photos/home_page_background.png")
        home_background_photo = ImageTk.PhotoImage(home_background_image)
        home_background_label = tk.Label(self.root, image=home_background_photo)
        home_background_label.image = home_background_photo
        home_background_label.place(relwidth=1, relheight=1)

        # ===========design============
        button_width = 20
        home_frame = tk.Frame(self.root, bg="white")
        home_frame.pack(side='bottom', pady=60, padx=20)
        tk.Button(home_frame, text="Logged", command=self.logged, font=("Helvetica", 14), bg="white",
                  width=button_width).grid(row=0, column=0, pady=5, padx=20)

        tk.Button(home_frame, text="Alert", command=self.alert, font=("Helvetica", 14), bg="white", fg="red",
                  width=button_width).grid(row=1, column=0, pady=5, padx=20)
        tk.Button(home_frame, text="Past Alerts", command=self.past_alerts, font=("Helvetica", 14), bg="white",
                  width=button_width).grid(row=2, column=0, pady=5, padx=20)
        tk.Button(home_frame, text="Settings", command=self.settings, font=("Helvetica", 14), bg="white",
                  width=button_width).grid(row=3, column=0, pady=5, padx=20)
        tk.Button(home_frame, text="Logout", command=self.logout, font=("Helvetica", 14),
                  bg="red", fg="white", width=button_width, compound='left').grid(row=4, column=0, pady=5, padx=20)

        self.message_label = tk.Label(home_frame, text="", fg="black", font=("Helvetica", 6), bg='white')
        self.message_label.grid(row=5, column=0, pady=5, padx=20)

    def build_send(self, socket, msg_type, data):
        """building, encrypting and sending the request to the server"""
        message = self.build_msg(msg_type, data)
        encrypted_message = self.encrypt_message(message)
        socket.send(encrypted_message.encode())
        print(f"==================\nsent: {self.build_msg(msg_type, data)}")


    def build_msg(self, msg_type, data):
        """build and return message by the protocol
        (if msg_type or data is wrong return None)"""
        if msg_type not in self.message_types:
            return None
        return f"{msg_type.ljust(10)}|*|*|{str(len(data)).zfill(6)}|*|*|{data}"


    def split_msg(self, str, mafridim):
        """checks if the separators matching the filds(if yes returns splitted list, if not return None)"""
        splitted = str.split("|*|*|")
        if len(splitted) == mafridim + 1:
            return splitted
        return None

    def login(self):
        """send login request to the server"""
        self.username = self.username_entry.get()
        self.password = self.password_entry.get()
        self.city = self.city_combobox.get()
        login_message = f"{self.username}:{self.password}:{self.city}"
        self.build_send(self.client_socket, "LOGIN", login_message)

    def register(self):
        """GUI register page"""
        self.forget_screens()  # Forget the login screen

        ##########  Style a new frame(screen)  ##########
        # Create new frame with a border and some padding
        register_frame = tk.Frame(self.root, bg='white', bd=2, relief='solid')
        register_frame.pack(padx=20, pady=80, expand=True)

        # Add an inner frame for better padding control
        inner_frame = tk.Frame(register_frame, bg='white')
        inner_frame.pack(padx=10, pady=1)

        font_style = ("Helvetica", 18)

        # Add a title label
        title_label = tk.Label(inner_frame, text="Register", font=("Helvetica", 24, "bold"), bg='white')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Username entry
        self.new_username_entry = tk.Entry(inner_frame, font=font_style, fg='grey', justify='center', bd=3)
        self.new_username_entry.insert(0, "username")
        self.new_username_entry.bind("<FocusIn>", self.on_entry_click_register_user)
        self.new_username_entry.bind("<FocusOut>", self.on_focus_out_register_user)
        self.new_username_entry.grid(row=1, column=0, pady=10, sticky=tk.W, padx=10)

        # Password entry
        self.new_password_entry = tk.Entry(inner_frame, font=font_style, fg='grey', justify='center', bd=3)
        self.new_password_entry.insert(0, "password")
        self.new_password_entry.bind("<FocusIn>", self.on_entry_click_register_pass)
        self.new_password_entry.bind("<FocusOut>", self.on_focus_out_register_pass)
        self.new_password_entry.grid(row=2, column=0, pady=10, sticky=tk.W, padx=10)

        button_style = {"font": ("Helvetica", 9, "bold"), "bg": "#FF0009", "fg": "white", "bd": 3, "width": 10,
                        "height": 2}
        register_button = tk.Button(inner_frame, text="Register", command=self.register_user, **button_style)
        register_button.grid(row=3, column=0, pady=(10, 3), sticky=tk.N,
                             padx=10)

        back_to_login_button = tk.Button(inner_frame, text="Back to Login", command=self.create_login_page)
        back_to_login_button.grid(row=4, column=0, pady=(0, 3), sticky=tk.N, padx=10)

        self.error_label = tk.Label(inner_frame, text="", fg="red", font=font_style, bg='white')
        self.error_label.grid(row=5, column=0, pady=(10, 0), sticky=tk.W, padx=10)

    def register_user(self):
        register_user = self.new_username_entry.get()
        register_pass = self.new_password_entry.get()
        register_message = f"{register_user}:{register_pass}"
        self.build_send(self.client_socket, "REGISTER", register_message)

    def past_alerts(self):
        """GUI past alerts page"""
        self.forget_screens()

        # Create a new screen for past alerts
        self.root.configure(bg='#f0f0f0')

        title_font = tkfont.Font(family='Helvetica', size=18, weight="bold")
        title_label = tk.Label(self.root, text="Your Past Alerts", font=title_font, bg='#f0f0f0', fg='#333333')
        title_label.pack(pady=20)

        # Listbox of past videos
        video_font = tkfont.Font(family='Helvetica', size=10)
        video_listbox = tk.Listbox(self.root, width=50, height=15, font=video_font, bg='#ffffff', fg='#333333', bd=2, relief='sunken')
        video_listbox.pack(pady=20)
        video_listbox.bind('<Double-1>', self.play_video)
        self.list_videos(video_listbox)

        # Back button
        button_font = tkfont.Font(family='Helvetica', size=14)
        back_button = tk.Button(self.root, text="Back", command=self.home_page, font=button_font, bg='gray', fg='white', bd=0, relief='flat')
        back_button.pack(pady=20)

    def settings(self):
        """GUI settings page"""
        self.forget_screens()
        self.root.configure(bg='#f0f0f0')

        # Camera selection
        camera_label = tk.Label(self.root, text="Select Camera:", font=('Helvetica', 12), bg='#f0f0f0', fg='#333333')
        camera_label.pack(pady=10)
        self.camera_menu = tk.OptionMenu(self.root, self.current_camera, "Loading...")
        self.camera_menu.config(bg='#ffffff', fg='#333333', bd=2, relief='sunken', font=('Helvetica', 10))
        self.camera_menu.pack(pady=10)

        # Start the camera detection in a new thread
        threading.Thread(target=self.update_camera_menu).start()

        # YeeLight bulb selection
        bulb_label = tk.Label(self.root, text="Select YeeLight Bulb:", font=('Helvetica', 12), bg='#f0f0f0', fg='#333333')
        bulb_label.pack(pady=10)
        self.bulb_menu = tk.OptionMenu(self.root, self.current_bulb, "Loading...")
        self.bulb_menu.config(bg='#ffffff', fg='#333333', bd=2, relief='sunken', font=('Helvetica', 10))
        self.bulb_menu.pack(pady=10)

        # Start the bulb detection in a new thread
        threading.Thread(target=self.update_bulb_menu).start()

        # Back button
        back_button = tk.Button(self.root, text="Back", command=self.home_page, font=('Helvetica', 14), bg='gray', fg='white', bd=0, relief='flat')
        back_button.pack(pady=20)

    def update_camera_menu(self):
        cameras = self.get_cameras()
        # Update the OptionMenu in the main thread
        try:
            self.root.after(0, self.populate_camera_menu, cameras)
        except Exception:
            pass

    def populate_camera_menu(self, cameras):
        menu = self.camera_menu["menu"]
        menu.delete(0, "end")
        for camera in cameras:
            menu.add_command(label=camera, command=lambda cam=camera: self.current_camera.set(cam))
        self.current_camera.set(cameras[0] if cameras else "No cameras found")

    def get_cameras(self):
        """find all available cameras"""
        index = 0
        arr = []
        while True:
            try:
                cap = cv2.VideoCapture(index)
                if not cap.read()[0]:
                    break
                else:
                    arr.append(f"Camera {index}")
                cap.release()
                index += 1
            except Exception:
                pass
        return arr

    def update_bulb_menu(self):
        bulbs = self.get_bulbs()

        # Update the OptionMenu in the main thread
        try:
            self.root.after(0, self.populate_bulb_menu, bulbs)
        except Exception:
            pass

    def populate_bulb_menu(self, bulbs):
        menu = self.bulb_menu["menu"]
        menu.delete(0, "end")
        for bulb in bulbs:
            # Set the command to update the selected bulb's IP address
            menu.add_command(label=bulb, command=lambda b=bulb: self.set_selected_bulb(b))
        self.current_bulb.set(bulbs[0] if bulbs else "No bulbs found")

    def get_bulbs(self):
        # Discover YeeLight bulbs on the network
        bulbs = discover_bulbs()
        bulb_list = [f"{bulb['capabilities']['name']} ({bulb['ip']})" for bulb in bulbs]
        return bulb_list

    def set_selected_bulb(self, bulb):
        # Extract the IP address from the selected bulb string and update the light_ip variable
        self.current_bulb.set(bulb)
        self.light_ip = bulb.split('(')[-1][:-1]

    def logout(self):
        """logout and return to login page"""
        self.logged_in = False
        self.build_send(self.client_socket, "LOGOUT", "")
        self.forget_screens()
        self.create_login_page()

    def logged(self):
        """sending logged request to the server"""
        self.build_send(self.client_socket, "LOGGED", "")

    def alert(self):
        """sending alert request to the server"""
        self.build_send(self.client_socket, "ALERT", "")

    def list_videos(self, video_listbox):
        videos = [f for f in os.listdir(self.saved_videos_path) if os.path.splitext(f)[1].lower() == ".avi"]

        video_listbox.delete(0, tk.END)
        for video in videos:
            video_listbox.insert(tk.END, video)

    def play_video(self, event):
        """play the selected video from the recorded options"""
        selected_video = event.widget.get(event.widget.curselection())
        video_path = os.path.join(self.saved_videos_path, selected_video)
        if os.name == 'nt':  # if Windows
            os.startfile(video_path)
        elif os.name == 'posix':  # if macOS or Linux
            subprocess.run(['open', video_path] if sys.platform == 'darwin' else ['xdg-open', video_path])

    def record_camera(self, duration=5):
        """record the camera for the duration time, streaming it
        to the screen and saving it in past_alerts file"""

        video_label = tk.Label(self.root, width=800, height=500)
        video_label.place(x=0, y=0)

        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.makedirs("past_alerts", exist_ok=True)  # Create the folder if it doesn't exist
        output_filename = os.path.join(self.saved_videos_path, f"output_{current_time}.avi")

        camera_index = int(self.current_camera.get().split()[-1])  # Extract the camera index from the selected camera

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return

        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        camera_fps = cap.get(cv2.CAP_PROP_FPS)

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(output_filename, fourcc, camera_fps, (width, height))

        start_time = time.time()
        frame_count = 0  # Count the frames captured

        try:
            while True:
                current_time = time.time()
                elapsed_time = current_time - start_time

                if elapsed_time >= duration:
                    break

                ret, frame = cap.read()
                if not ret:
                    print("Error: Failed to capture frame.")
                    break

                # Resize frame to match Label size
                frame = cv2.resize(frame, (width, height))
                out.write(frame)
                frame_count += 1

                # Display the video in the Tkinter label
                img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                imgtk = ImageTk.PhotoImage(image=img)
                video_label.imgtk = imgtk
                video_label.config(image=imgtk)
                self.root.update()  # Explicitly update the Tkinter window

                # Introduce a delay to match the camera's frame rate
                time.sleep(1 / camera_fps)  # Adjust this delay as needed

        finally:
            cap.release()
            out.release()
            cv2.destroyAllWindows()
            video_label.destroy()

            # Calculate actual frame rate
            actual_duration = time.time() - start_time
            actual_fps = frame_count / actual_duration
            print(f"Recorded at {actual_fps} fps")

    def alert_light(self, ip):
        """with Yeeligh api and light_lock - the function the selected
        bulb blinks to illustrate the alert"""
        try:
            self.light_lock = True
            bulb = Bulb(self.new_light_ip)
            bulb.ensure_on()
            bulb.turn_on()
            bulb.set_brightness(100)
            time.sleep(1)
            bulb.set_brightness(1)
            time.sleep(0.5)
            bulb.set_brightness(100)
            time.sleep(1)
            bulb.set_brightness(1)
            time.sleep(0.5)
            bulb.set_brightness(100)
            time.sleep(1)
            bulb.set_brightness(1)
            time.sleep(0.5)
            bulb.set_brightness(100)
            time.sleep(1)
            bulb.set_brightness(1)
            time.sleep(0.5)
            bulb.set_brightness(100)
            time.sleep(1)
            self.light_lock = False

        except Exception as ex:
            print(f"light didn't work: {ex}")
            self.light_lock = False
            pass


    def listen_messages(self):
        """listening nonstop to messages from the server and handeling them"""
        try:
            while True:
                encrypted_message = self.client_socket.recv(1024).decode()
                received = self.decrypt_message(encrypted_message)
                if not received:
                    break
                print(f"\nreceived: {received}\n==================")
                type1, num1, data1 = self.split_msg(received, 2)
                type_stripped = type1.strip()
                if data1 == "you are logged in!":
                    self.logged_in = True
                    self.home_page()
                if data1 == "you are registered!":
                    self.create_login_page()
                if type_stripped == "ERROR" and self.error_label.winfo_exists():
                    self.error_label.config(
                        text=data1,
                        font=("Helvetica", 9))
                    self.root.after(5000, self.clear_label_if_exists, self.error_label)
                if type_stripped == "MESSAGE" and self.message_label.winfo_exists():
                    try:
                        self.message_label.config(text=data1, font=("Garamond", 12, "bold"))
                        self.root.after(3000, self.clear_label_if_exists, self.message_label)
                    except Exception:
                        pass
                if type_stripped == "ALERT":
                    threading.Thread(target=self.record_camera, args=(5,)).start()
                    if not self.light_lock:
                        self.alert_light(self.light_ip)
                    else:
                        print("the bulb is being used")

        except Exception as e:
            print(f"\nError in listen_messages: {e}")
            # Handle the error as needed

    def close(self):
        """closing the app"""
        if self.logged_in:
            self.build_send(self.client_socket, "LOGOUT", "")
        self.client_socket.close()

    def clear_label_if_exists(self, label):
        """if the label exist - clear it"""
        if label.winfo_exists():
            label.config(text="")



if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 12345

    root = tk.Tk()
    client = Client(root, HOST, PORT)
    root.mainloop()
    try:
        while True:
            time.sleep(0.5)
            break
    except KeyboardInterrupt:
        print("\nClient terminated by user.")
    client.close()


