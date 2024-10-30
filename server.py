import hashlib
import socket
import threading
import functools
import logging
import time
from Cryptodome.Cipher import AES
from Cryptodome.Util.Padding import pad, unpad
import pyDH
import base64
import azakot
import json


class User:
    def __init__(self, client_socket, ip, username, password, city):
        self.client_socket = client_socket
        self.ip = ip
        self.username = username
        self.password = password
        self.city = city
    def get_client_socket(self):
        return self.client_socket
    def get_ip(self):
        return self.ip
    def get_username(self):
        return self.username
    def get_password(self):
        return self.password
    def get_city(self):
        return self.city
    def set_username(self, name):
        self.username = name
    def set_password(self, password):
        self.password = password
    def set_city(self, city):
        self.city = city

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        logging.basicConfig(filename='server.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.users_file_path = "users.txt"
        self.cities_file_path = "all_cities.json"
        self.lock = threading.Lock()
        self.message_types = ["LOGIN", "LOGOUT", "MESSAGE", "ERROR", "LOGGED", "ALERT", "REGISTER"]
        self.logged_users = []  # User list
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f"Server listening on {self.host}:{self.port}")

        self.dh = pyDH.DiffieHellman()
        self.public_key = self.dh.gen_public_key()
        self.shared_secrets = {}  # Store shared secrets for each client

    def get_list(self, kind):
        """input kind of list(like username list or ip list), and return the selected list"""
        options = ["username", "ip", "city", "password", "client_socket"]
        if kind not in options:
            logging.error("Error in get_list function")
            return None
        return list(map(lambda x: getattr(x, f"get_{kind}")(), self.logged_users))

    def encrypt_message(self, message, shared_secret):
        """encrypt the text"""
        cipher = AES.new(shared_secret[:32].encode('utf-8'), AES.MODE_CBC)
        ct_bytes = cipher.encrypt(pad(message.encode('utf-8'), AES.block_size))
        return base64.b64encode(cipher.iv + ct_bytes).decode('utf-8')

    def decrypt_message(self, ciphertext, shared_secret):
        """decrypt the text"""
        ciphertext = base64.b64decode(ciphertext)
        iv = ciphertext[:16]
        ct = ciphertext[16:]
        cipher = AES.new(shared_secret[:32].encode('utf-8'), AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')

    def build_msg(self, msg_type, data):
        """build and return message by the protocol
        (if msg_type or data is wrong return None)"""
        if msg_type not in self.message_types:
            return None
        return f"{msg_type.ljust(10)}|*|*|{str(len(data)).zfill(6)}|*|*|{data}"

    def build_send(self, socket, msg_type, data):
        """building, encrypting and sending the request to the server"""
        message = self.build_msg(msg_type, data)
        shared_secret = self.shared_secrets[socket]
        encrypted_message = self.encrypt_message(message, shared_secret)
        socket.send(encrypted_message.encode())
        if msg_type == "ERROR":
            logging.error(f"sent: {self.build_msg(msg_type, data)}")
        else:
            logging.info(f"sent: {self.build_msg(msg_type, data)}")

    def split_msg(self, str, mafridim):
        """checks if the separators matching the filds(if yes returns splitted list, if not return None)"""
        splitted = str.split("|*|*|")
        if len(splitted) == mafridim + 1:
            return splitted
        return None

    def is_logged(self, user):
        """gets user and return True if the socket logged in and False if not(to search for permission to commands)"""
        if user in self.logged_users: return True
        return False

    def handle_client(self, user):
        """gets user and handle it"""
        client_socket = user.get_client_socket()
        while True:
            try:
                encrypted_message = client_socket.recv(1024).decode()
                shared_secret = self.shared_secrets[client_socket]
                protocol_message = self.decrypt_message(encrypted_message, shared_secret)
                if protocol_message is None:  # Handle the case where the client disconnected
                    logging.info(f"Client {client_socket.getpeername()} disconnected")
                    return
                elif protocol_message == "":  # timed out and continue the loop
                    continue
            except Exception as e:
                # Handle exceptions during message reception
                logging.error(f"Error receiving message from {user.get_ip()}: {e}")
                return
            logging.info("handle client...")
            type1, num1, data1 = self.split_msg(protocol_message, 2)
            type_stripped = type1.strip()
            logging.info(f"received: {protocol_message}")
            if type_stripped not in self.message_types: return None
            # check if the protocol message is right
            if not self.is_logged(user):
                if type_stripped == "LOGIN":
                    self.handle_login(user, protocol_message)
                elif type_stripped == "REGISTER":
                    self.handle_register(user, protocol_message)
                else:
                    self.build_send(client_socket, "ERROR", "you need to log in to use this command")
            else:
                if type_stripped == "LOGOUT":
                    self.handle_logout(user)
                elif type_stripped == "LOGGED":
                    self.handle_logged(user)
                elif type_stripped == "ALERT":
                    self.handle_alert(user)

    def handle_login(self, user, protocol_message):
        """handle user trying to login"""
        client_socket = user.get_client_socket()
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
        user.set_username(user_and_pass[0])
        user.set_password(user_and_pass[1])
        user.set_city(user_and_pass[2])
        self.logged_users.append(user)  # add to connected clients
        logging.info(f"now logged users are: {self.logged_users}")

    def hash_password(self, password):
        """Hashes the password using SHA-256"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def authenticate(self, username, password, city):
        """checking the username, password and city for login"""
        hashed_password = self.hash_password(password)
        with self.lock:
            with open(self.cities_file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                cities = [area["label"] for area in data]
            with open(self.users_file_path, 'r') as file:
                for line in file:
                    try:
                        stored_username, stored_password = line.strip().split(":")
                    except ValueError:
                        logging.error("something went wrong")
                        return False
                    if username == stored_username and stored_password == hashed_password and city in cities:
                        return True
        return False

    def handle_register(self, user, protocol_message):
        """handle client trying to register"""
        client_socket = user.get_client_socket()
        type1, num1, data1 = self.split_msg(protocol_message, 2)
        user_and_pass = data1.split(":")
        if len(user_and_pass) != 2:
            self.build_send(client_socket, "ERROR", "Login message should look like 'username:password'")
            return None
        # check if the username exist
        with self.lock:
            with open("users.txt", 'r') as file:
                usernames = [line.strip().split(':')[0] for line in file if len(line.strip().split(':')) == 2]
        if user_and_pass[0] in usernames:  # the username already exist
            self.build_send(client_socket, "ERROR", f"The Username '{user_and_pass[0]}' Is Already Exist")
            return None
        if user_and_pass[0] == "username" or user_and_pass[1] == "password" or not user_and_pass[0].isalpha() or not user_and_pass[1].isalpha():
            self.build_send(client_socket, "ERROR", "You Can Only Use Letters")
            return None
        self.build_send(client_socket, "MESSAGE", "you are registered!")
        with self.lock:
            with open("users.txt", 'a') as file:
                file.write(f"{user_and_pass[0]}:{self.hash_password(user_and_pass[1])}\n")


    def handle_logout(self, user):
        """handle client logout"""
        client_socket = user.get_client_socket()
        if user in self.logged_users:
            try:
                self.logged_users.remove(user)
            except ValueError:
                logging.error(f"in handle_logout function, user: {user} not found in the list.")
            logging.info(f"now logged users are: {self.logged_users}")
            # attempt to send logout message
            try:
                self.build_send(client_socket, "MESSAGE", "You have been logged out.")
            except (BrokenPipeError, ConnectionError):
                # handle the case where the client has closed the connection
                logging.error("Client has closed the connection.")

    def handle_logged(self, user):
        """sending the client a list of the logged users"""
        client_socket = user.get_client_socket()
        try:
            logged_string = str(functools.reduce(lambda x, y: f"{str(x)}, {str(y)}",
                                                 [username for username in self.get_list("username")]))
            self.build_send(client_socket, "MESSAGE", logged_string)
        except (BrokenPipeError, ConnectionError):
            # handle the case where the client has closed the connection
            logging.error("Error handling LOGGED command / lost connection")



    def handle_alert(self, user):
        """handle if there is alert"""
        client_socket = user.get_client_socket()
        self.build_send(client_socket, "ALERT", "מוות לחמאס")


    def run(self):
        """run the server and handling connections of clients"""
        find_alert_thread = threading.Thread(target=self.find_alert, args=())
        find_alert_thread.start()
        while True:
            client, addr = self.server_socket.accept()
            user = User(client_socket=client, ip=addr[0], username=None, password=None, city=None)
            logging.info(f"Accepted connection from {addr}")

            # Exchange public keys
            client_public_key = int(client.recv(1024).decode())
            client.send(str(self.public_key).encode())
            shared_secret = self.dh.gen_shared_key(client_public_key)
            self.shared_secrets[client] = shared_secret

            client_thread = threading.Thread(target=self.handle_client, args=(user,))
            client_thread.start()

    def find_alert(self):
        """checks in a loop if one of the logged user's city has alert and if True, handle_alert(user)"""
        while True:
            for user in self.logged_users:
                if azakot.find_alert_by_city(user.get_city()):
                    self.handle_alert(user)
                else:
                    pass
            time.sleep(3)  # un-harming the servers


if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 12345

    server = Server(HOST, PORT)
    server.run()
