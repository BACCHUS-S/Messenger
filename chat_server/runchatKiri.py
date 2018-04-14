#!/usr/bin/env python 2.x

import socketserver, socket
import threading
from os.path import exists, isfile
from time import sleep, strftime, time, localtime
import signal
from aes import myAES
from os import system, fork, kill
from sys import argv
from random import shuffle, randrange

HOST = ''
PORT = 10007
aes = myAES('test', 'test')
pidfile = '.chatserverP.pid'
dummy_proc = '0000'
VER = '1.4 Public'

class UserManager:
    def __init__(self):
        self.users = {}
        self.members = []
        self.lock = threading.Lock()
        
    def addUser(self, username, conn, addr):
        global WELCOME_EMOTI

        if username in self.users:
            msg = aes.enc('이미 등록된 사용자입니다.\n'.encode())
            conn.send(msg)
            return None

        if len(self.users) > 5:
            msg = aes.enc('사용자수 초과입니다.\n'.encode())
            conn.send(msg)
            return None
        
        with self.lock:
            self.users[username] = (conn, addr)
            self.members.append(username)
        
        try:
            welcome_msg = '/welcome;%s' %username
            welcome_msg = aes.enc(welcome_msg.encode())
            conn.send(welcome_msg)
            memberlist = '#'.join(self.members)
            self.sendMessageToAll('/addmember;%s;[%s]님이 입장했습니다.\n\n' %(memberlist, username))
        except Exception as e:
            writeLog('Error-1: ' + str(e))
            pass
        
        return username
    
    def removeUser(self, username):
        if username not in self.users:
            return

        with self.lock:
            del self.users[username]
            if username in self.members:
                self.members.remove(username)
            if username+'(X)' in self.members:
                self.members.remove(username+'(X)')

        memberlist = '#'.join(self.members)
        self.sendMessageToAll('/delmember;%s;[%s]님이 퇴장했습니다.\n\n' %(memberlist, username))
        
    def messageHandler(self, username, msg):
        msg = msg.strip()
        try:
            if msg[0] != '/':
                self.sendMessageToAll('/msgbody;%s;%s' %(username, msg))
                return

            if msg == '/absence':
                pos = self.members.index(username)
                self.members[pos] = username + '(X)'
                memberlist = '#'.join(self.members)
                self.sendMessageToAll('/updatepresence;%s' %memberlist)
                return

            if msg == '/presence':
                pos = self.members.index(username+'(X)')
                self.members[pos] = username
                memberlist = '#'.join(self.members)
                self.sendMessageToAll('/updatepresence;%s' %memberlist)
                return

            if '/emoticon' in msg:
                self.sendMessageToAll(msg)
                return

            if msg == '/quit':
                msg = aes.enc('/bye'.encode())
                self.users[username][0].send(msg)
                self.removeUser(username)
                return -1

            if msg == '/keypressed':
                self.sendMessageWithoutMe(username, 0)
                return

            if msg == '/emptymsg':
                self.sendMessageWithoutMe(username, 1)
                return

            if '/personalchat' in msg:
                tmp = msg.split(';')
                self.sendMessage2Users(username, tmp[1], ';'.join(tmp[2:]))
                return
        except Exception as e:
            writeLog('Error-1-1: '+str(e))

    def sendMessageToAll(self, msg):
        try:
            msg = aes.enc(msg.encode())
            for conn, addr in self.users.values():
                conn.send(msg)
            #print('SENDINGALL')
        except Exception as e:
            writeLog('Error-2: ' + str(e))
            pass

    def sendMessageWithoutMe(self, username, mode):
        try:
            if mode == 0:
                msg = '/keypressed;%s' %username
            else:
                msg = '/emptymsg;%s' %username

            msg = aes.enc(msg.encode())
            for user, val in self.users.items():
                if user == username:
                    continue
                val[0].send(msg)
        except Exception as e:
            writeLog('Error-3: ' + str(e))
            pass

    def sendMessage2Users(self, username, yourname, msg):
        try:
            conn1 = self.users[username][0]
            conn2 = self.users[yourname][0]
            header = '/personalchat#%s#%s#' %(username, yourname)
            msg = header + msg
            msg = aes.enc(msg.encode())
            conn1.send(msg)
            conn2.send(msg)
        except Exception as e:
            writeLog('Error-4: '+str(e))

class MyTcpHandler(socketserver.BaseRequestHandler):
    userman = UserManager()
    heartbits = [chr(x) for x in range(40, 120)]
    
    def handle(self):
        self.request.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        username = ''
        buf = b''
        try:
            while True: 
                msg = self.request.recv(65565)
                if not msg:
                    break

                if len(msg)%16 != 0:
                    #writeLog('INCOMMING MSG LENGTH [%d]' %len(msg))
                    buf += msg
                    if len(buf)%16 != 0:
                        continue
                    else:
                        msg = buf
                        buf = b''

                msg = aes.dec(msg)
                if msg == None:
                    continue
                msg = msg.strip()
                #print(msg)
                #writeLog('INCOMING MSG [%s]: %s' %(username, msg))

                if msg == '/login':
                    username = self.registerUsername()
                    continue

                if '$%#' in msg:
                    shuffle(self.heartbits)
                    randstr = ''.join(self.heartbits)
                    scope1 = randrange(1, max(2,len(randstr)-1))
                    scope2 = randrange(1, max(2,scope1))

                    if scope1 == scope2:
                        scope1 += 1
                
                    msg = randstr[:scope2] + '$%#' + randstr[scope2:scope1]
                    msg = aes.enc(msg.encode())
                    self.request.send(msg)
                    #writeLog('INCOMING HEARTBIT[%s]' %username)
                    continue

                ret = self.userman.messageHandler(username, msg)
                #writeLog('CALL Message Handler')
                if ret == -1:
                    self.request.close()
                    break
    	                
        except Exception as e:
            log = 'Error-5: [%s] %s' %(username, str(e))
            writeLog(log)
            self.userman.removeUser(username)
            pass
            
        
    def registerUsername(self):
        try: 
            flag = True
            try:
                with open('notice.txt', 'r') as f:
                    notice = f.read()
            except:
                notice = ''

            while True:
                if flag:
                    msg = '끼리서버 ver. %s\n\n%s\n[대화명을 입력하세요]\n' %(VER, notice)
                    msg = aes.enc(msg.encode())
                    self.request.send(msg)
                    flag = False
                username = self.request.recv(65565)
                username = aes.dec(username)
                if username[0] == '/':
                    continue
                #writeLog('Call Add Username: %s' %username)
                if self.userman.addUser(username, self.request, self.client_address):
                    return username
        except Exception as e:
            writeLog('Error-6: '+str(e))
            self.userman.removeUser(username)
            pass
 
def writeLog(log):
    tstr = strftime('%Y-%m-%d %H:%M:%S;', localtime())
    log = tstr + log  + '\n'  
    with open('chat2.log', 'a') as f:
        f.writelines(log)
         
class ChatingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def runServer(args):
    if len(args) == 0:
        print('사용법: ./runchat -s or -x')
        return

    if args[0] == '-s':
        if isfile(pidfile):
            print('서버가 이미 구동중입니다.')
            return

        try:
            with open(pidfile, 'w') as h:
                h.write(dummy_proc)
        except Exception as e:
            print(str(e))
            return

        pid = fork()
        if pid == 0: # Child Process
            try:
                server = ChatingServer((HOST, PORT), MyTcpHandler)
                server.serve_forever()
            except KeyboardInterrupt:
                server.shutdown()
                server.server_close()
        else:
            print('+++ 채팅 서버를 시작합니다.')
            with open(pidfile, 'w') as h:
                h.write('%d' %pid)

    elif args[0] == '-x':
        try:
            with open(pidfile, 'r') as h:
                pid = h.readline()
        except Exception as e:
            print('.chatserver.pid 파일을 읽지 못했습니다.')
            return

        try:
            kill(int(pid), signal.SIGINT)
            print('--- 채팅 서버를 종료중입니다..')
            sleep(1)
            kill(int(pid), signal.SIGINT)
        except:
            pass

        cmd = 'rm -rf %s' %pidfile
        system(cmd)

        print('--- 채팅 서버를 종료했습니다.')

    else:
        print('사용법: ./runchat -s or -x')
       

if __name__ == '__main__':
    runServer(argv[1:])
