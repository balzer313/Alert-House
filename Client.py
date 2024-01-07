import socket
import functools

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        self.message_types = ["LOGIN", "LOGOUT", "GET", "MESSAGE", "LOGGED"]
        self.username = None
        self.password = None

    def close(self):
        self.client_socket.close()
    def build_msg(self, msg_type, data):#build and return message by the protocol(if msg_type or data is wrong return None)
        if msg_type not in self.message_types:
            return None
        return f"{msg_type.ljust(10)}|{str(len(data)).zfill(6)}|{data}"

    def parse_msg(self, protocol_message):#get protocol message and return the splitted parts(message type, length of data, and data)
        splitted = self.split_msg(protocol_message, 2)
        return splitted[0], splitted[1], splitted[2] if len(splitted) > 2 else None

    def b_s_r_p(self, msg_type, data):#build message, send message, receive answer, return parse message
        self.client_socket.send(self.build_msg(msg_type, data).encode('utf-8'))
        print(f"sent: {self.build_msg(msg_type, data)}")
        received = self.client_socket.recv(1024).decode('utf-8')
        print(f"received: {received}")
        return self.parse_msg(received)

    def split_msg(self, str, mafridim):#checks if str's '|' seperators are the like the number of mafridim(if yes returns splitted list, if not return None)
        splitted = str.split("|")
        if len(splitted) == mafridim+1:
            return splitted
        return None
    def join_msg(self, list):#join the list to a message with seperators and return it
        return str(functools.reduce(lambda x, y: f"{str(x)}|{str(y)}", list))
    def login(self):
        login_message = f"{self.username}:{self.password}"
        type1, num1, data1 = self.b_s_r_p("LOGIN", login_message)
        print(data1)
    def logout(self):
        type1, num1, data1 = self.b_s_r_p("LOGOUT", "")
        print(data1)

    def logged(self):
        type1, num1, data1 = self.b_s_r_p("LOGGED", "")
        print(data1)
    def handle_options(self, option):
        if option not in self.message_types:
            print("not an option!")
            return
        if option == "LOGIN": self.username = input("enter username: "); self.password = input("enter password: "); self.login()
        elif option == "LOGOUT": self.logout()
        elif option == "LOGGED": self.logged()

    def close(self):
        self.client_socket.close()


if __name__ == "__main__":
    HOST = '127.0.0.1'
    PORT = 12345

    client = Client(HOST, PORT)

    try:
        while True:
            what = input("Choose: LOGIN / LOGOUT / LOGGED / EXIT : ")
            if what.upper() == 'EXIT':
                break
            client.handle_options(what)
    except KeyboardInterrupt:
        print("\nClient terminated by user.")
    client.close()