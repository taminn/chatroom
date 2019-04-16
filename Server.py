import socket
import threading
import sqlite3
import os
import sys
import time


#普通全局数据-------------------------------------------------------
host=socket.gethostbyname(socket.gethostname())
print("server ip",host)
port=5000

#存在互斥访问情况的数据----------------------------------------------
db=None
user_list={} #根据ip标记用户
msg_list=[]
log_list=[]


#锁----------------------------------------------------------------
db_lock=threading.Lock()
user_list_lock=threading.Lock()
msg_list_lock=threading.Lock()
log_list_lock=threading.Lock()

#功能性函数---------------------------------------------------------
def now_datetime():
    nowtime=int(time.time())
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(nowtime))

def format_datetime(datetime):
    print(datetime)
    print(type(datetime))
    res= time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(datetime))
    return res

#数据库相关---------------------------------------------------------

class UserMsg():
    def __init__(self,ip,username,time,msg):
        self.ip,self.username,self.time,self.msg=ip,username,time,msg
    def __str__(self):
        datetime=time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(self.time))
        return self.ip+' '+self.username+' '+datetime+' '+self.msg

class Log():
    def __init__(self,time,log):
        self.time,self.log=time,log
    def __str__(self):
        return format_datetime(self.time)+" "+self.log

def open_db():
    os.chdir(sys.path[0])
    global db
    try:
        db=sqlite3.connect('./data.db',check_same_thread=False)
    except:
        return False
    return True

def close_db():
    global db
    global db_lock
    db_lock.acquire()
    db.close()
    db=None
    db_lock.release()

def init_datebase():
    global db
    global db_lock
    db_lock.acquire()
    db_is_open=False
    if db!=None:
        db.close()
        db=None
        db_is_open=True
    os.chdir(sys.path[0])
    if os.path.exists("./data.db"):
        os.remove("./data.db")
    open_db()

    sql='''
        create table UserMsgs(
            ip text,
            username text,
            time int,
            msg text
        )'''

    cursor=db.cursor()
    cursor.execute(sql)
    cursor.close()
    if(not db_is_open):
        close_db()

def insert_msg_to_db():
    global msg_list
    global db
    msg_list_lock.acquire()
    msg_list_cp=msg_list[:]
    msg_list_lock.release()
    cursor=db.cursor()
    for i in msg_list_cp:
        sql='''
            insert into UserMsgs
            (ip,username,time,msg)
            values
            ("{ip}","{username}","{time}","{msg}")
            '''.format(ip=i.ip,username=i.username,time=i.time,msg=i.msg)
        cursor.execute(sql)
    cursor.close()

def auto_write_msg_to_db():
    insert_msg_to_db()
    time.sleep(5)
    
def write_msg(data):
    global db
    if db==None:
        quit()
    db_lock.acquire()
    cursor=db.cursor()
    for i in data:
        sql='''
            insert into UserMsgs
            (ip, username, time,msg)
            values
            ("{ip}","{username}",{time},"{msg}")
            '''.format(ip=i.ip,username=i.username,time=i.time,msg=i.msg)
        cursor.execute(sql)
    cursor.close()
    db.commit()
    db_lock.release()

def add_log(log):
    global log_list
    log_list.append(Log(int(time.time()),log))
    if len(log_list)==1000:
        write_log()


def write_log():
    os.chdir(sys.path[0])
    datetime=now_datetime()
    log_file=open("./"+datetime+".txt",'w')
    global log_list_lock
    global log_list
    log_list_lock.acquire()
    for i in log_list:
        log_file.write(str(i)+'\n')
    log_file.close()
    log_list.clear()
    log_list_lock.release()

def query_msg_by_ip(ip):
    sql='''
        select * from UserMsgs
        where
        ip="{ip}"
        '''.format(ip=ip)
    global db
    cursor=db.cursor()
    res=cursor.execute(sql).fetchall()
    cursor.close()
    msgs=[]
    for i in res:
        msgs.append(UserMsg(i[0],i[1],i[2],i[3]))
    for i in msg_list:
        if i.ip==ip:
            msgs.append(i)
    return msgs

def query_msg_by_username(username):
    sql='''
        select * from UserMsgs
        where
        username="{username}"
        '''.format(username=username)
    global db
    global msg_list
    cursor=db.cursor()
    res=cursor.execute(sql).fetchall()
    cursor.close()
    msgs=[]
    for i in res:
        msgs.append(UserMsg(i[0],i[1],i[2],i[3]))
    for i in msg_list:
        if i.username==username:
            msgs.append(i)
    return msgs

#消息接收转发--------------------------------------------------------

def add_user(addr,username):
    global user_list
    global log_list
    user_list[addr]=username
    add_log("get connect "+addr+" "+username)

def del_user(addr):
    global user_list
    del_username=user_list[addr]
    try:
        del user_list[addr]
    except:
        pass
    add_log("lost connect "+addr+" "+del_username)

def send_msg(user_ip,msg):
    client_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        client_socket.connect((user_ip,5001))
    except TimeoutError:
        del_user(user_ip)
        return False
    client_socket.send(msg.encode())
    client_socket.close()
    return True

def forward_msg(ip,msg):
    global user_list
    global msg_list
    global user_list_lock
    global host
    msg_list.append(UserMsg(ip,user_list[ip],int(time.time()),msg))
    user_list_lock.acquire()
    username=user_list[ip]
    for user_ip in user_list.keys():
        if ip!=user_ip and user_ip!=host:
             send_msg_thread=threading.Thread(target=send_msg,args=(user_ip,username+':'+msg))
             send_msg_thread.start()
    user_list_lock.release()

def open_server():
    global host
    global port
    global user_list
    open_db()
    auto_write_msg_thread=threading.Thread(target=auto_write_msg_to_db(),args=())
    auto_write_msg_thread.start()
    user_list[host]="admin"

    server_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    server_socket.bind((host,port))
    server_socket.listen(5)
    while True:
        client,addr=server_socket.accept()
        msg=client.recv(4096).decode()
        client.close()
        if addr[0] in user_list:
            disposeMsg=threading.Thread(target=forward_msg,args=(addr[0],msg))
            disposeMsg.start()
        else:
            add_user(addr[0],msg)

def menu():
    print("1:open server")
    print("2:print log")
    print("3:print currently users list")
    print("4:send admin message")
    print("5:query by ip")
    print("6:query by username")
    print("7:clear screen message")
    print("8:init database")
    print("9:ready to quit")

if __name__=="__main__":
    menu()
    while True:
        try:
            op=int(input())
        except:
            print("invalid command")
            continue
        if op==1:
            server_thread=threading.Thread(target=open_server,args=())
            server_thread.start()
        elif op==2:
            write_log()
        elif op==3:
            print("current users:")
            user_list_lock.acquire()
            for i in user_list.items():
                print(i[0],i[1])
            user_list_lock.release()
        elif op==4:
            admin_msg=input("input admin message:\n")
            send_admin_msg_thread=threading.Thread(target=forward_msg,args=(host,admin_msg))
            send_admin_msg_thread.start()
        elif op==5:
            ip=input("input ip:\n")
            query_res=query_msg_by_ip(ip)
            if len(query_res)==0:
                print("don't exist any information")
                continue
            for i in query_res:
                print(i)
        elif op==6:
            username=input("input username:\n")
            query_res=query_msg_by_username(username)
            if len(query_res)==0:
                print("don't exist any information")
                continue
            for i in query_res:
                print(i)
        elif op==7:
            os.system("cls")
            menu()
        elif op==8:
            init_datebase()
        elif op==9:
            insert_msg_to_db()
            close_db()
            write_log()
            print("success close")
        else:
            print("invalid command")
        
