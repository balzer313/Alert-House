import socket
import threading
import functools
import logging
import numpy as np
import cv2
import azakot
import json

# protocol = tttttttttt|llllll|mmmm...

class User:
    def __init__(self, username, password):
        self.username = username
        self.password = password


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        logging.basicConfig(filename='server.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        with open('users.txt', 'r') as file:
            self.users = file.readlines()
        self.lock = threading.Lock()
        self.message_types = ["LOGIN", "LOGOUT", "GET", "MESSAGE", "ERROR", "LOGGED", "ALERT", "VIDEO"]
        self.logged_users = {}  # ip:username
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"Server listening on {self.host}:{self.port}")

    def build_msg(self, msg_type,
                  data):  # build and return message by the protocol(if msg_type or data is wrong return None)
        if msg_type not in self.message_types:
            return None
        return f"{msg_type.ljust(10)}|||{str(len(data)).zfill(6)}|||{data}"

    def build_send(self, socket, msg_type, data):
        socket.send(self.build_msg(msg_type, data).encode('utf-8'))
        if msg_type == "VIDEO":
            logging.info(f"sent: {self.build_msg(msg_type, '')}")
        elif msg_type == "ERROR":
            logging.error(f"sent: {self.build_msg(msg_type, data)}")
        else:
            logging.info(f"sent: {self.build_msg(msg_type, data)}")

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

    def is_logged(self, client_socket):  # gets client socket and return True if the socket logged in and False if not(to search for permission to commands)
        if client_socket.getpeername() in self.logged_users.keys(): return True
        return False

    def handle_client(self, client_socket):  # gets client socket and handle it
        city = None
        while True:
            find_alert_thread = threading.Thread(target=self.find_alert, args=(client_socket, city))
            find_alert_thread.start()
            try:
                protocol_message = self.receive_message(client_socket)
                print(protocol_message)
                find_alert_thread.join()  # Wait for the thread to complete before proceeding
                if protocol_message is None:  # Handle the case where the client disconnected
                    logging.info(f"Client {client_socket.getpeername()} disconnected")
                    return
                elif protocol_message == "":  # timed out and continue the loop
                    continue
            except Exception as e:
                # Handle exceptions during message reception
                logging.error(f"Error receiving message from {client_socket.getpeername()}: {e}")
                return
            logging.info("handle client...")
            type1, num1, data1 = self.split_msg(protocol_message, 2)
            type_stripped = type1.strip()
            if type_stripped == "VIDEO":
                logging.info(f"received: {type1}|||{num1}|||video bytes")
            else:
                logging.info(f"received: {protocol_message}")
            if type_stripped not in self.message_types: return None
            # check if the protocol message is right
            if not self.is_logged(client_socket):
                if type_stripped == "LOGIN":
                    city = self.handle_login(client_socket, protocol_message)
                else:
                    self.build_send(client_socket, "ERROR", "you need to log in to use this command")
            else:
                if type_stripped == "LOGOUT":
                    self.handle_logout(client_socket)
                elif type_stripped == "LOGGED":
                    self.handle_logged(client_socket)
                elif type_stripped == "ALERT":
                    self.handle_alert(client_socket)
                elif type_stripped == "VIDEO":
                    self.handle_video(client_socket, protocol_message)

    def handle_login(self, client_socket, protocol_message):
        type1, num1, data1 = self.split_msg(protocol_message, 2)
        user_and_pass = data1.split(":")
        if len(user_and_pass) != 3:
            self.build_send(client_socket, "ERROR", "Login message should look like 'username:password:city'")
            return None
        # login failed
        if not self.authenticate(user_and_pass[0], user_and_pass[1], user_and_pass[2]):
            self.build_send(client_socket, "ERROR", "My Gootz, it seems like the username, password or city isn't right")
            return None
        # login Succeeded
        self.build_send(client_socket, "MESSAGE", "you are logged in!")
        self.logged_users[client_socket.getpeername()] = user_and_pass[0]  # add to connected clients
        logging.info(f"now logged users are: {self.logged_users}")
        return user_and_pass[2]

    def authenticate(self, username, password, city):
        with self.lock:
            with open("all_cities.json", 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                cities = [area["label"] for area in data]
            for line in self.users:
                try:
                    stored_username, stored_password = line.strip().split(":")
                except ValueError:
                    logging.error("something went wrong"); return
                if username == stored_username and stored_password == password and city in cities:
                    return True
        return False

    def handle_logout(self, client_socket):
        if client_socket.getpeername() in self.logged_users.keys():
            del self.logged_users[client_socket.getpeername()]  # remove from connected clients
            logging.info(f"now logged users are: {self.logged_users}")
            # attempt to send logout message
            try:
                self.build_send(client_socket, "MESSAGE", "You have been logged out.")
            except (BrokenPipeError, ConnectionError):
                # handle the case where the client has closed the connection
                logging.error("Client has closed the connection.")

    def handle_logged(self, client_socket):
        try:
            logged_string = str(functools.reduce(lambda x, y: f"{str(x)}, {str(y)}",
                                                 [username for username in self.logged_users.values()]))
            self.build_send(client_socket, "MESSAGE", logged_string)
        except (BrokenPipeError, ConnectionError):
            # handle the case where the client has closed the connection
            logging.error("Error handling LOGGED command/ lost connection")

    def receive_message(self, client_socket, timeout=2):
        buffer_size = 1024
        complete_message = b''  # Use bytes for binary data

        while True:
            data_chunk = client_socket.recv(buffer_size)
            if not data_chunk:
                break  # No more data, connection closed

            complete_message += data_chunk

            # Check if the message is complete
            if len(data_chunk) < buffer_size:
                break  # Message received completely

        return complete_message.decode()

    def handle_alert(self, client_socket):
        self.build_send(client_socket, "ALERT", "מוות לחמאס")

    def handle_video(self, client_socket, protocol_message, width=1920, height=1080,
                     output_filename="received_video.avi"):
        # Extract the frame data from the protocol message
        frame_bytes = protocol_message.split("|||")[2].encode()

        try:
            # Decode the JPEG-encoded frame data to an OpenCV frame
            frame = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), flags=cv2.IMREAD_COLOR)
        except Exception as e:
            print("Error decoding frame:", e)
            frame = None

        if frame is not None and frame.size > 0:
            # Print the shape of the decoded frame
            print("Decoded frame shape:", frame.shape)

            # Resize the frame to the desired resolution
            frame = cv2.resize(frame, (width, height))

            # Write the frame to the output video file
            if not hasattr(self, 'video_writer'):
                fourcc = cv2.VideoWriter_fourcc(*"XVID")
                self.video_writer = cv2.VideoWriter(output_filename, fourcc, 20.0, (width, height))

            self.video_writer.write(frame)
        else:
            print("Error: Decoded frame is empty or invalid")

    def run(self):
        while True:
            client, addr = self.server_socket.accept()
            logging.info(f"Accepted connection from {addr}")
            client_thread = threading.Thread(target=self.handle_client, args=(client,))
            client_thread.start()

    def find_alert(self, client_socket, city):
        if azakot.main(city):
            self.handle_alert(client_socket)


if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 12345

    server = Server(HOST, PORT)
    server.run()
