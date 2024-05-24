import ast
import pathlib
import shutil
import zipfile
from tkinter import END, LEFT, N, S, W, E, StringVar, Tk
from tkinter import filedialog, Button, Canvas, Entry, Frame, Label, Listbox
from tkinter import messagebox
from tkinter import ttk

import yaml
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


class LabelTool:
    def __init__(self, master):
        # set up the main frame
        self.rootPanel = master
        self.rootPanel.title("AZ Vision - Trainer")
        self.rootPanel.resizable(width=False, height=False)

        # initialize global state
        self.baseDir = os.path.dirname(os.path.dirname(__file__))
        self.configFile = os.path.join(self.baseDir, 'config', 'config.yml')
        if os.path.exists(self.configFile):
            with open(self.configFile, 'r') as file:
                config = yaml.safe_load(file)
                self.nextBboxAfterClass = config['next_box_after_class_set']
                file.close()
        else:
            self.nextBboxAfterClass = True

        self.model = None
        self.imageDir = ''
        self.imageList = []
        self.cur = 0
        self.total = 0
        self.imgRootName = None
        self.imageName = ''
        self.labelsDir = None
        self.labelFileName = ''
        self.tkimg = None
        self.currentLabelClass = ''
        self.classesList = []

        self.classCandidateFile = os.path.join(self.baseDir, 'data', 'classes.txt')
        self.annotations_batch = "batch-003"
        self.fileNameExt = "jpg"
        self.selectedBbox = 0

        self.imgPath = os.path.join('C:\\', 'azvision', 'batches')
        self.checkedBatchesPath = os.path.join('C:\\', 'azvision', 'checked-batches')
        self.this_repo = str(pathlib.Path(__file__).parent.resolve().parent)
        self.default_images_filepath = os.path.join(self.imgPath, self.annotations_batch)

        # initialize mouse state
        self.STATE = {}

        # reference to bbox
        self.bboxIdList = []
        self.curBBoxId = None
        self.horizontalLine = None
        self.verticalLine = None

        # ----------------- GUI stuff ---------------------

        # Top panel stuff
        self.ctrTopPanel = Frame(self.rootPanel)
        self.ctrTopPanel.grid(row=0, column=0, sticky=W + N, padx=5)

        # file
        file_frame = Frame(self.ctrTopPanel)
        file_frame.grid(row=0, column=0, ipady=5, sticky=W + N)

        # file image dir entry
        Button(file_frame, text="Img folder", command=self.select_src_dir).pack(side=LEFT)
        self.svSourcePath = StringVar()
        Entry(file_frame, textvariable=self.svSourcePath, width=70).pack(side=LEFT, padx=5)
        self.svSourcePath.set(self.default_images_filepath)

        # button load dir
        self.bLoad = Button(file_frame, text="Load Dir", command=self.load_dir)
        self.bLoad.pack(side=LEFT, padx=5)

        # export batch
        self.bExport = Button(file_frame, text="Export batch", command=self.export_batch)
        self.bExport.pack(side=LEFT, padx=5)

        # image info
        image_frame = Frame(self.ctrTopPanel)
        image_frame.grid(row=1, column=0, sticky=W)

        # current file info
        self.lblFilename = Label(image_frame, text="Filename")
        self.lblFilename.grid(row=0, column=0, sticky=W + N)

        # main panel for labeling
        self.mainPanel = Canvas(image_frame, cursor='tcross')
        self.mainPanel.grid(row=1, column=0, sticky=W + N)
        self.mainPanel.bind("<Button-1>", self.mouse_click)
        self.mainPanel.bind("<Motion>", self.mouse_move)

        self.rootPanel.bind("<Escape>", self.cancel_bbox)  # press Escape to cancel current bbox
        self.rootPanel.bind("c", self.cancel_bbox)
        self.rootPanel.bind("a", self.prev_image)  # press 'a' to go backward
        self.rootPanel.bind("<Left>", self.prev_image)  # press '<-' to go backward
        self.rootPanel.bind("d", self.next_image)  # press 'd' to go forward
        self.rootPanel.bind("<Right>", self.next_image)  # press '->' to go forward
        self.rootPanel.bind("z", self.del_bbox)  # press 'z' to delete selected
        self.rootPanel.bind("x", self.del_all_bboxes)  # press 'x' to delete all

        # Class panel
        self.ctrClassPanel = Frame(self.rootPanel)
        self.ctrClassPanel.grid(row=0, column=1, sticky=N, padx=5)

        Label(self.ctrClassPanel, text='Classes:').grid(row=0, column=0, sticky=W + N)
        self.className = StringVar()
        self.classCandidate = ttk.Combobox(self.ctrClassPanel, state='readonly', textvariable=self.className)
        self.classCandidate.grid(row=1, column=0, sticky=W + N)
        if os.path.exists(self.classCandidateFile):
            with open(self.classCandidateFile) as cf:
                for line in cf.readlines():
                    self.classesList.append(line.strip('\n'))

        numbered_classes_list = self.classesList.copy()
        for class_id in range(len(numbered_classes_list)):
            numbered_classes_list[class_id] = numbered_classes_list[class_id] + ' (' + str(class_id + 1) + ')'

        self.classCandidate['values'] = numbered_classes_list
        self.classCandidate.current(0)
        self.class_on_create()
        self.classCandidate.bind("<<ComboboxSelected>>", self.class_on_create)

        next_bbox_frame = Frame(self.ctrClassPanel)
        next_bbox_frame.grid(row=2, column=0, sticky=W + N)
        next_bbox_label = Label(next_bbox_frame, text='Next box on set:')
        next_bbox_label.pack(side=LEFT)
        next_bbox_text = 'ON' if self.nextBboxAfterClass else 'OFF'
        self.bNextBboxAfterClass = Button(next_bbox_frame, text=next_bbox_text, command=self.toggle_next_bbox_after_class)
        self.bNextBboxAfterClass.pack(side=LEFT)

        # showing bbox info & delete bbox
        Label(self.ctrClassPanel, text='Annotations:').grid(row=4, column=0, sticky=W + N)
        Button(self.ctrClassPanel, text='Delete Selected (z)', command=self.del_bbox).grid(row=5, column=0, sticky=W + N + S)
        Button(self.ctrClassPanel, text='Delete All (x)', command=self.del_all_bboxes).grid(row=6, column=0, sticky=W + N + S)
        self.annotationsList = Listbox(self.ctrClassPanel, width=70, height=12, selectmode="SINGLE", activestyle="none")
        self.annotationsList.grid(row=7, column=0, columnspan=2, sticky=N + S + W)
        self.annotationsList.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.annotationsList.bind("<Up>", self.arrow_up)
        self.annotationsList.bind("<Down>", self.arrow_down)
        self.annotationsList.bind("1", self.set_class)  # press to select class
        self.annotationsList.bind("2", self.set_class)  # press to select class
        self.annotationsList.bind("3", self.set_class)  # press to select class
        self.annotationsList.bind("4", self.set_class)  # press to select class
        self.annotationsList.bind("5", self.set_class)  # press to select class
        self.annotationsList.bind("6", self.set_class)  # press to select class
        self.annotationsList.bind("7", self.set_class)  # press to select class
        self.annotationsList.bind("8", self.set_class)  # press to select class
        self.annotationsList.bind("9", self.set_class)  # press to select class
        self.annotationsList.focus_set()

        master.unbind_all("<Tab>")  # removing default Tab behavior
        master.unbind_all("<<NextWindow>>")
        master.unbind_all("<<PrevWindow>>")
        self.rootPanel.bind("<Tab>", self.arrow_up)  # press to select next box in the list

        # control panel GoTo

        self.ctrGoToPanel = Frame(self.ctrClassPanel)
        self.ctrGoToPanel.grid(row=10, column=0, columnspan=1, pady=10, sticky=W + E)
        self.tmpLabel = Label(self.ctrGoToPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrGoToPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrGoToPanel, text='Go', command=self.goto_image)
        self.goBtn.pack(side=LEFT)

        # Navigation control panel
        self.ctrNavigatePanel = Frame(self.ctrClassPanel)
        self.ctrNavigatePanel.grid(row=12, column=0, sticky=W + N)
        self.prevBtn = Button(self.ctrNavigatePanel, text='<< Prev (a)', width=10, command=self.prev_image)
        self.prevBtn.pack(padx=5, pady=3)
        self.progLabel = Label(self.ctrNavigatePanel, text="Progress:     /    ")
        self.progLabel.pack(padx=5)
        self.nextBtn = Button(self.ctrNavigatePanel, text='(d) Next >>', width=10, command=self.next_image)
        self.nextBtn.pack(padx=5, pady=3)

        # display mouse position
        self.disp = Label(self.ctrNavigatePanel, text='Mouse location')
        self.disp.pack(pady=3)
        self.rootPanel.columnconfigure(5, weight=1)
        self.rootPanel.rowconfigure(6, weight=1)

    def select_src_dir(self):
        path = filedialog.askdirectory(title="Select image source folder", initialdir=self.svSourcePath.get())
        self.svSourcePath.set(path)

    def load_dir(self):
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
        self.imageList = []  # resets the list because the program gets in a loop after loading a new directory (after one has already been loaded).
        self.imageList.extend(filelist)

        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # Load a model
        self.model = YOLO(os.path.join(self.this_repo, "models", "best.pt"))

        self.load_image()

        self.annotationsList.focus_set()

    def export_batch(self):
        if self.labelsDir is None:
            return

        if not os.path.exists(self.checkedBatchesPath):
            os.makedirs(self.checkedBatchesPath, exist_ok=True)

        with zipfile.ZipFile(self.imageDir + '.zip',  'w') as zip_object:
            for folder_name, sub_folders, file_names in os.walk(self.labelsDir):
                for filename in file_names:
                    zip_object.write(str(os.path.join(folder_name, filename)), os.path.join('labels', filename))

        shutil.move(self.imageDir + '.zip', os.path.join(self.checkedBatchesPath, os.path.basename(self.imageDir) + '.zip'))

        print("Exported currently loaded batch as a zip file.")

        self.annotationsList.focus_set()

    def load_image(self):
        self.selectedBbox = -1
        self.tkimg = [0, 0, 0]

        # load image
        self.imgRootName = self.imageList[self.cur - 1]
        img_file_path = os.path.join(self.imageDir, self.imgRootName + "." + self.fileNameExt)
        self.tkimg = self.load_img_from_disk(img_file_path)
        img_width = max(self.tkimg.width() * ZOOM_RATIO, 10)
        img_height = max(self.tkimg.height() * ZOOM_RATIO, 10)
        self.tkimg = self.tkimg._PhotoImage__photo.zoom(ZOOM_RATIO)
        self.mainPanel.config(width=img_width, height=img_height)
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=N + W)

        self.progLabel.config(text=f"{self.cur}/{self.total}")
        self.lblFilename.config(text=f"Filename: {self.imgRootName}")

        self.del_all_bboxes()

        # load labels
        xyxy_list = self.get_boxes_from_file()
        if xyxy_list is None:
            xyxy_list = self.get_predictions_from_yolo()

        first = True
        for x1, y1, x2, y2, classIndex, selected in xyxy_list:
            box_string = self.get_bbox_string(x1, y1, x2, y2, classIndex, True if first else selected)
            self.annotationsList.insert(END, box_string)
            self.annotationsList.itemconfig(END, {'fg': COLORS[classIndex]})
            if first:
                self.selectedBbox = 0
            first = False

    def get_bbox_string(self, x1, y1, x2, y2, class_index, selected):
        bbox_id = self.create_bbox(x1, y1, x2, y2, COLORS[class_index], selected)
        box_string = f"{{'class': '{self.classesList[class_index]}', 'x1': {x1}, 'y1': {y1}, 'x2': {x2}, 'y2': {y2}, 'id': {bbox_id}, 'selected': {selected}}}"
        return box_string

    def get_boxes_from_file(self):
        annotation_file_path, img_width, img_height = self.get_annotations_metadata()
        results = []
        if os.path.exists(annotation_file_path):
            with open(annotation_file_path) as f:
                for i, line in enumerate(f):
                    tmp = line.split()
                    class_index = int(tmp[0])
                    cx = int(float(tmp[1]) * img_width)
                    cy = int(float(tmp[2]) * img_height)
                    hw = int(float(tmp[3]) * img_width / 2)
                    hh = int(float(tmp[4]) * img_height / 2)
                    x1 = cx - hw
                    y1 = cy - hh
                    x2 = cx + hw
                    y2 = cy + hh
                    results.append((x1, y1, x2, y2, class_index, False))
        else:
            return None

        return results

    def get_predictions_from_yolo(self):
        rgb_img_file_path = os.path.join(self.imageDir, self.imgRootName + "." + self.fileNameExt)
        predictions = self.model(rgb_img_file_path)  # predict on an image
        results = []
        for result in predictions:
            # probs = result.probs  # Probs object for classification outputs
            for box in result.boxes:
                class_index = int(box.cls.item())
                for x1, y1, x2, y2 in box.xyxy:
                    results.append((int(x1) * ZOOM_RATIO, int(y1) * ZOOM_RATIO, int(x2) * ZOOM_RATIO, int(y2) * ZOOM_RATIO, class_index, False))

        return results

    def load_img_from_disk(self, full_file_path):
        loaded_img = Image.open(full_file_path)
        size = loaded_img.size
        img_factor = max(size[0] / 1000, size[1] / 1000., 1.)
        loaded_img = loaded_img.resize((int(size[0] / img_factor), int(size[1] / img_factor)))
        return ImageTk.PhotoImage(loaded_img)

    def save_image(self):
        if self.imgRootName == '':
            return

        annotation_file_path, img_width, img_height = self.get_annotations_metadata()
        annotations = self.annotationsList.get(0, END)
        with open(annotation_file_path, 'w') as file:
            for annotationListItem in annotations:
                annotation = ast.literal_eval(annotationListItem)
                class_ = self.classesList.index(annotation['class'])
                center_x = (annotation['x1'] + annotation['x2']) / 2. / img_width
                center_y = (annotation['y1'] + annotation['y2']) / 2. / img_height
                height = abs(annotation['x1'] - annotation['x2']) * 1. / img_width
                width = abs(annotation['y1'] - annotation['y2']) * 1. / img_height
                file.write(f'{class_} {center_x} {center_y} {height} {width}\n')

    def get_annotations_metadata(self):
        annotation_file_name = self.imgRootName
        annotation_file_path = os.path.join(self.labelsDir, annotation_file_name + ".txt")
        img_width, img_height = self.tkimg.width(), self.tkimg.height()
        return annotation_file_path, img_width, img_height

    def mouse_click(self, event):
        if self.STATE == {}:
            self.STATE['class'], self.STATE['x1'], self.STATE['y1'] = self.currentLabelClass, event.x, event.y
        else:
            self.STATE['x2'], self.STATE['y2'] = event.x, event.y
            bbox_id = self.create_bbox(self.STATE['x1'], self.STATE['y1'], self.STATE['x2'], self.STATE['y2'], COLORS[self.get_index_of_class(self.STATE['class'])], True)
            self.STATE['id'], self.STATE['selected'] = bbox_id, True  # attributes in order

            # For other boxes, set the 'selected' attribute to False
            idx = 0
            for item in self.annotationsList.get(0, END):
                bbox = ast.literal_eval(item)
                bbox['selected'] = False
                self.annotationsList.delete(idx)
                self.annotationsList.insert(0, str(bbox))
                idx += 1

            self.annotationsList.insert(END, str(self.STATE))
            self.STATE = {}

            self.selectedBbox = self.annotationsList.size() - 1
            self.annotationsList.focus_set()

            self.render_boxes()

    def toggle_next_bbox_after_class(self):
        self.nextBboxAfterClass = not self.nextBboxAfterClass
        new_text = "ON" if self.nextBboxAfterClass else "OFF"
        self.bNextBboxAfterClass.config(text=new_text)
        with open(self.configFile, 'w') as file:
            yaml.dump(dict(next_box_after_class_set=self.nextBboxAfterClass), file)

        file.close()

    def create_bbox(self, x1, y1, x2, y2, color=COLORS[0], selected=False):
        rectangle_width = 2 if selected else 1
        bbox_id = self.mainPanel.create_rectangle(x1, y1, x2, y2, width=rectangle_width, outline=color)
        return bbox_id

    def mouse_move(self, event):
        self.disp.config(text=f'x: {event.x}, y: {event.y}')
        if self.tkimg:
            if self.horizontalLine:
                self.mainPanel.delete(self.horizontalLine)
            self.horizontalLine = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width=2)
            if self.verticalLine:
                self.mainPanel.delete(self.verticalLine)
            self.verticalLine = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width=2)

        if self.STATE != {}:
            if self.curBBoxId:
                self.mainPanel.delete(self.curBBoxId)
            self.curBBoxId = self.mainPanel.create_rectangle(self.STATE['x1'], self.STATE['y1'], event.x, event.y, width=2, outline=COLORS[self.get_index_of_class(self.currentLabelClass)])

    def class_on_create(self, event=None):
        index = self.classCandidate.current()
        if index < 0 or index > len(self.classesList):
            return

        self.currentLabelClass = self.classesList[index]

    def cancel_bbox(self, event=None):
        if self.curBBoxId:
            self.mainPanel.delete(self.curBBoxId)
        self.STATE = {}

    def del_bbox(self, event=None):
        idx = 0
        for item in self.annotationsList.get(0, END):
            bbox = ast.literal_eval(item)
            is_selected = bbox.get('selected', False)
            if is_selected:
                self.mainPanel.delete(bbox['id'])
                self.annotationsList.delete(idx)
            idx += 1

        if self.selectedBbox >= self.annotationsList.size():
            self.selectedBbox = 0

        self.on_listbox_select()
        self.render_boxes()

    def del_all_bboxes(self, event=None):
        num_elements = len(self.annotationsList.get(0, END))
        self.annotationsList.delete(0, num_elements - 1)
        self.selectedBbox = 0
        self.render_boxes()

    def prev_image(self, event=None):
        if len(self.imageList) < 1:
            return False

        self.save_image()
        if self.cur > 1:
            self.cur -= 1
            self.load_image()

    def next_image(self, event=None):
        if len(self.imageList) < 1:
            return False

        self.save_image()
        if self.cur < self.total:
            self.cur += 1
            self.load_image()
            self.cancel_bbox()

    def goto_image(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx <= self.total:
            self.save_image()
            self.cur = idx
            self.load_image()

    def set_class(self, key):
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=N + W)
        idx = 0
        for item in self.annotationsList.get(0, END):
            bbox = ast.literal_eval(item)
            if bbox['selected'] is True:
                try:
                    target_class_index = int(key.keysym) - 1
                    target_class = self.classesList[target_class_index]
                except (IndexError, ValueError) as key:
                    print("Error:", key)
                    return
                bbox_id = bbox.get('id', 0)
                if bbox_id > 0:
                    bbox['class'] = target_class
                    self.annotationsList.delete(idx)
                    self.annotationsList.insert(idx, bbox)
                    self.annotationsList.itemconfig(idx, {'fg': COLORS[target_class_index]})
            idx += 1

        if self.nextBboxAfterClass:
            self.arrow_down()

        self.render_boxes()

    def arrow_up(self, event=None):
        self.selectedBbox -= 1
        if self.selectedBbox < 0:
            self.selectedBbox = self.annotationsList.size() - 1
        self.on_listbox_select()

    def arrow_down(self, event=None):
        self.selectedBbox += 1
        if self.selectedBbox >= self.annotationsList.size():
            self.selectedBbox = 0
        self.on_listbox_select()

    def on_listbox_select(self, event=None):
        if self.annotationsList.size() < 1:
            return

        # Get the selected item's index
        selected_indices = self.annotationsList.curselection()  # arrows return empty indices for some reason, even though the item gets underlined which means its active
        if selected_indices:
            idx = self.selectedBbox = selected_indices[0]
        else:
            idx = self.selectedBbox

        # Retrieve the current string value from the selected item
        selected_str = self.annotationsList.get(idx)

        try:
            # Safely evaluate the string as a Python literal expression
            selected_dict = ast.literal_eval(selected_str)
            selected_class = self.get_index_of_class(selected_dict['class'])

            # Update the dictionary to include 'selected': true
            selected_dict['selected'] = True

            # Convert the updated dictionary back to a string
            updated_str = str(selected_dict)

            # Set the updated string as the value of the selected item
            self.annotationsList.delete(idx)
            self.annotationsList.insert(idx, updated_str)
            self.annotationsList.itemconfig(idx, {'fg': COLORS[selected_class]})

            # For other items, set the 'selected' attribute to False
            for i in range(self.annotationsList.size()):
                if i != idx:
                    other_str = self.annotationsList.get(i)
                    other_dict = ast.literal_eval(other_str)
                    other_class = self.get_index_of_class(other_dict['class'])
                    if 'selected' in other_dict:
                        other_dict['selected'] = False

                    self.annotationsList.delete(i)
                    self.annotationsList.insert(i, str(other_dict))
                    self.annotationsList.itemconfig(i, {'fg': COLORS[other_class]})

            self.render_boxes()
        except (ValueError, SyntaxError) as exception:
            print("Error:", exception)

    def render_boxes(self):
        self.mainPanel.create_image(0, 0, image=self.tkimg, anchor=N + W)
        for item in self.annotationsList.get(0, END):
            bbox = ast.literal_eval(item)
            self.mainPanel.delete(bbox['id'])
            current_class = self.get_index_of_class(bbox['class'])
            self.create_bbox(bbox['x1'], bbox['y1'], bbox['x2'], bbox['y2'], color=COLORS[current_class], selected=bbox['selected'])

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
