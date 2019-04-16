import socket
import threading

host=socket.gethostbyname(socket.gethostname())
port=5001
serverHost=input("input server ip\n")
serverPort=5000

client=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
client.bind((host,port))

client.listen(5)

server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.connect((serverHost,serverPort))
userName=input("Please input your name:")
server.send(userName.encode())
server.close()
print("Ok,welcome!")

def recvMsg(server):
    msg=server.recv(4096).decode()
    server.close()
    print(msg)
def sendMsg(serverHost,serverPort):
    while True:
        msg=input()
        toServer=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        toServer.connect((serverHost,serverPort))
        toServer.send(msg.encode())
        toServer.close()
inputAndSendMsg=threading.Thread(target=sendMsg,args=(serverHost,serverPort))
inputAndSendMsg.start()
while True:
    server,addr=client.accept()
    printMsg=threading.Thread(target=recvMsg,args=(server,))
    printMsg.start()
