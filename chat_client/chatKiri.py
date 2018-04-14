__author__ = 'sunghyeon86@gmail.com'


from tkinter import *
import tkinter.ttk as ttk
import threading
import socket
from PIL import ImageTk, Image, ImageSequence
import win32gui
from time import strftime, localtime, sleep, time
import webbrowser
from aes import myAES
from emoticons import EmoticonBox
import os
from random import shuffle, randrange

messenger_title = '챗끼리'   # 채팅클라이언트 타이틀바 제목
chaticon = 'image/chat.ico'  # 채팅클라이언트 아이콘
chatserverip = 'epaiai.com'  # 채팅서버 주소
portnum = 10007              # 채팅서버 포트번호

lock = threading.Lock()
aes1 = myAES('test', 'test') # 송신 AES
aes2 = myAES('test', 'test') # 수신 AES

HEARTBIT_EXPIRED = 100             # 핫빗요청에 대한 응답 유효 시간
ABSENCE_TIME = 300                 # 자리비움 설정 시간

hyperlink_counter = 0
hyper_links = {}
hyper_urls = {}

END_PROG = False


# 이모니콘 GIF 애니메이션을 위한 클래스
class AnimatedGif(object):
    """ Animated GIF Image Container. """
    def __init__(self, image_file_path):
        self.image_file_path = image_file_path
        self._load()

    def __len__(self):
        return len(self._frames)

    def __getitem__(self, frame_num):
        return self._frames[frame_num]

    def _load(self):
        """ Read in all the frames of a gif image. """
        self._frames = []
        img = Image.open(self.image_file_path)
        for frame in ImageSequence.Iterator(img):
            photo = ImageTk.PhotoImage(frame)
            photo.delay = frame.info['duration']  # add attribute
            self._frames.append(photo)


# 하이퍼링크 처리를 위한 클래스
class HyperlinkManager:
    def __init__(self, text):

        self.text = text
        self.text.tag_config("hyper", foreground="blue", underline=1)
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)

        self.reset()

    def reset(self):
        self.links = {}

    def add(self, action, url):
        global hyperlink_counter, hyper_links, hyper_urls
        
        # add an action to the manager.  returns tags to use in
        # associated text widget

        hyperlink_counter += 1        
        tag = "hyper-%d" % (len(self.links)+hyperlink_counter)        
        hyper_links[tag] = action
        hyper_urls[tag] = url
        
        return "hyper", tag

    def _enter(self, event):
        self.text.config(cursor="hand2")

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        for tag in self.text.tag_names(CURRENT):
            if tag[:6] == "hyper-":
                url = hyper_urls[tag]
                hyper_links[tag](url)
                return


# 하이퍼링크를 클릭하면 호출되는 함수
def click(url):
    webbrowser.open_new(url)

    
# 이모티콘 이미지 로딩
def loadImage(folder):
    emoticons_container = {}
    emoticonlist = os.listdir(folder)

    for emoticon in emoticonlist:            
        emoticon = folder +'/' + emoticon
        emotiimg = ImageTk.PhotoImage(Image.open(emoticon))
        emoticons_container[emoticon] = emotiimg

    return emoticons_container


# 채팅 클라이언트 메인 클래스
class ChatClient():
    def __init__(self, HOST, PORT):
        global LOGO
        
        self.me = ''                # 채팅클라이언트의 주인의 대화명
        self.yourname = ''          # 1:1 대화시 상대방 대화명
        self.title = messenger_title
        self.keypress_members = []  # 대화창에 메시지를 입력하는 멤버 리스트
        self.isKeyPressed = False   # 내가 메시지를 입력하는지 체크하는 플래그
        self.isEmptyMsg = True      # 메시지 입력창에 내용이 비어있는지 체크하는 플래그
        self.last_recvmsg_time = time()  # 메시지 최근 수신 시간

        self.host = HOST    # 채팅서버 IP 또는 도메인주소
        self.port = PORT    # 채팅서버 포트번호

        
        self.lastevent = time() # 마지막으로 메신저 프로그램에 마우스 클릭이 일어난 시간을 저장하는 변수
        self.isAbsence = False  # 자리비움 플래그

        # 채팅 클라이언트 UI를 정의
        root = Tk()        
        root.protocol("WM_DELETE_WINDOW", self.destroyWin)  # 메신저 닫기 했을 때 발생하는 이벤트처리

        self.root = root
        
        self.root.title(self.title) 
        self.root.iconbitmap(chaticon)      # 메신저 아이콘 설정
        self.root.resizable(width=False, height=False)

        # 마우스 왼쪽 버튼을 누르면 호출되는 함수와 바인딩
        self.root.bind('<Button-1>', self.mouseClick)

        # 메신저에 키보드를 누르면 호출되는 함수와 바인딩
        self.root.bind('<Key>', self.keyPressedAtRoot)

        # 메신저 윈도우에서 발생하는 이벤트를 캡쳐하기 위함
        self.root.bind('<Configure>', self.configEvent)
        

        # 이모티콘 입력 버튼에 삽입될 이미지
        imgbutton = PhotoImage(file="image/emoti1.png")
        imgbutton2 = PhotoImage(file="image/emoti2.png")
        imgbutton3 = PhotoImage(file="image/emoti3.png")
        imgbutton4 = PhotoImage(file="image/emoti4.png")

        # 핫빗 수신을 나타내기 위한 점멸등 이미지
        self.hbitimg1 = PhotoImage(file='image/greenball.png')
        self.hbitimg2 = PhotoImage(file='image/redball.png')

        # 화면 아래에 표시될 2개의 상태표시창에 출력될 변수
        self.statusmsg = StringVar()
        self.statusmsg2 = StringVar()
        self.mymsg = StringVar()

        self.statusmsg0 = StringVar()
        self.mymsg0 = StringVar()

        """try:
            LOGO = ImageTk.PhotoImage(Image.open('image/chat4.png'))
        except Exception as e:
            #print(str(e))
            pass"""
        
        
        # 메인프레임 정의
        content = ttk.Frame(self.root, padding=(6, 6, 6, 6))
        content.grid(column=0, row=0, sticky=(N, W, E, S))        

        #logo_panel = ttk.Frame(content, padding=(3,3,3,3))        
        panel1 = ttk.Frame(content, relief='groove', padding=(3,3,3,3)) 
        panel2 = ttk.Frame(content, relief='groove', padding=(3,3,3,3))
        panel3 = ttk.Frame(content, padding=(3,3,3,3))
        
        panel1.grid(column=0, row=0, sticky=(N, W, E, S))
        panel2.grid(column=0, row=1, sticky=(N, W, E, S))
        panel3.grid(column=0, row=2, sticky=(N, W, E, S))

        self.panel1 = panel1
        self.panel2 = panel2
        self.panel3 = panel3
        
        
        # 대화 표시창 생성
        self.textoutwin = Text(panel1, relief='solid', width=50, height=38, font=('맑은 고딕', 9))
        self.textoutysb = ttk.Scrollbar(panel1, orient=VERTICAL, command=self.textoutwin.yview)
        self.textoutwin['yscroll'] = self.textoutysb.set

        # 멤버 표시창 생성
        self.memberwin = Listbox(panel1, relief='solid', width=20, height=31)
        #self.memberwin.bind('<Double-1>', self.selectMemeber)
        self.memberwin.bind('<Button-1>', self.selectMemeber)

        # 메신저 화면 투명 설정 바 생성
        self.transparency = Scale(panel1, from_=0, to=70, orient=HORIZONTAL, command=self.setTransparency)

        # 핫빗 점멸등
        self.hbit = Label(panel1)
        self.hbit.configure(image=self.hbitimg1)
        self.hbit.image = self.hbitimg1

        # 이모티콘 선택 버튼 생성
        self.selemoticon1 = Button(panel1, image=imgbutton, command=self.selectEmoticon1)
        self.selemoticon1.image = imgbutton
        
        self.selemoticon2 = Button(panel1, image=imgbutton2, command=self.selectEmoticon2)
        self.selemoticon2.image = imgbutton2

        self.selemoticon3 = Button(panel1, image=imgbutton3, command=self.selectEmoticon3)
        self.selemoticon3.image = imgbutton3

        self.selemoticon4 = Button(panel1, image=imgbutton4, command=self.selectEmoticon4)
        self.selemoticon4.image = imgbutton4
        
        # 대화 입력창 생성
        self.textinwin = Entry(panel2, width=73, textvariable=self.mymsg)

        # 키보드를 누르면 호출되는 함수와 바인딩
        self.textinwin.bind('<Key>', self.keyPressed)

        # 1:1 대화 상태 표시창 생성        
        self.status0 = ttk.Label(panel2, textvariable=self.statusmsg0, anchor=W)

        # 1:1 대화 입력창 생성
        self.textinwin0 = Entry(panel2, width=73, textvariable=self.mymsg0)
        self.textinwin0.config(state=DISABLED)

        # 상태 표시창 생성        
        self.status = ttk.Label(panel3, width=40, textvariable=self.statusmsg, anchor=W)

        # 상태 표시창2 생성        
        self.status2 = ttk.Label(panel3, width=30, textvariable=self.statusmsg2, anchor=E)
        

        # 엔터키와 메시지 전송 함수 바인딩
        self.textinwin.bind('<Return>', self.sendMessage)

        # 엔터키와 1:1 메시지 전송 함수 바인딩
        self.textinwin0.bind('<Return>', self.sendMessage0)
        
        # 대화 표시창 및 스크롤바 위치 시키기
        self.textoutwin.grid(column=0, rowspan=3, row=0, sticky=W)
        self.textoutysb.grid(column=1, rowspan=3, row=0, sticky=NS)

        # 멤버 표시창 위치 시키기
        self.memberwin.grid(column=2, columnspan=4, row=0, sticky=E)

        # 이모티콘 선택 버튼1, 2 위치 시키기
        self.selemoticon1.grid(column=2, row=1, sticky=E)
        self.selemoticon2.grid(column=3, row=1, sticky=E)
        self.selemoticon3.grid(column=4, row=1, sticky=E)
        self.selemoticon4.grid(column=5, row=1, sticky=E)        

        # 투명 설정바 위치 시키기
        self.transparency.grid(column=2, columnspan=3, row=2, sticky=W)        

        # 핫빗 점멸등 위치 시키기
        self.hbit.grid(column=5, row=2, sticky=SE)          
        
        # 대화 입력창 위치 시키기
        self.textinwin.grid(column=0, row=0, sticky=W)

        # 1:1 대화창 상태 표시창 위치 시키기
        self.status0.grid(column=0, row=1, sticky=W)
        self.textinwin0.grid(column=0, row=2, sticky=W)

        # 상태 표시창 위치 시키기
        self.status.grid(column=0, row=0, sticky=W)
        self.status2.grid(column=1, row=0, sticky=E)

        # 포커스를 메시지 입력창에 두기
        self.textinwin.focus()

        # 이모티콘 이미지 reading and saving
        self.emoticons = loadImage('emoti/large')
        self.katok_emoticons = loadImage('emoti/katok/large')
        self.katokgif1_emoticons = loadImage('emoti/gif1/large')
        self.katokgif2_emoticons = loadImage('emoti/gif2/large')

        self.statusmsg0.set('1:1 은밀히 대화하기-대화상대를 클릭한 후 메시지를 입력하세요')
    

    # 이모티콘 선택 로직
    def selectEmoticon1(self):        
        self.emotiobj = EmoticonBox(Toplevel(), 'emoti')
        self.emotiobj.showEmoticons(self)
        #self.emotiobj.mainloop()

    def selectEmoticon2(self):        
        self.emotiobj = EmoticonBox(Toplevel(), 'emoti/katok')
        self.emotiobj.showEmoticons(self)
        #self.emotiobj.mainloop()        

    def selectEmoticon3(self):        
        self.emotiobj = EmoticonBox(Toplevel(), 'emoti/gif1')
        self.emotiobj.showEmoticons(self)
        #self.emotiobj.mainloop()

    def selectEmoticon4(self):
        self.emotiobj = EmoticonBox(Toplevel(), 'emoti/gif2')
        self.emotiobj.showEmoticons(self)
        #self.emotiobj.mainloop() 

    # 메신저 화면 투명도 설정 로직
    def setTransparency(self, event):
        val = (100-self.transparency.get())/100        
        self.root.wm_attributes("-alpha", val)
        #print(val)

    # 핫빗 점멸을 위한 쓰레드
    def blinkHbitStatus(self):
        hbitimgs = [self.hbitimg1, self.hbitimg2]

        try:
            for i in range(4):
                img = hbitimgs[(i+1)%2]
                self.hbit.configure(image=img)
                self.hbit.image = img
                sleep(0.2)
        except:
            pass

        return


    # 메신저 프로그램에서 ESC를 눌렀을 때 처리
    def keyPressedAtRoot(self, event):
        try:
            if event.char == '\x1b': # ESC 키값
                self.destroyWin()
        except:
            pass
        

    # 자리비움인지 체크하기, 5분동안 메신저에 이벤트가 없을 때 자리비움으로 설정함
    def checkIdle(self):
        global END_PROG
        
        while not END_PROG:
            t = time() - self.lastevent            
            if t > ABSENCE_TIME and not self.isAbsence:
                self.isAbsence = True
                with lock:
                    msg = aes1.enc('/absence'.encode())
                    self.sock.send(msg)

            sleep(61)
            
        

    # 사용자의 Presence 체크
    def checkPresence(self):        
        if self.isAbsence:
            self.isAbsence = False
                
            with lock:
                msg = aes1.enc('/presence'.encode())
                self.sock.send(msg)
        

    # 대화입력창에서 키보드를 눌렀을 때 처리 로직
    def keyPressed(self, event):
        try:            
            self.checkPresence()
                
            k = event.char            
            if not self.isKeyPressed and k != '\x1b' and k != '\x08':
                msg = aes1.enc('/keypressed'.encode())
                
                with lock:                
                    self.sock.send(msg)
                self.isKeyPressed = True
                self.lastevent = time()
                return

            if k == '\x08': # 지우기 백스페이스를 눌렀을 때
                content = self.mymsg.get()
                if len(content) == 1:
                    msg = aes1.enc('/emptymsg'.encode())
                    with lock:                
                        self.sock.send(msg)

                    self.isKeyPressed = False
                return
        except:
            pass
        

    # 메신저 창에 마우스를 클릭할 때 번쩍임 없애기
    def mouseClick(self, event):        
        #self.flashTitlebar(False)
        self.lastevent = time()        
        self.checkPresence()            


    # 메신저 윈도우가 활성화 되었을 경우
    def configEvent(self, event):        
        self.lastevent = time()        
        self.checkPresence()        
       

    # 멤버 리스트 창에서 멤버를 마우스 클릭할 때 처리 로직
    def selectMemeber(self, event):
        try:            
            self.yourname = self.memberwin.selection_get()
            if '(X)' in self.yourname:
                self.yourname = self.yourname[:-3]
                
            if self.yourname == '' or self.yourname == self.me:
                self.statusmsg0.set('1:1 은밀히 대화하기-대화상대를 클릭한 후 메시지를 입력하세요')
                self.textinwin0.config(state=DISABLED)
                return

            msg = '1:1 은밀히 대화하기 with [%s]' %self.yourname
            self.statusmsg0.set(msg)
            self.textinwin0.config(state=NORMAL)
        except:
            pass
        
        
    # 서버에 연결
    def connect(self):
        HOST = self.host
        PORT = self.port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        try:
            self.sock.connect((HOST, PORT))
            msg = aes1.enc('/login'.encode())
            self.sock.send(msg)
            
            t = threading.Thread(target=self.recvMessage)
            t.daemon = True
            t.start()
        except Exception as e:
            self.statusmsg.set(str(e))
            return

        self.statusmsg.set('보안채팅서버에 연결되었습니다')


    # 이모티콘 메시지 전송
    def sendEmoticon(self, msg):
        try:            
            if not msg:                
                return
            
            encmsg = aes1.enc(msg.encode())
            with lock:
                self.sock.send(encmsg)
                
        except Exception as e:
            self.statusmsg.set(str(e))
   

    # 엔터키를 누르면 메시지 전송하는 로직
    def sendMessage(self, *args):
        try:
            msg = self.mymsg.get()
            if not msg:                
                return
            
            encmsg = aes1.enc(msg.encode())
            with lock:
                self.sock.send(encmsg)
            self.textinwin.delete(0, END)            
         
            self.isKeyPressed = False            
        except Exception as e:
            self.statusmsg.set(str(e))
            

    # 엔터키를 누르면 1:1 메시지 전송 로직
    def sendMessage0(self, *args):
        try:
            msg = self.textinwin0.get()
            if not msg:
                return            
            
            msg = '/personalchat;' + self.yourname + ';' + msg
            msg = aes1.enc(msg.encode())

            with lock:
                self.sock.send(msg)
            self.textinwin0.delete(0, END)
            
        except Exception as e:
            self.statusmsg.set(str(e))
        

    # 메시지 수신 처리를 위한 쓰레드 함수 
    def recvMessage(self):        
        isStart = False  # 로그인이 완료되면 True로 설정되는 플래그
        tagstr = 'tg'
        tag_count = 0
        h_count = 0
        isPersonalChat = False
        
        while True:
            try:
                msg = self.sock.recv(65565)
                if not msg:
                    break
                

                # 메시지가 수신되면 수신시간 갱신
                self.last_recvmsg_time = time()
                self.statusmsg2.set('통신상태 OK')

                # AES로 암호화된 메시지 복호화
                msg= aes2.dec(msg)                

                tag_count += 1
                tag = tagstr + str(tag_count)
                
                # 메시지 수신 시각       
                tstamp = strftime('%H:%M:%S', localtime())

                # 메시지가 핫빗 응답일 때
                if '$%#' in msg:
                    t = threading.Thread(target=self.blinkHbitStatus)
                    t.daemon = True
                    t.start()
                    continue

                # 메시지가 환영 메시지일 때 - 대화명 입력 후 서버가 전송
                if '/welcome' in msg:
                    data = msg.split(';')                    
                    self.me = data[1]                    
                    self.statusmsg.set('')
                    isStart = True

                    t = threading.Thread(target=self.sendHeartbit)
                    t.daemon = True
                    t.start()

                    t = threading.Thread(target=self.checkIdle)
                    t.daemon = True
                    t.start()
                    continue

                # 상대방이 키를 누르고 있다는 메시지일 때
                if '/keypressed' in msg:
                    if not isStart:
                        continue

                    keypressedUser = msg.split(';')[1]
                    if keypressedUser not in self.keypress_members:
                        self.keypress_members.append(keypressedUser)

                    if len(self.keypress_members) > 1:
                        self.statusmsg.set('2명 이상이 메시지를 입력중입니다..')
                        continue

                    self.statusmsg.set('[%s]님이 메시지를 입력중입니다..' %keypressedUser)
                    continue
                

                # 상대방이 백스페이스 키를 눌러 메시지 입력창에 메시지가 없을 때
                if '/emptymsg' in msg:
                    keypressedUser = msg.split(';')[1]
                    if keypressedUser in self.keypress_members:
                        self.keypress_members.remove(keypressedUser)

                    if len(self.keypress_members) > 1:
                        self.statusmsg.set('2명 이상이 메시지를 입력중입니다..')
                    elif len(self.keypress_members) == 1:
                        self.statusmsg.set('[%s]님이 메시지를 입력중입니다..' %self.keypress_members[0])
                    else:
                        self.statusmsg.set('')
                    
                    continue
                

                # 멤버리스트창의 사용자 Presence 정보 업데이트
                if '/updatepresence' in msg:                    
                    data = msg.split(';')
                    memberlist = data[1].split('#')                    
                    self.updateMember(memberlist)
                    continue
                

                # 메신저 창이 현재 활성상태가 아닐 때 타이틀바를 번쩍이게 함
                if self.root.focus_get() == None:
                    self.flashTitlebar(True)
                    

                # 이모티콘 표현 메시지일 때
                if '/emoticon' in msg:                    
                    data = msg.split(';')
                    emoticonfile = data[1]
                    username = data[2]

                    mark = emoticonfile.split('/')[1]

                    if mark == 'katok':
                        emoticon_img = self.katok_emoticons[emoticonfile]
                    elif mark == 'gif1':
                        emoticon_img = self.katokgif1_emoticons[emoticonfile]
                    elif mark == 'gif2':
                        emoticon_img = self.katokgif2_emoticons[emoticonfile]
                    else:
                        emoticon_img = self.emoticons[emoticonfile]

                    self.textoutwin.config(state='normal')
                    if self.me == username:
                        username = tstamp + '\n'
                        self.colorText(tag, username, justification='right')
                    else:
                        username = '[' + username + '] ' + tstamp + '\n'
                        self.colorText(tag, username)
                    
                    if emoticonfile[-4:] == '.gif':
                        t = threading.Thread(target=self.animateGif, args=(emoticonfile, ))
                        #t = threading.Thread(target=self.animateGif, args=(emoticon_img, ))
                        t.daemon = True
                        t.start()
                    else:
                        #self.textoutwin.image_create(END, image=self.emoticons[emoticonfile])
                        self.textoutwin.image_create(END, image=emoticon_img) 
                        self.textoutwin.insert(END, '\n\n')
                        self.textoutwin.config(state='disabled')
                        self.textoutwin.see(END)
                        
                    continue
                

                # 새로운 멤버가 추가되었다는 메시지 일 때
                if '/addmember' in msg: 
                    data = msg.split(';')
                    memberlist = data[1].split('#')
                    msg = data[2]                    
                    self.updateMember(memberlist)
                    
                # 멤버가 퇴장했다는 메시지 일 때
                if '/delmember' in msg:                    
                    data = msg.split(';')
                    memberlist = data[1].split('#')
                    msg = data[2]
                    self.updateMember(memberlist)
                    
                # 메시지 표시창을 컨텐츠 입력 가능 모드로 변경
                self.textoutwin.config(state='normal')

                # 메신저 종료 메시지 일 때                   
                if msg == '/bye':
                    msg = self.me + '님이 퇴장했습니다. ' + tstamp
                    self.textoutwin.insert(END, msg)
                    self.textoutwin.see(END)
                    self.bye()
                    self.statusmsg.set('대화를 하려면 프로그램을 다시 시작하세요.')
                    break
                

                # 사용자의 대화 메시지일 때
                if '/msgbody' in msg:                    
                    msglist = msg.split(';')
                    username = msglist[1]
                        
                    msgbody = ';'.join(msglist[2:]) + '\n\n'
                    user = '[' + username + ']' + ' ' + tstamp + '\n'

                    # 입력한 메시지가 http://나 https://로 시작할 때
                    #if 'http://' in msgbody or 'https://' in msgbody:
                    if msgbody[:7] == 'http://' or msgbody[:8] == 'https://':
                        if self.me == username:
                            msgbody = tstamp + '\n' + msgbody
                            self.colorText(tag, msgbody, justification='right')
                        else:                            
                            self.colorText(tag, user)
                            hyperlink = HyperlinkManager(self.textoutwin)
                            self.textoutwin.insert(END, msgbody, hyperlink.add(click, msgbody))                            

                    # 메시지를 입력한 사람이 당사자이면 오른쪽으로 정렬, 타인이면 왼쪽으로 정렬함
                    else:
                        if self.me == username:
                            msg = tstamp + '\n' + msgbody
                            self.colorText(tag, msg, justification='right')
                        else:
                            msg = user + msgbody                            
                            self.colorText(tag, msg)

                    if username in self.keypress_members:
                        self.keypress_members.remove(username)
                    
                    if len(self.keypress_members) == 1:
                        self.statusmsg.set('[%s]님이 메시지를 입력중입니다..' %self.keypress_members[0])
                    elif len(self.keypress_members) == 0:
                        self.statusmsg.set('')
                        

                # 1:1 대화 모드일 때
                elif '/personalchat' in msg:                    
                    msglist = msg.split('#')
                    if len(msglist) != 4:
                        continue
                    
                    username = msglist[1]
                    yourname = msglist[2]
                    msgbody = msglist[3]

                    user = '[' + username + ' > ' + yourname + ' 1:1대화]' + ' ' + tstamp
                    msg = user + '\n' + msgbody + '\n\n'                    
                    self.colorText(tag, msg, font=('맑은 고딕', 9, 'bold'))
                    isPersonalChat = True

                else:      
                    #self.colorText(tag, msg, justification='right')
                    self.colorText(tag, msg)

                #self.textoutwin.see(END)                
                if self.textoutysb.get()[1] > 0.9:
                    self.textoutwin.see(END)
                    
                self.textoutwin.config(state='disabled')

                if isPersonalChat:
                    self.textinwin0.focus()
                    isPersonalChat = False
                else:
                    self.textinwin.focus()

            except Exception as e:
                pass
                #self.statusmsg.set(str(e))

        self.isKeyPressed = True


    # 핫빗 전송 쓰레드
    def sendHeartbit(self):
        heartbits = [chr(x) for x in range(40, 120)]
                    
        try:
            while True:
                tt = time() - self.last_recvmsg_time
                if tt > HEARTBIT_EXPIRED:
                    dispmsg = '핫빗불량! 서버와 연결이 끊어졌습니다[%d]' %tt
                    self.statusmsg.set(dispmsg)
                    self.sock.close()
                    self.hbit.configure(image=self.hbitimg2)
                    self.hbit.image = self.hbitimg2
                    return

                # 핫빗은 랜덤하게 생성하고 랜덤 시간에 전송
                shuffle(heartbits)
                randstr = ''.join(heartbits)
                scope1 = randrange(1, max(2,len(randstr)-1))
                scope2 = randrange(1, max(2,scope1))

                if scope1 == scope2:
                    scope1 += 1
                
                msg = randstr[:scope2] + '$%#' + randstr[scope2:scope1]
                #print(msg)
                msg = aes1.enc(msg.encode())

                try:
                    with lock:
                        self.sock.send(msg)
                except Exception as e:
                    self.statusmsg2.set('소켓오류! 서버와 연결이 끊어졌습니다.')
                    self.hbit.configure(image=self.hbitimg2)
                    self.hbit.image = self.hbitimg2
                    return
                
                timer = randrange(1, 20)                                
                sleep(timer)
        except Exception as e:            
            #self.statusmsg.set(str(e))
            return

    # 멤버 리스트 창을 갱신
    def updateMember(self, memberlist):
        self.memberwin.delete(0, END)
        
        for member in memberlist:
            self.memberwin.insert(END, member)

        if self.yourname:
            if self.yourname not in memberlist:
                self.statusmsg0.set('1:1 은밀히 대화하기-대화상대를 클릭한 후 메시지를 입력하세요')
                self.textinwin0.config(state=DISABLED)
                

    # 메신저 실행 함수
    def run(self):
        self.connect()        
        self.root.mainloop()
        self.sock.close()
        

    # 메신저 종료시 호출되는 함수
    def bye(self):        
        try:
            msg = aes1.enc('/quit'.encode())
            self.sock.send(msg)            
        except:
            pass

    # 메신저 윈도우 디스트로이
    def destroyWin(self):
        global END_PROG
        
        self.bye()
        self.root.destroy()
        END_PROG = True
        

    # 타이틀바 번쩍이게 하는 함수
    def flashTitlebar(self, flag):        
        id = win32gui.FindWindow(None, self.title)
        win32gui.FlashWindow(id, flag)

    # Tkinter TextBox에 텍스트를 형식화해서 표시하는 함수
    def colorText(self, tag, msg, font=('맑은 고딕', 9), fg_color='gray', bg_color='white', justification='left'):
        self.textoutwin.insert(END, msg)
        end_index = self.textoutwin.index(END)
        begin_index = "%s-%sc" % (end_index, len(msg) + 1)        
        self.textoutwin.tag_add(tag, begin_index, end_index)
        self.textoutwin.tag_config(tag, font=font, foreground=fg_color, background=bg_color, justify=justification)
        
    
    # 애니메이션 GIF로 만들어진 이모티콘을 TextBox에서 재생하는 함수
    def animateGif(self, gifname):
        anigif = AnimatedGif(gifname)
        label = Label(self.textoutwin)
        label.configure(image=anigif[0], bg='white')
        label.image = anigif[0]
        
        self.textoutwin.window_create(END, window=label)        
        self.textoutwin.config(state='normal')
        self.textoutwin.insert(END, '\n\n')
        self.textoutwin.see(END)
        self.textoutwin.config(state='disabled')        
        label.after(anigif[0].delay, self.playGif, label, anigif, 0, 0)

    # 3번 반복 재생한 후 GIF의 첫 프레임을 노출
    def playGif(self, label, anigif, frame_num, count):
        frame = anigif[frame_num]
        label.configure(image=frame, bg='white')
        label.image = frame

        frame_num = (frame_num+1) % len(anigif) # 다음 프레임 넘버

        if frame_num == 1:
            count += 1

        if count > 4:
            return
        
        label.after(frame.delay, self.playGif, label, anigif, frame_num, count)
    

    # ------------------------ 위 로직으로 교체
    """def animateGif(self, gifname):
        img = PhotoImage(file=gifname)
        delay = 150
        label = Label(self.textoutwin)
        label.configure(image=img, bg='white')
        label.image = img
        
        self.textoutwin.window_create(END, window=label)
        self.textoutwin.config(state='normal')
        self.textoutwin.insert(END, '\n\n')
        self.textoutwin.see(END)
        self.textoutwin.config(state='disabled')
        label.frame = 0
        label.after(delay, self.playGif, label, delay, 0)

    # 3번 반복 재생한 후 GIF의 첫 프레임을 노출
    def playGif(self, label, delay, count):
        try:
            opt = 'GIF -index {}'.format(label.frame)
            label.image.configure(format=opt)
        except:
            label.frame = 0
            count += 1
            self.playGif(label, delay, count)
            return

        if count > 3:
            return

        label.frame += 1
        label.after(delay, self.playGif, label, delay, count)"""
    
        
if __name__ == '__main__':    
    obj = ChatClient(chatserverip, portnum)

    try:        
        obj.run()
    except:
        pass
