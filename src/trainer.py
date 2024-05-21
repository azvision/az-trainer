import ast
import pathlib
from tkinter import END, LEFT, N, RIGHT, S, W, E, StringVar, Tk
from tkinter import filedialog, Button, Canvas, Entry, Frame, Label, Listbox
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import os
import glob
from ultralytics import YOLO

# colors for the bboxes
COLORS = ['red', 'pink', 'blue', 'green', 'black', 'cyan']
# COLORS = ['darkred', 'maroon', 'darkblue', 'darkgreen', 'black', 'cyan']
# image sizes for the examples
SIZE = 256, 256
ZOOM_RATIO = 2


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.rootPanel = master
        self.rootPanel.title("AZ Vision - Trainer")
        self.rootPanel.resizable(width=False, height=False)

        # initialize global state
        self.imageDir = ''
        self.imageList = []
        self.cur = 0
        self.total = 0
        self.imageName = ''
        self.labelFileName = ''
        self.tkimg = None
        self.currentLabelClass = ''
        self.classesList = []
        self.classCandidateFilename = 'src/class.txt'
        self.annotations_batch = "batch-002"
        self.fileNameExt = "jpg"

        self.images_path = os.path.join('C:\\', 'azvision', 'batches')
        self.this_repo = str(pathlib.Path(__file__).parent.resolve().parent)
        self.default_images_filepath = os.path.join(self.images_path,
                                                    self.annotations_batch)

        # initialize mouse state
        self.STATE = {}

        # reference to bbox
        self.bboxIdList = []
        self.curBBoxId = None
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------

        # Empty label
        self.lblAlign = Label(self.rootPanel, text='  \n  ')
        self.lblAlign.grid(column=0, row=0, rowspan=100, sticky=W)

        # Top panel stuff
        self.ctrTopPanel = Frame(self.rootPanel)
        self.ctrTopPanel.grid(row=0, column=1, sticky=W+N)
        Button(self.ctrTopPanel, text="Image input folder", command=self.selectSrcDir).grid(row=0, column=0)

        # input image dir entry
        self.svSourcePath = StringVar()
        Entry(self.ctrTopPanel, textvariable=self.svSourcePath, width=70).grid(row=0, column=1, sticky=W+E, padx=5)
        self.svSourcePath.set(self.default_images_filepath)

        # Button load dir
        self.bLoad = Button(self.ctrTopPanel, text="Load Dir", command=self.loadDir)
        self.bLoad.grid(row=0, column=3, rowspan=1, padx=2, pady=2, ipadx=5, ipady=5)
        self.lblFilename = Label(self.ctrTopPanel, text="Current filename: <name>", justify=LEFT, anchor="w")
        self.lblFilename.grid(row=1, column=0, columnspan=2, sticky=W)

        # main panel for labeling
        self.mainPanel = Canvas(self.rootPanel, cursor='tcross')
        self.mainPanel.grid(row=1, column=1, sticky=W+N)
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)

        self.rootPanel.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.rootPanel.bind("c", self.cancelBBox)
        self.rootPanel.bind("a", self.prevImage)  # press 'a' to go backward
        self.rootPanel.bind("d", self.nextImage)  # press 'd' to go forward
        self.rootPanel.bind("z", self.delBBox)  # press 'z' to delete selected
        self.rootPanel.bind("x", self.clearBBox)  # press 'x' to clear all

        # Class panel
        self.ctrClassPanel = Frame(self.rootPanel)
        self.ctrClassPanel.grid(row=1, column=2, sticky=W+N)

        Label(self.ctrClassPanel, text='Classes:').grid(row=1, column=0, sticky=W)
        self.className = StringVar()
        self.classCandidate = ttk.Combobox(self.ctrClassPanel, state='readonly', textvariable=self.className)
        self.classCandidate.grid(row=2, column=0, sticky=W)
        if os.path.exists(self.classCandidateFilename):
            with open(self.classCandidateFilename) as cf:
                for line in cf.readlines():
                    self.classesList.append(line.strip('\n'))
        self.classCandidate['values'] = self.classesList
        self.classCandidate.current(0)
        self.currentLabelClass = self.classCandidate.get()

        # showing bbox info & delete bbox
        Label(self.ctrClassPanel, text='Annotations:').grid(row=3, column=0, sticky=W+N)
        Button(self.ctrClassPanel, text='Delete Selected (z)', command=self.delBBox).grid(row=4, column=0, sticky=W+E+N)
        Button(self.ctrClassPanel, text='Clear All (x)', command=self.clearBBox).grid(row=4, column=1, sticky=W+E+S)
        self.annotationsList = Listbox(self.ctrClassPanel, width=60, height=12, selectmode="SINGLE")
        self.annotationsList.grid(row=5, column=0, columnspan=2, sticky=N+S+W)
        self.annotationsList.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.annotationsList.bind("1", self.setClass)  # press to select class
        self.annotationsList.bind("2", self.setClass)  # press to select class
        self.annotationsList.bind("3", self.setClass)  # press to select class
        self.annotationsList.bind("4", self.setClass)  # press to select class
        self.annotationsList.bind("5", self.setClass)  # press to select class
        self.annotationsList.bind("6", self.setClass)  # press to select class
        self.annotationsList.bind("7", self.setClass)  # press to select class
        self.annotationsList.bind("8", self.setClass)  # press to select class
        self.annotationsList.bind("9", self.setClass)  # press to select class

        # control panel GoTo

        Label(self.ctrClassPanel, text='  \n  ').grid(row=7, column=0, columnspan=2)

        self.ctrGoToPanel = Frame(self.ctrClassPanel)
        self.ctrGoToPanel.grid(row=8, column=0, columnspan=2, sticky=W+E)
        self.tmpLabel = Label(self.ctrGoToPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrGoToPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrGoToPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        Label(self.ctrClassPanel, text='  \n  ').grid(row=9, column=0, columnspan=2)

        # Navigation control panel
        self.ctrNavigatePanel = Frame(self.ctrClassPanel)
        self.ctrNavigatePanel.grid(row=10, column=0, columnspan=2, sticky=W+E)
        self.prevBtn = Button(self.ctrNavigatePanel, text='<< Prev (a)', width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrNavigatePanel, text='(d) Next >>', width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrNavigatePanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)

        # display mouse position
        self.disp = Label(self.ctrNavigatePanel, text='')
        self.disp.pack(side=RIGHT)
        self.rootPanel.columnconfigure(5, weight=1)
        self.rootPanel.rowconfigure(6, weight=1)

    def selectSrcDir(self):
        path = filedialog.askdirectory(title="Select image source folder", initialdir=self.svSourcePath.get())
        self.svSourcePath.set(path)
        return

    def loadDir(self):
        self.rootPanel.focus()

        self.imageDir = self.svSourcePath.get()
        if not os.path.isdir(self.imageDir):
            messagebox.showerror("Error!", message="The specified dir doesn't exist!")
            return

        self.labelsDir = os.path.join(self.imageDir, 'labels')
        if not os.path.isdir(self.labelsDir):
            os.makedirs(self.labelsDir, exist_ok=True)

        filelist = glob.glob(os.path.join(self.imageDir, "*." + self.fileNameExt))
        filelist = [f.split("\\")[-1] for f in filelist]  # in form of filename
        filelist = [os.path.splitext(f)[0] for f in filelist]  # remove extension
        self.imageList = [] # resets the list because the program.
                            # gets in a loop after loading a new directory (after one has already been loaded).
        self.imageList.extend(filelist)

        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # Load a model
        self.model = YOLO(os.path.join(self.this_repo, "models", "best.pt"))

        self.loadImage()

    def loadImage(self):
        self.tkimg = [0, 0, 0]
        # load image
        self.imgRootName = self.imageList[self.cur - 1]
        imgFilePath = os.path.join(self.imageDir, self.imgRootName + "." + self.fileNameExt)
        self.tkimg = self.loadImgFromDisk(imgFilePath)
        img_width = max(self.tkimg.width()*ZOOM_RATIO, 10)
        img_height = max(self.tkimg.height()*ZOOM_RATIO, 10)
        self.tkimg = self.tkimg._PhotoImage__photo.zoom(ZOOM_RATIO)
        self.mainPanel.config(width=img_width, height=img_height)
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=N+W)

        self.progLabel.config(text=f"{self.cur}/{self.total}")
        self.lblFilename.config(text=f"Filename: {self.imgRootName}")

        self.clearBBox()

        # load labels
        xyxyList = self.getBoxesFromFile()
        if xyxyList is None:
            xyxyList = self.getPredictionsFromYolo()

        for x1, y1, x2, y2, classIndex in xyxyList:
            box_string = self.get_bbox_string(x1, y1, x2, y2, classIndex)
            self.annotationsList.insert(END, box_string)
            self.annotationsList.itemconfig(END, {'fg': COLORS[classIndex]})

    def get_bbox_string(self, x1, y1, x2, y2, classIndex):
        bboxId = self.createBBox(x1, y1, x2, y2, COLORS[classIndex])
        box_string = f"{{'class':'{self.classesList[classIndex]}', 'x1':{x1}, 'y1':{y1}, 'x2': {x2}, 'y2': {y2}, 'id':{bboxId}  }}"
        return box_string

    def getBoxesFromFile(self):
        annotationFilePath, imgWidth, imgHeight = self.get_annotations_metadata()
        results = []
        if os.path.exists(annotationFilePath):
            with open(annotationFilePath) as f:
                for i, line in enumerate(f):
                    tmp = line.split()
                    classIndex = int(tmp[0])
                    cx = int(float(tmp[1])*imgWidth)
                    cy = int(float(tmp[2])*imgHeight)
                    hw = int(float(tmp[3])*imgWidth/2)
                    hh = int(float(tmp[4])*imgHeight/2)
                    x1 = cx - hw
                    y1 = cy - hh
                    x2 = cx + hw
                    y2 = cy + hh
                    results.append((x1, y1, x2, y2, classIndex))
        else:
            return None
        return results

    def getPredictionsFromYolo(self):
        rgbImgFilePath = os.path.join(self.imageDir, self.imgRootName + "." + self.fileNameExt)
        predictions = self.model(rgbImgFilePath)  # predict on an image
        results = []
        for result in predictions:
            # probs = result.probs  # Probs object for classification outputs
            for box in result.boxes:
                classIndex = int(box.cls.item())
                for x1, y1, x2, y2 in box.xyxy:
                    results.append((int(x1)*ZOOM_RATIO, int(y1)*ZOOM_RATIO, int(x2)*ZOOM_RATIO, int(y2)*ZOOM_RATIO, classIndex))
        return results

    def loadImgFromDisk(self, fullFilePath):
        loaded_img = Image.open(fullFilePath)
        size = loaded_img.size
        img_factor = max(size[0]/1000, size[1]/1000., 1.)
        loaded_img = loaded_img.resize((int(size[0]/img_factor), int(size[1]/img_factor)))
        return ImageTk.PhotoImage(loaded_img)

    def saveImage(self):
        if self.imgRootName == '':
            return

        annotationFilePath, imgWidth, imgHeight = self.get_annotations_metadata()
        annotations = self.annotationsList.get(0, END)

        with open(annotationFilePath, 'w') as f:
            for annotationListItem in annotations:
                annotation = ast.literal_eval(annotationListItem)
                class_ = self.classesList.index(annotation['class'])
                centerX = (annotation['x1'] + annotation['x2']) / 2. / imgWidth
                centerY = (annotation['y1'] + annotation['y2']) / 2. / imgHeight
                height = abs(annotation['x1'] - annotation['x2']) * 1. / imgWidth
                width = abs(annotation['y1'] - annotation['y2']) * 1. / imgHeight

                f.write(f'{class_} {centerX} {centerY} {height} {width}\n')

    def get_annotations_metadata(self):
        annotationFileName = self.imgRootName
        annotationFilePath = os.path.join(self.labelsDir, annotationFileName + ".txt")
        imgWidth, imgHeight = self.tkimg.width(), self.tkimg.height()
        return annotationFilePath, imgWidth, imgHeight

    def mouseClick(self, event):
        if self.STATE == {}:
            self.STATE['class'], self.STATE['x1'], self.STATE['y1'] = self.currentLabelClass, event.x, event.y
        else:
            self.STATE['x2'], self.STATE['y2'], self.STATE['selected'] = event.x, event.y, True
            bboxId = self.createBBox(self.STATE['x1'], self.STATE['y1'], self.STATE['x2'], self.STATE['y2'], selected=self.STATE['selected'])
            self.STATE['id'] = bboxId
            self.annotationsList.insert(END, self.STATE)
            self.STATE = {}

    def createBBox(self, x1, y1, x2, y2, color=COLORS[0], selected=False):
        rectangle_width = 2 if selected else 1
        bboxId = self.mainPanel.create_rectangle(x1, y1, x2, y2, width=rectangle_width, outline=color)
        return bboxId

    def mouseMove(self, event):
        self.disp.config(text=f'x: {event.x}, y: {event.y}')
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width=2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width=2)
        if self.STATE != {}:
            if self.curBBoxId:
                self.mainPanel.delete(self.curBBoxId)
            self.curBBoxId = self.mainPanel.create_rectangle(self.STATE['x1'], self.STATE['y1'],
                                                             event.x, event.y,
                                                             width=2, outline=COLORS[0])

    def cancelBBox(self, event):
        if self.curBBoxId:
            self.mainPanel.delete(self.curBBoxId)
        self.STATE = {}

    def delBBox(self, event=None):
        idx = 0
        for item in self.annotationsList.get(0, END):
            bbox = ast.literal_eval(item)
            is_selected = bbox.get('selected', False)
            if is_selected:
                self.mainPanel.delete(bbox['id'])
                self.annotationsList.delete(idx)
            idx += 1
        self.render_boxes()

    def clearBBox(self, event=None):
        num_elements = len(self.annotationsList.get(0, END))
        self.annotationsList.delete(0, num_elements-1)
        self.render_boxes()

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    def setClass(self, e):
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=N+W)
        idx = 0
        for item in self.annotationsList.get(0, END):
            bbox = ast.literal_eval(item)
            is_selected = bbox.get('selected', False)
            if is_selected:
                try:
                    target_class_index = int(e.keysym)-1
                    target_class = self.classesList[target_class_index]
                except (IndexError, ValueError) as e:
                    print("Error:", e)
                    return
                bbox_id = bbox.get('id', 0)
                if bbox_id > 0:
                    bbox['class'] = target_class
                    self.annotationsList.delete(idx)
                    self.annotationsList.insert(idx, bbox)
                    self.annotationsList.itemconfig(idx, {'fg': COLORS[target_class_index]})

            idx += 1
        self.render_boxes()

    def on_listbox_select(self, event):
        selected_indices = event.widget.curselection()

        if selected_indices:

            # Get the selected item's index
            idx = selected_indices[0]

            # Retrieve the current string value from the selected item
            selected_str = event.widget.get(idx)

            try:
                # Safely evaluate the string as a Python literal expression
                selected_dict = ast.literal_eval(selected_str)
                selected_class = self.get_index_of_class(selected_dict['class'])

                # Update the dictionary to include "selected": true
                selected_dict["selected"] = True

                # Convert the updated dictionary back to a string
                updated_str = str(selected_dict)

                # Set the updated string as the value of the selected item
                event.widget.delete(idx)
                event.widget.insert(idx, updated_str)
                event.widget.itemconfig(idx, {'fg': COLORS[selected_class]})

                # For other items, remove the "selected" attribute
                for i in range(event.widget.size()):
                    if i != idx:
                        other_str = event.widget.get(i)
                        other_dict = ast.literal_eval(other_str)
                        other_class = self.get_index_of_class(other_dict['class'])

                        if "selected" in other_dict:
                            del other_dict["selected"]
                        updated_other_str = str(other_dict)
                        event.widget.delete(i)
                        event.widget.insert(i, updated_other_str)
                        event.widget.itemconfig(i, {'fg': COLORS[other_class]})
                self.render_boxes()
            except (ValueError, SyntaxError) as e:
                print("Error:", e)

    def render_boxes(self):
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=N+W)
        for item in self.annotationsList.get(0, END):
            bbox = ast.literal_eval(item)
            self.mainPanel.delete(bbox['id'])
            current_class = self.get_index_of_class(bbox['class'])
            self.createBBox(bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2'], color=COLORS[current_class], selected=bbox.get('selected', False))

    def get_index_of_class(self, search_string):
        try:
            index = self.classesList.index(search_string)
            return index
        except ValueError:
            return -1  # Return -1 if the string is not found in the list


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()
