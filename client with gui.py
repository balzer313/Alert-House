import socket
import functools
import threading
import cv2
import time
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import json

class Client:
    def __init__(self, root, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        self.message_types = ["LOGIN", "LOGOUT", "GET", "MESSAGE", "LOGGED", "ALERT", "VIDEO"]
        self.username = None
        self.password = None
        self.city = None
        self.logged_in = False
        self.listen_thread = threading.Thread(target=self.listen_messages, daemon=True)
        self.listen_thread.start()

        self.root = root
        self.root.title("Alert House")

        window_width = 800
        window_height = 500
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        self.create_login_page()

    def create_login_page(self):
        # Login Page
        self.background_image = Image.open("photos/login_background.png")
        self.background_photo = ImageTk.PhotoImage(self.background_image)
        self.background_label = tk.Label(self.root, image=self.background_photo)
        self.background_label.image = self.background_photo
        self.background_label.place(relwidth=1, relheight=1)
        self.login_frame = tk.Frame(self.root, bg='white')

        self.login_frame.pack(padx=20, pady=140)
        font_style = ("Helvetica", 18)
        self.username_entry = tk.Entry(self.login_frame, font=font_style, fg='grey', justify='center', bd=3)
        self.username_entry.insert(0, "username")  # Default text
        self.username_entry.bind("<FocusIn>", self.on_entry_click_user)
        self.username_entry.bind("<FocusOut>", self.on_focus_out)
        self.username_entry.grid(row=1, column=1, pady=10, sticky=tk.W)

        self.password_entry = tk.Entry(self.login_frame, font=font_style, fg='grey', justify='center', bd=3)
        self.password_entry.insert(0, "password")  # Default text
        self.password_entry.bind("<FocusIn>", self.on_entry_click_pass)
        self.password_entry.bind("<FocusOut>", self.on_focus_out)
        self.password_entry.grid(row=2, column=1, pady=10, sticky=tk.W)

        with open("all_cities.json", 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            self.cities = [area["label"] for area in data]
            self.cities.sort()
        self.city_combobox = ttk.Combobox(self.login_frame, values=self.cities, font=font_style, width=19)
        self.city_combobox.grid(row=3, column=1, pady=10, sticky=tk.W)
        self.city_combobox.bind('<KeyRelease>', self.check_and_update)
        login_button = tk.Button(self.login_frame, text="Login", command=self.login)
        login_button.grid(row=4, column=0, columnspan=2, pady=10)






    def check_and_update(self, event):
        str1 = self.city_combobox.get()
        if str1 == '':
            data = self.cities
        else:
            data = [item for item in self.cities if str1.lower() in item.lower()]
        self.city_combobox['values'] = data


        # self.city_combobox.event_generate('<Down>')
        # self.city_combobox.update()
        # time.sleep(1)
        # # # Set the focus back to the entry widget and set the text to what was there before
        # self.city_combobox.focus()


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

    def on_focus_out(self, event):
        if not self.username_entry.get():
            self.username_entry.insert(0, "username")
            self.username_entry.config(fg='grey')
        if not self.password_entry.get():
            self.password_entry.insert(0, "password")
            self.password_entry.config(fg='grey')

    def home_page(self):
        self.login_frame.forget()
        self.background_label.place_forget()
        # ==========background============
        self.home_background_image = Image.open("photos/home_page_background.png")
        self.home_background_photo = ImageTk.PhotoImage(self.home_background_image)
        self.home_background_label = tk.Label(self.root, image=self.home_background_photo)
        self.home_background_label.image = self.home_background_photo
        self.home_background_label.place(relwidth=1, relheight=1)

        # ===========design============
        button_width = 20  # Adjust this value for the desired button width
        self.home_frame = tk.Frame(self.root, bg="white")
        self.home_frame.pack(side='bottom', pady=150, padx=20)
        tk.Button(self.home_frame, text="Alerts", command=self.alert, font=("Helvetica", 14), bg="white",
                  width=button_width).grid(row=0, column=0, pady=5, padx=20)
        tk.Button(self.home_frame, text="Logged", command=self.logged, font=("Helvetica", 14), bg="white",
                  width=button_width).grid(row=1, column=0, pady=5, padx=20)
        tk.Button(self.home_frame, text="Logout", command=self.logout, font=("Helvetica", 14),
                  bg="white", width=button_width, compound='left').grid(row=2, column=0, pady=5, padx=20)
    def build_send(self, socket, msg_type, data):
        socket.send(self.build_msg(msg_type, data).encode('utf-8'))
        if msg_type == "VIDEO":
            print(f"==================\nsent: {self.build_msg(msg_type, '')}")
        else:
            print(f"==================\nsent: {self.build_msg(msg_type, data)}")

    def close(self):
        self.client_socket.close()

    def build_msg(self, msg_type,
                  data):  # build and return message by the protocol(if msg_type or data is wrong return None)
        if msg_type not in self.message_types:
            return None
        return f"{msg_type.ljust(10)}|||{str(len(data)).zfill(6)}|||{data}"

    def parse_msg(self,
                  protocol_message):  # get protocol message and return the splitted parts(message type, length of data, and data)
        splitted = self.split_msg(protocol_message, 2)
        return splitted[0], splitted[1], splitted[2] if len(splitted) > 2 else None

    def split_msg(self, str,
                  mafridim):  # checks if str's '|' seperators are the like the number of mafridim(if yes returns splitted list, if not return None)
        splitted = str.split("|||")
        if len(splitted) == mafridim + 1:
            return splitted
        return None

    def join_msg(self, list):  # join the list to a message with seperators and return it
        return str(functools.reduce(lambda x, y: f"{str(x)}|{str(y)}", list))

    def login(self):
        self.username = self.username_entry.get()
        self.password = self.password_entry.get()
        self.city = self.city_combobox.get()
        login_message = f"{self.username}:{self.password}:{self.city}"
        self.build_send(self.client_socket, "LOGIN", login_message)

    def logout(self):
        self.logged_in = False
        self.build_send(self.client_socket, "LOGOUT", "")
        self.home_frame.destroy()
        self.create_login_page()

    def logged(self):
        self.build_send(self.client_socket, "LOGGED", "")

    def alert(self):
        self.build_send(self.client_socket, "ALERT", "")

    def handle_options(self, option):  # handeling command to send to the server
        option_stripped = option.strip()
        if option_stripped not in self.message_types:
            print("not an option!")
            return
        if option_stripped == "LOGIN":
            self.username = input("enter username: ")
            self.password = input("enter password: ")
            self.city = input("enter city: ")
            self.login()
        elif option_stripped == "LOGOUT":
            self.logout()
        elif option_stripped == "LOGGED":
            self.logged()
        elif option_stripped == "ALERT":
            self.alert()

    def record_camera(self, duration=5, output_filename="camera_record.avi"):
        # Open the default camera (usually the built-in webcam)
        cap = cv2.VideoCapture(0)

        # Check if the camera opened successfully
        if not cap.isOpened():
            print("Error: Could not open camera.")
            return

        # Set the desired resolution (e.g., 1920x1080 for Full HD)
        width, height = 1920, 1080

        # Define the codec and create a VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(output_filename, fourcc, 20.0, (width, height))

        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                # Capture frame-by-frame
                ret, frame = cap.read()
                if not ret:
                    print("Error: Failed to capture frame.")
                    break
                # Resize the frame to the desired resolution
                frame = cv2.resize(frame, (width, height))
                # Write the frame to the video file
                out.write(frame)

                # Break the loop if 'q' key is pressed
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            # Release the VideoCapture and VideoWriter, and close OpenCV windows
            cap.release()
            out.release()
            cv2.destroyAllWindows()
        data_bytes = cv2.imencode('.jpg', frame)[1].tobytes()
        self.build_send(self.client_socket, "VIDEO", data_bytes)

    def listen_messages(self):  # listening nonstop to messages from the server and handeling them(print except alert)
        try:
            while True:
                received = self.client_socket.recv(1024).decode()
                if not received:
                    break
                print(f"\nreceived: {received}\n==================")
                type1, num1, data1 = self.parse_msg(received)
                type_stripped = type1.strip()
                if data1 == "you are logged in!":
                    self.logged_in = True
                    self.home_page()
                if type_stripped == "ALERT":
                    # start lock
                    self.record_camera(5, "camera_record.avi")
                    # send record
                    # end lock

        except Exception as e:
            print(f"\nError in listen_messages: {e}")
            # Handle the error as needed

    def close(self):
        if self.logged_in:
            self.build_send(self.client_socket, "LOGOUT", "")
        self.client_socket.close()

    def receive_message(self, client_socket):
        # Initialize an empty message buffer
        message_buffer = b""

        while True:
            # Receive data from the client
            data = client_socket.recv(1024)  # You can adjust the buffer size as needed

            # Break the loop if no more data is received
            if not data:
                break

            # Append the received data to the message buffer
            message_buffer += data

            # Check if the entire message has been received
            if b"\n" in message_buffer:
                break

        # Decode and return the complete message
        return message_buffer.decode('utf-8').strip()


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


