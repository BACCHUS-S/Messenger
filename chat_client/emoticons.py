import tkinter as tk
import os
from PIL import ImageTk, Image
import wcktooltips

class EmoticonBox(tk.Frame):
    def __init__(self, parent, folder):
        tk.Frame.__init__(self, parent)        
        
        self.parent = parent
        self.emoticons = []
        self.remoticons = []
        self.emoticonfiles = []
        self.tooltipsText = []
        self.ret = ''

        midimg_folder = folder + '/medium/'
        largeimg_folder = folder + '/large/'
        
        #emoticonlist = os.listdir('emoti/medium')
        emoticonlist = os.listdir(midimg_folder)

        for emoticon in emoticonlist:
            self.tooltipsText.append(emoticon.split('.')[0])
            #emoticon = 'emoti/medium/' + emoticon
            emoticon = midimg_folder + emoticon            
            imgbton = ImageTk.PhotoImage(Image.open(emoticon))            
            self.emoticons.append(imgbton)            

        #emoticonlist = os.listdir('emoti/large')
        emoticonlist = os.listdir(largeimg_folder)

        for emoticon in emoticonlist:            
            #emoticon = 'emoti/large/' + emoticon            
            emoticon = largeimg_folder + emoticon
            #print(emoticon)
            emotiimg = ImageTk.PhotoImage(Image.open(emoticon))                        
            self.remoticons.append(emotiimg)
            self.emoticonfiles.append(emoticon)

        #for img in self.emoticons:
            #print(img)
                    
        self.initialize()
    

    def initialize(self):
        self.parent.title('이모티콘 고르기')
        self.parent.grid_rowconfigure(1, weight=1)
        self.parent.grid_columnconfigure(1, weight=1)

        self.frame = tk.Frame(self.parent)
        self.frame.pack(fill=tk.X, padx=5, pady=5)

    def showEmoticons(self, gui):       
        self.gui = gui
        a, r = divmod(len(self.emoticons), 10)

        #print('몫: %d 나머지 %d' %(a, r))

        self.buttons = {}
        index = 0        
        for i in range(a):
            for j in range(10):
                b = tk.Button(self.frame, image=self.emoticons[index])
                self.buttons[b] = index
                b.image = self.emoticons[index]
                b.grid(row=i, column=j)
                b.bind('<Button-1>', self.buttonClick)                
                wcktooltips.register(b, self.tooltipsText[index])
                index += 1

        for j in range(r):           
            b = tk.Button(self.frame, image=self.emoticons[index])
            self.buttons[b] = index
            b.image = self.emoticons[index]
            b.grid(row=a+1, column=j)
            b.bind('<Button-1>', self.buttonClick)
            wcktooltips.register(b, self.tooltipsText[index])
            index += 1

        return

    def buttonClick(self, event):
        index = self.buttons[event.widget]
        msg = '/emoticon;' + self.emoticonfiles[index] + ';' + self.gui.me        
        self.gui.sendEmoticon(msg)
        self.parent.destroy()

if __name__ == '__main__':
    #obj = EmoticonBox(tk.Tk(), 'emoti/gif1')
    obj = EmoticonBox(tk.Tk(), 'emoti/katok')
    obj.showEmoticons(None)
    #obj.mainloop()
