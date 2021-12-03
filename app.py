import tkinter as tk
import cv2
import json
import pymunk
import math
import random
from enum import Enum
from os import path
from datetime import datetime
import numpy as np
from PIL import Image
from PIL import ImageTk
from tkinter import ttk

# Constants
MIN_RADIUS = 10
MASS = 10
SETUP_ERROR = 70
HEADER_FONT = ("Arial", 16)
PARAGRAPH_FONT = ("Arial", 12)
CAMERA_PORT = 0

cap = cv2.VideoCapture(CAMERA_PORT,  cv2.CAP_DSHOW)
space = pymunk.Space()
frameStack = []

balls = ['Yellow', 'Blue', 'Red', 'Purple', 'Orange', 'Green']
ballColors = [(0, 255, 255), (255, 0, 0), (0, 0, 255),
              (128, 0, 128), (0, 128, 255), (0, 255, 0)]
ballObjects = []


# Create trackbars for HSV colors
def create_trackbars():
    cv2.namedWindow("Trackbars")
    for c in "HSV":
        cv2.createTrackbar("{}_MIN".format(
            c), "Trackbars", 0, 255, lambda x: x)
        cv2.createTrackbar("{}_MAX".format(
            c), "Trackbars", 255, 255, lambda x: x)


# Create data file with ball HSV values
def create_data_file():
    with open('data.txt', "w+") as file:
        data = {}
        data['balls'] = []
        for ball in balls:
            data['balls'].append({
                ball: {
                    'hMin': '0',
                    'hMax': '179',
                    'sMin': '0',
                    'sMax': '255',
                    'vMin': '0',
                    'vMax': '255'
                }
            })
        json.dump(data, file)


# Main pool irl app
class PoolIRLApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        # tk.Tk.iconbitmap(self, default="example.ico")
        tk.Tk.wm_title(self, "Pool IRL")
        tk.Tk.protocol(self, "WM_DELETE_WINDOW", self.delete_window)

        if not path.exists('data.txt'):
            create_data_file()

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        menubar = tk.Menu(container)
        filemenu = tk.Menu(menubar, tearoff=0)
        # filemenu.add_command(label="Soundboard",
        #                      command=lambda: self.show_frame(SoundboardPage))
        filemenu.add_command(label="Settings",
                             command=lambda: self.show_frame(SettingsPage))
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.delete_window)
        menubar.add_cascade(label="File", menu=filemenu)

        tk.Tk.config(self, menu=menubar)

        self.frames = {}

        for F in (StartPage, PracticePage, GamePage, SettingsPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)

    def show_frame(self, controller):
        if controller in frameStack:
            frameStack.remove(controller)
        frameStack.insert(0, controller)
        if len(frameStack) >= 2:
            self.frames[frameStack[1]].onFocusOut()
        if len(frameStack) >= 3:
            frameStack.pop()
        frame = self.frames[controller]
        frame.tkraise()
        frame.event_generate("<<ShowFrame>>")

    # Destroy window
    def delete_window(self):
        try:
            # cap.release()
            cv2.destroyAllWindows()
            tk.Tk.destroy(self)
        except:
            print("Error: Could not destroy!")


# Start page frame
class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        style = ttk.Style()
        style.configure("BW.TLabel", foreground="black", font=HEADER_FONT)
        self.image = Image.open(
            "images/background_image.jpeg")
        self.backgroundImage = self.image
        self.backgroundImage = ImageTk.PhotoImage(self.backgroundImage)
        self.backgroundLabel = tk.Label(self, image=self.backgroundImage)
        self.backgroundLabel.place(x=0, y=0, relwidth=1, relheight=1)
        self.backgroundLabel.bind('<Configure>', self.resize)
        headingLabel = ttk.Label(self, text="Pool IRL", style="BW.TLabel")
        headingLabel.pack(pady=10, padx=10)
        practiceButton = ttk.Button(
            self, text="Practice", command=lambda: (controller.show_frame(PracticePage)))
        practiceButton.pack()
        gameButton = ttk.Button(
            self, text="Game", command=lambda: (controller.show_frame(GamePage)))
        gameButton.pack()

    # Resize background image to new width/height
    def resize(self, event):
        self.backgroundImage = self.image.resize(
            (event.width, event.height), Image.ANTIALIAS)
        self.backgroundImage = ImageTk.PhotoImage(self.backgroundImage)
        self.backgroundLabel.configure(image=self.backgroundImage)

    def onFocus(self, event):
        pass

    def onFocusOut(self):
        pass


# Practice page frame
class PracticePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        headingLabel = tk.Label(self, text="Pool IRL - Practice",
                                fg="black", font=HEADER_FONT)
        headingLabel.pack(pady=10, padx=10)
        self.img_canvas = tk.Canvas(self)
        img_scroller = tk.Scrollbar(
            self, orient='vertical', command=self.img_canvas.yview)
        self.img_canvas.configure(scrollregion=self.img_canvas.bbox(
            'all'), yscrollcommand=img_scroller.set)
        self.img_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.img_canvas.pack(fill='both', expand=False, side='right')
        img_scroller.pack(fill='y', side='right')
        self.cam = tk.Label(self)
        self.cam.pack()
        self.job = None
        self.overlay_imgs = []
        self.overlay_times = []
        self.overlay_img = 0
        self.save_img = False
        self.opacitySlider = tk.Scale(
            self, orient='horizontal', from_=0, to=1, resolution=0.05)
        self.opacitySlider.set(0.2)
        self.opacitySlider.pack()
        saveButton = ttk.Button(
            self, text="Save", command=lambda: self.save())
        saveButton.pack()
        backButton = ttk.Button(
            self, text="Back", command=lambda: (controller.show_frame(StartPage)))
        backButton.pack()
        self.bind("<<ShowFrame>>", self.onFocus)

    def show_camera(self):
        ret, frame = cap.read()
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        if (self.save_img):
            self.overlay_imgs.insert(0, cv2image)
            self.overlay_times.insert(0, datetime.now().strftime("%X"))
            for i, img in enumerate(self.overlay_imgs):
                (h, w, c) = img.shape
                r = 150.0 / w
                dim = (150, int(h*r))
                image = cv2.resize(img, dim,
                                   interpolation=cv2.INTER_AREA)
                image = Image.fromarray(image)
                photo = ImageTk.PhotoImage(image=image)
                button = tk.Button(self.img_canvas, bd=1, fg="black",
                                   command=lambda i=i, img=img: self.change_image(i))
                button.image = photo
                label = tk.Label(self.img_canvas, text=self.overlay_times[i])
                button.configure(image=photo)
                self.img_canvas.create_window(
                    0, i*(h/4), anchor='nw', window=button, height=h/4, width=w/4)
                self.img_canvas.create_window(
                    0, i*(h/4), anchor='ne', window=label, height=h/4, width=w/4)
                self.overlay_img = 0
            self.img_canvas.configure(scrollregion=self.img_canvas.bbox(
                'all'))
            self.save_img = False
        if (self.overlay_imgs):
            cv2image = cv2.addWeighted(
                cv2image, 1, self.overlay_imgs[self.overlay_img], self.opacitySlider.get(), 0)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.cam.imgtk = imgtk
        self.cam.configure(image=imgtk)
        self.job = self.cam.after(10, self.show_camera)

    def _on_mousewheel(self, event):
        self.img_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def change_image(self, i):
        self.overlay_img = i

    def save(self):
        self.save_img = True

    def onFocus(self, event):
        self.img_canvas.configure(scrollregion=(0, 0, 0, 0))
        self.show_camera()

    def onFocusOut(self):
        self.img_canvas.delete("all")
        self.overlay_img = 0
        self.overlay_imgs = []
        self.overlay_times = []
        self.cam.after_cancel(self.job)

# Ball class storing a name, physics values, and min/max hsv values
class Ball:
    def __init__(self, name, hMin=0, hMax=179, sMin=0, sMax=255, vMin=0, vMax=255):
        self.name = name
        self.hMin = hMin
        self.hMax = hMax
        self.sMin = sMin
        self.sMax = sMax
        self.vMin = vMin
        self.vMax = vMax
        self.r = 0
        self.x = 0
        self.y = 0
    
    def init(self):
        self.moment = pymunk.moment_for_circle(MASS, 0, self.r)
        self.body = pymunk.Body(MASS, self.moment)
        self.body.position = self.x, self.y
        self.shape = pymunk.Circle(self.body, self.r)
        self.shape.elasticity = 0.7
        self.shape.friction = 0.8
        self.shape.collision_type = 1
        self.piv = pymunk.constraints.PivotJoint(space.static_body, self.body, (0,0), (0,0))
        self.piv.max_force = 1000
        self.piv.max_bias = 0
        self.mot = pymunk.constraints.SimpleMotor(space.static_body, self.body, 0)
        self.mot.max_force = 50000000
        space.add(self.body, self.shape, self.piv, self.mot)

    def setPos(self, x, y, r):
        self.x = x
        self.y = y
        self.r = r
        
class Turn(Enum):
    PLAYER = 1
    COMPUTER = 2
    SETUP = 3

def collide(arbiter, space, data):
    return True

# Walls
shape = pymunk.Segment(space.static_body, (1, 1), (1, cap.get(4)), 1.0)
space.add(shape)
shape.elasticity = 1
shape.friction = 1

shape = pymunk.Segment(space.static_body, (1, 1), (cap.get(3), 1), 1.0)
space.add(shape)
shape.elasticity = 1
shape.friction = 1

shape = pymunk.Segment(space.static_body, (cap.get(3), 1), (cap.get(3), cap.get(4)), 1.0)
space.add(shape)
shape.elasticity = 1
shape.friction = 1

shape = pymunk.Segment(space.static_body, (1, cap.get(4)), (cap.get(3), cap.get(4)), 1.0)
space.add(shape)
shape.elasticity = 1
shape.friction = 1

# Game page frame
class GamePage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        headingLabel = tk.Label(self, text="Pool IRL - Game",
                                fg="black", font=HEADER_FONT)
        headingLabel.pack(pady=10, padx=10)
        self.turn = Turn.PLAYER
        self.cam = tk.Label(self)
        self.cam.pack()
        self.job = None
        self.turnButton = ttk.Button(
            self, text="End turn", command=lambda: (self.endTurn()))
        self.turnButton.pack()
        backButton = ttk.Button(
            self, text="Back", command=lambda: (controller.show_frame(StartPage)))
        backButton.pack()
        self.bind("<<ShowFrame>>", self.onFocus)

    def show_camera(self):
        ret, frame = cap.read()

        if self.turn == Turn.PLAYER:
            for i, ball in enumerate(balls):
                    # Covert BGR to HSV
                    thresh = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                    # Get HSV settings
                    hMin, hMax, sMin, sMax, vMin, vMax = SettingsPage.getHSVSliders(
                        ball)

                    thresh = cv2.inRange(
                        thresh, (hMin, sMin, vMin), (hMax, sMax, vMax))

                    kernel = np.ones((5, 5), np.uint8)
                    mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                    # Get list of possible balls
                    contours = cv2.findContours(
                        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

                    center = None

                    if len(contours) > 0:
                        # Get largest ball
                        largestBall = max(contours, key=cv2.contourArea)
                        (x, y), radius = cv2.minEnclosingCircle(largestBall)
                        M = cv2.moments(largestBall)
                        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

                        # Show ball outline
                        if radius > MIN_RADIUS:
                            ballObjects[balls.index(ball)].setPos(x, y, radius)
                            cv2.circle(frame, center,
                                    int(radius), ballColors[i], 2)
        # Computer turn
        elif self.turn == Turn.COMPUTER:
            stop = True
            for i, ball in enumerate(balls):
                b = ballObjects[balls.index(ball)]
                if b.r < cap.get(4)/2:
                    cv2.circle(frame, (int(b.body.position[0]), int(b.body.position[1])), int(b.r), ballColors[i], 2)
                    if b.body.velocity != (0,0):
                        stop = False
            if stop:
                self.turn = Turn.SETUP
        elif self.turn == Turn.SETUP:
            shapes = np.zeros_like(frame, np.uint8)
            aligned = True
            for i, ball in enumerate(balls):
                # Covert BGR to HSV
                thresh = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # Get HSV settings
                hMin, hMax, sMin, sMax, vMin, vMax = SettingsPage.getHSVSliders(
                    ball)

                thresh = cv2.inRange(
                    thresh, (hMin, sMin, vMin), (hMax, sMax, vMax))

                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                # Get list of possible balls
                contours = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]

                center = None

                b = ballObjects[balls.index(ball)]

                if len(contours) > 0:
                    # Get largest ball
                    largestBall = max(contours, key=cv2.contourArea)
                    (x, y), radius = cv2.minEnclosingCircle(largestBall)
                    M = cv2.moments(largestBall)
                    center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                    
                    # Show ball outline
                    if radius > MIN_RADIUS and b.r < cap.get(4)/2:
                        cv2.line(frame, (int(x),int(y)), (int(b.body.position[0]),int(b.body.position[1])), (0,0,0), 8)
                        print(b.name, math.sqrt(math.pow((x-b.body.position[0]),2) + math.pow((y-b.body.position[1]),2)))
                        if (math.sqrt(math.pow((x-b.body.position[0]),2) + math.pow((y-b.body.position[1]),2))) > SETUP_ERROR:
                            aligned = False
                
                if b.r < cap.get(4)/2:
                    cv2.circle(shapes, (int(b.body.position[0]), int(b.body.position[1])), int(b.r), ballColors[i], cv2.FILLED)
                    frame = cv2.addWeighted(frame, 1, shapes, 0.25, 0)

            if aligned:
                self.turn = Turn.PLAYER
                self.turnButton['state'] = 'enabled'

        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        img = Image.fromarray(cv2image)
        imgtk = ImageTk.PhotoImage(image=img)
        self.cam.imgtk = imgtk
        self.cam.configure(image=imgtk)
        space.step(0.01)

        # Call show_camera after 10 ms
        self.job = self.cam.after(10, self.show_camera)

    def computer(self):
        b = ballObjects[balls.index("Yellow")]
        b.body.apply_impulse_at_world_point((random.randint(5000,10000),random.randint(5000,10000)),(0,0))
    
    def endTurn(self):
        self.turn = Turn.COMPUTER
        self.turnButton['state'] = 'disabled'
        for i, ball in enumerate(balls):
                b = ballObjects[balls.index(ball)]
                if b.r < cap.get(4)/2:
                    b.init()
        handler = space.add_collision_handler(1, 1)
        handler = space.add_collision_handler(1, 2)
        handler.begin = collide
        self.computer()

    def onFocus(self, event):
        # Start showing camera when GamePage is focused
        self.show_camera()

    def onFocusOut(self):
        # Terminate showing camera
        self.cam.after_cancel(self.job)


# Settings page frame
class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.headingLabel = tk.Label(self, text="Pool IRL - Settings",
                                     fg="black", font=HEADER_FONT)
        self.headingLabel.pack(pady=10, padx=10)
        self.initBalls()
        self.job = None
        self.data = None
        self.variable = tk.StringVar(self)
        self.variable.set(balls[0])
        colorMenu = tk.OptionMenu(
            self, self.variable, *balls, command=self.onChange)
        colorMenu.pack()

        hMinLabel = tk.Label(
            self, text="hMin", fg="black", font=PARAGRAPH_FONT)
        hMinLabel.pack()
        self.hMinSlider = tk.Scale(
            self, orient='horizontal', from_=0, to=179)
        self.hMinSlider.pack()

        hMaxLabel = tk.Label(
            self, text="hMax", fg="black", font=PARAGRAPH_FONT)
        hMaxLabel.pack()
        self.hMaxSlider = tk.Scale(
            self, orient='horizontal', from_=0, to=179)
        self.hMaxSlider.pack()

        sMinLabel = tk.Label(
            self, text="sMin", fg="black", font=PARAGRAPH_FONT)
        sMinLabel.pack()
        self.sMinSlider = tk.Scale(
            self, orient='horizontal', from_=0, to=255)
        self.sMinSlider.pack()

        sMaxLabel = tk.Label(
            self, text="sMax", fg="black", font=PARAGRAPH_FONT)
        sMaxLabel.pack()
        self.sMaxSlider = tk.Scale(
            self, orient='horizontal', from_=0, to=255)
        self.sMaxSlider.pack()

        vMinLabel = tk.Label(
            self, text="vMin", fg="black", font=PARAGRAPH_FONT)
        vMinLabel.pack()
        self.vMinSlider = tk.Scale(
            self, orient='horizontal', from_=0, to=255)
        self.vMinSlider.pack()

        vMaxLabel = tk.Label(
            self, text="vMax", fg="black", font=PARAGRAPH_FONT)
        vMaxLabel.pack()
        self.vMaxSlider = tk.Scale(
            self, orient='horizontal', from_=0, to=255)
        self.vMaxSlider.pack()

        saveButton = ttk.Button(
            self, text="Save", command=lambda: self.save())
        saveButton.pack()
        backButton = ttk.Button(
            self, text="Back", command=lambda: (controller.show_frame(frameStack[1])))
        backButton.pack()
        self.bind("<<ShowFrame>>", self.onFocus)

    def initBalls(self):
        for ball in balls:
            b = Ball(ball)
            ballObjects.append(b)
        self.loadBalls()

    @staticmethod
    def getHSVSliders(color):
        values = []
        values.append(ballObjects[balls.index(color)].hMin)
        values.append(ballObjects[balls.index(color)].hMax)
        values.append(ballObjects[balls.index(color)].sMin)
        values.append(ballObjects[balls.index(color)].sMax)
        values.append(ballObjects[balls.index(color)].vMin)
        values.append(ballObjects[balls.index(color)].vMax)
        return values

    def save(self):
        colorIndex = balls.index(self.variable.get())
        ballObjects[colorIndex].hMin = self.hMinSlider.get()
        ballObjects[colorIndex].hMax = self.hMaxSlider.get()
        ballObjects[colorIndex].sMin = self.sMinSlider.get()
        ballObjects[colorIndex].sMax = self.sMaxSlider.get()
        ballObjects[colorIndex].vMin = self.vMinSlider.get()
        ballObjects[colorIndex].vMax = self.vMaxSlider.get()
        self.saveToFile()

    def loadBalls(self):
        with open('data.txt') as file:
            self.data = json.load(file)

            for ballObject in ballObjects:
                ballObject.hMin = int(self.data['balls'][balls.index(
                    ballObject.name)].get(ballObject.name).get('hMin'))
                ballObject.hMax = int(self.data['balls'][balls.index(
                    ballObject.name)].get(ballObject.name).get('hMax'))
                ballObject.sMin = int(self.data['balls'][balls.index(
                    ballObject.name)].get(ballObject.name).get('sMin'))
                ballObject.sMax = int(self.data['balls'][balls.index(
                    ballObject.name)].get(ballObject.name).get('sMax'))
                ballObject.vMin = int(self.data['balls'][balls.index(
                    ballObject.name)].get(ballObject.name).get('vMin'))
                ballObject.vMax = int(self.data['balls'][balls.index(
                    ballObject.name)].get(ballObject.name).get('vMax'))

    def onChange(self, event=None):
        colorIndex = balls.index(self.variable.get())
        self.hMinSlider.set(ballObjects[colorIndex].hMin)
        self.hMaxSlider.set(ballObjects[colorIndex].hMax)
        self.sMinSlider.set(ballObjects[colorIndex].sMin)
        self.sMaxSlider.set(ballObjects[colorIndex].sMax)
        self.vMinSlider.set(ballObjects[colorIndex].vMin)
        self.vMaxSlider.set(ballObjects[colorIndex].vMax)

    def update(self):
        colorIndex = balls.index(self.variable.get())
        ret, frame = cap.read()

        thresh = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        hMin, hMax, sMin, sMax, vMin, vMax = SettingsPage.getHSVSliders(
            balls[colorIndex])

        thresh = cv2.inRange(
            thresh, (hMin, sMin, vMin), (hMax, sMax, vMax))

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Show Thresh and Mask frames
        cv2.imshow("Thresh", thresh)
        cv2.imshow("Mask", mask)

        self.job = self.headingLabel.after(10, self.update)

    # Save ball HSV values to data file
    def saveToFile(self):
        with open('data.txt', "w+") as file:
            data = {}
            data['balls'] = []
            for i, ball in enumerate(balls):
                data['balls'].append({
                    ball: {
                        'hMin': ballObjects[i].hMin,
                        'hMax': ballObjects[i].hMax,
                        'sMin': ballObjects[i].sMin,
                        'sMax': ballObjects[i].sMax,
                        'vMin': ballObjects[i].vMin,
                        'vMax': ballObjects[i].vMax
                    }
                })
            json.dump(data, file)

    def onFocus(self, event):
        self.onChange()
        self.update()

    def onFocusOut(self):
        self.headingLabel.after_cancel(self.job)
        self.saveToFile()
        cv2.destroyAllWindows()


# Start app
app = PoolIRLApp()
app.mainloop()
