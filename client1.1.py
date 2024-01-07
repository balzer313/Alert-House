import socket
import functools
import threading
import cv2
import time


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        self.message_types = ["LOGIN", "LOGOUT", "GET", "MESSAGE", "LOGGED", "ALERT"]
        self.username = None
        self.password = None
        self.city = None
        self.listen_thread = threading.Thread(target=self.listen_messages, daemon=True)
        self.listen_thread.start()

    def build_send(self, socket, msg_type, data):
        socket.send(self.build_msg(msg_type, data).encode('utf-8'))
        if msg_type == "ERROR":
            print(f"sent: {self.build_msg(msg_type, data)}")
        else:
            print(f"sent: {self.build_msg(msg_type, data)}")

    def close(self):
        self.client_socket.close()

    def build_msg(self, msg_type,
                  data):  # build and return message by the protocol(if msg_type or data is wrong return None)
        if msg_type not in self.message_types:
            return None
        return f"{msg_type.ljust(10)}|{str(len(data)).zfill(6)}|{data}"

    def parse_msg(self,
                  protocol_message):  # get protocol message and return the splitted parts(message type, length of data, and data)
        splitted = self.split_msg(protocol_message, 2)
        return splitted[0], splitted[1], splitted[2] if len(splitted) > 2 else None

    def split_msg(self, str,
                  mafridim):  # checks if str's '|' seperators are the like the number of mafridim(if yes returns splitted list, if not return None)
        splitted = str.split("|")
        if len(splitted) == mafridim + 1:
            return splitted
        return None

    def join_msg(self, list):  # join the list to a message with seperators and return it
        return str(functools.reduce(lambda x, y: f"{str(x)}|{str(y)}", list))

    def login(self):
        login_message = f"{self.username}:{self.password}:{self.city}"
        self.build_send(self.client_socket, "LOGIN", login_message)

    def logout(self):
        self.build_send(self.client_socket, "LOGOUT", "")

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

                # Display the frame (optional)
                cv2.imshow("Recording...", frame)

                # Break the loop if 'q' key is pressed
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            # Release the VideoCapture and VideoWriter, and close OpenCV windows
            cap.release()
            out.release()
            cv2.destroyAllWindows()

    def listen_messages(self):  # listening nonstop to messages from the server and handeling them(print except alert)
        try:
            while True:
                received = self.client_socket.recv(1024).decode('utf-8')
                if not received:
                    break
                print(f"\nreceived: {received}")
                type1, num1, data1 = self.parse_msg(received)
                type_stripped = type1.strip()
                if type_stripped == "ALERT":
                    # start lock
                    self.record_camera(5, "camera_record.avi")
                    # send record
                    # end lock

        except Exception as e:
            print(f"\nError in listen_messages: {e}")
            # Handle the error as needed

    def close(self):
        self.client_socket.close()


if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 12345

    client = Client(HOST, PORT)

    try:
        while True:
            time.sleep(0.5)
            what = input("Choose: LOGIN / LOGOUT / LOGGED / EXIT / ALERT : ")
            if what.upper() == 'EXIT':
                break
            client.handle_options(what)
    except KeyboardInterrupt:
        print("\nClient terminated by user.")
    client.close()
