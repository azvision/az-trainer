import ast
import pathlib
import re
import threading
from datetime import datetime
from tkinter import END, LEFT, N, S, W, E, StringVar, Tk
from tkinter import Button, Canvas, Entry, Frame, Label, Listbox, Toplevel
from tkinter import messagebox
from tkinter import ttk
from xml.etree import ElementTree

import requests
import yaml
from PIL import Image, ImageTk
import os
import glob

from tqdm import tqdm
from ultralytics import YOLO

# colors for the bboxes
COLORS = ['red', 'pink', 'blue', 'green', 'black', 'cyan']
# COLORS = ['darkred', 'maroon', 'darkblue', 'darkgreen', 'black', 'cyan']
# image sizes for the examples
SIZE = 256, 256
ZOOM_RATIO = 2


def list_folders_in_folder(local_directory):
    if not os.path.exists(local_directory):
        os.mkdir(local_directory)

    if not os.path.isdir(local_directory):
        print(f"Path isn't a directory: {local_directory}")
        return []

    try:
        return [entry for entry in os.listdir(local_directory) if os.path.isdir(os.path.join(local_directory, entry))]
    except Exception as error:
        print(f"An error occurred: {error}")
        return []


def list_folders_in_folder_azure(url, container, code, folder_path):
    if not url:
        print("The url is empty!")
        return []

    if not container:
        print("The container is empty!")
        return []

    if not code:
        print("The code is empty!")
        return []

    if folder_path and not folder_path.endswith('/'):
        folder_path += '/'

    try:
        list_url = f"{url}{container}?restype=container&comp=list&prefix={folder_path}&delimiter=/&{code}"
        response = requests.get(list_url)
        response.raise_for_status()

        folders = []
        for blob_prefix in ElementTree.fromstring(response.content).findall('.//BlobPrefix'):
            name_element = blob_prefix.find('Name')
            if name_element is not None and name_element.text:
                prefix_text = name_element.text
                if prefix_text != folder_path.rstrip('/'):
                    subfolder = prefix_text[len(folder_path):].rstrip('/')
                    if subfolder:
                        folders.append(subfolder)

        return folders
    except Exception as error:
        print(f"An error occurred: {error}")
        return []


def list_blobs_in_folder(url, container, code, folder_path):
    if not url:
        print("The url is empty!")
        return

    if not container:
        print("The container is empty!")
        return

    if not code:
        print("The code is empty!")
        return

    if not folder_path:
        print("The folder path is empty!")
        return

    try:
        url = f"{url}{container}?restype=container&comp=list&prefix={folder_path}&{code}"
        response = requests.get(url)
        response.raise_for_status()
        blobs = [blob.find('Name').text for blob in ElementTree.fromstring(response.content).findall('.//Blob')]
        return blobs
    except Exception as error:
        print(f"An error occurred: {error}")
        return []


def get_blob_properties(blob_url):
    if not blob_url:
        print("The blob url is empty!")
        return

    try:
        response = requests.head(blob_url)
        response.raise_for_status()
        return {'last_modified': datetime.strptime(response.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z')}
    except Exception as error:
        print(f"An error occurred: {error}")
        return {}


def download_blob(blob_url, local_path, tqdm_used=False):
    if tqdm_used:
        print("\n")

    if not blob_url:
        print("The blob url is empty!")
        return

    if os.path.exists(local_path):
        blob_last_modified = get_blob_properties(blob_url).get('last_modified')
        if blob_last_modified and blob_last_modified <= datetime.fromtimestamp(os.path.getmtime(local_path)):
            print(f"Local file is up to date: {local_path}")
            return

    try:
        response = requests.get(blob_url, stream=True)
        response.raise_for_status()
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print(f"Blob downloaded successfully and saved as {local_path}")
    except Exception as error:
        print(f"An error occurred: {error}")


def download_folder(url, container, code, folder, local_directory):
    if not url:
        print("The url is empty!")
        return

    if not container:
        print("The container is empty!")
        return

    if not code:
        print("The code is empty!")
        return

    if not os.path.exists(local_directory):
        os.mkdir(local_directory)

    if not os.path.isdir(local_directory):
        print(f"Path isn't a directory: {local_directory}")
        return []

    print(f"Downloading folder: {folder}")

    for blob in tqdm(list_blobs_in_folder(url, container, code, folder), desc="Downloading files"):
        local_path = os.path.join(local_directory, blob).replace('\\', '/')
        blob_url = f"{url}{container}/{blob}?{code}"
        download_blob(blob_url, local_path, True)


def upload_file(file_path, url, container, code, blob_name, tqdm_used=False):
    if tqdm_used:
        print("\n")

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    if not url:
        print("The url is empty!")
        return

    if not container:
        print("The container is empty!")
        return

    if not code:
        print("The code is empty!")
        return

    if not blob_name:
        print("The blob name is empty!")
        return

    blob_url = f"{url}{container}/{blob_name}?{code}"
    try:
        with open(file_path, 'rb') as file_data:
            file_content = file_data.read()
            headers = {
                'x-ms-blob-type': 'BlockBlob',
                'Content-Length': str(len(file_content)),
            }

            response = requests.put(blob_url, data=file_content, headers=headers)
            response.raise_for_status()

            print(f"Uploaded file: {file_path}")
    except Exception as error:
        print(f"An error occurred: {error}")


def upload_folder(local_folder, url, container, code, folder):
    if not local_folder or not os.path.isdir(local_folder):
        print("The directory doesn't exist or is empty!")
        return

    if not url:
        print("The url is empty!")
        return

    if not container:
        print("The container is empty!")
        return

    if not code:
        print("The code is empty!")
        return

    if not folder:
        print("The folder to upload to is not specified!")
        return

    print(f"Uploading folder: {folder}")

    for base, _, files in os.walk(local_folder):
        for file_name in tqdm(files, desc="Uploading files"):
            file_path = os.path.join(base, file_name)
            blob_name = os.path.relpath(file_path, local_folder).replace("\\", "/")
            upload_file(file_path, url, container, code, f"{folder}/{blob_name}", True)


class LabelTool:
    def __init__(self, master):
        # set up the main frame
        self.rootPanel = master
        self.rootPanel.title("AZ Vision - Trainer")
        self.rootPanel.resizable(width=False, height=False)

        self.baseDir = os.path.dirname(os.path.dirname(__file__))
        self.dataDir = os.path.join(self.baseDir, 'data')
        self.this_repo = str(pathlib.Path(__file__).parent.resolve().parent)
        self.configFile = os.path.join(self.dataDir, 'config', 'config.yml')

        # initialize global state
        self.config = {'url': "", 'container': "", 'code': "", 'next_box_after_class_set': True}
        if os.path.exists(self.configFile):
            with open(self.configFile, 'r') as file:
                loaded_config = yaml.safe_load(file)
                if loaded_config is not None:
                    self.config = loaded_config

            file.close()

        self.containerDir = os.path.join(self.dataDir, self.config['container'])
        self.modelDir = os.path.join(self.containerDir, 'models')
        self.batchDir = os.path.join(self.containerDir, 'batches')

        self.model = None
        self.currentBatchDir = ''
        self.imageList = []
        self.cur = 0
        self.total = 0
        self.imgRootName = None
        self.imageName = ''
        self.batchList = list_folders_in_folder_azure(self.config['url'], self.config['container'], self.config['code'], "batches")
        self.labelsDir = None
        self.labelFileName = ''
        self.tkimg = None
        self.currentLabelClass = ''
        self.classesList = [
            "generic",
            "woman",
            "man",
            "child",
            "stroller",
            "wheelchair"
        ]

        self.fileNameExt = "jpg"
        self.selectedBbox = 0

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

        # batch
        batch_frame = Frame(self.ctrTopPanel)
        batch_frame.grid(row=0, column=0, ipady=5, sticky=W + N)

        Button(batch_frame, text="Set code", command=self.set_code).pack(side=LEFT, padx=5)
        Button(batch_frame, text="Load model", command=self.reload_model).pack(side=LEFT, padx=5)

        self.batchSelector = ttk.Combobox(batch_frame, state='readonly')
        self.batchSelector.pack(side=LEFT, padx=5)
        self.batchSelector['values'] = self.batchList if self.batchList else [""]
        if len(self.batchSelector['values']) > 0:
            self.batchSelector.current(0)

        self.batchSelector.bind("<<ComboboxSelected>>", self.batch_select)

        Button(batch_frame, text="Download batch from server", command=self.batch_download_select).pack(side=LEFT, padx=5)
        Button(batch_frame, text="Upload labels to server", command=self.upload_labels).pack(side=LEFT, padx=5)

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
        self.rootPanel.bind("c", self.cancel_bbox) # press 'c' to cancel creation
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
        next_bbox_text = 'ON' if self.config['next_box_after_class_set'] else 'OFF'
        self.bNextBboxAfterClass = Button(next_bbox_frame, text=next_bbox_text, command=self.toggle_next_bbox_after_class)
        self.bNextBboxAfterClass.pack(side=LEFT)

        # showing bbox info & delete bbox
        Label(self.ctrClassPanel, text='Annotations:').grid(row=4, column=0, sticky=W + N)
        Button(self.ctrClassPanel, text='Delete Selected (z)', command=self.del_bbox).grid(row=5, column=0, sticky=W + N + S)
        Button(self.ctrClassPanel, text='Delete All (x)', command=self.del_all_bboxes).grid(row=6, column=0, sticky=W + N + S)
        self.annotationsList = Listbox(self.ctrClassPanel, width=80, height=12, selectmode="SINGLE", activestyle="none")
        self.annotationsList.grid(row=7, column=0, columnspan=2, sticky=N + S + W)
        self.annotationsList.bind("<<ListboxSelect>>", self.on_listbox_select)
        self.annotationsList.bind("<Up>", self.arrow_up)
        self.annotationsList.bind("w", self.arrow_up)
        self.annotationsList.bind("<Down>", self.arrow_down)
        self.annotationsList.bind("s", self.arrow_down)
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

        #  loading

        self.reload_model()
        self.batch_select()

    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.configFile), exist_ok=True)
            with open(self.configFile, 'w') as file:
                yaml.dump(self.config, file, default_flow_style=False)
        except Exception as exception:
            print(f"Failed to save config: {exception}")

    def set_code(self):
        popup = Toplevel(root)
        width = 250
        height = 75
        x = (root.winfo_screenwidth() / 2) - (width / 2)
        y = (root.winfo_screenheight() / 2) - (height / 2)
        popup.geometry('%dx%d+%d+%d' % (width, height, x, y))
        popup.title("Set code")
        popup_frame = Frame(popup)
        popup_frame.pack(pady=10)
        entry = Entry(popup_frame, width=25)
        entry.pack()
        button_frame = Frame(popup_frame)
        button_frame.pack(pady=5)
        Button(button_frame, text="Apply", command=lambda: [self.apply_code(entry.get()), popup.destroy()]).grid(row=0, column=0)
        Button(button_frame, text="Cancel", command=lambda: [popup.destroy()]).grid(row=0, column=1, padx=15)
        popup.focus_set()
        return

    def apply_code(self, new_code):
        url_search = re.search(r"(https://[^/]+/)", new_code)
        self.config['url'] = url_search.group(1) if url_search else ""
        container_search = re.search(r"https://[^/]+/([^?]+)\?sv=", new_code)
        self.config['container'] = container_search.group(1) if container_search else ""
        code_search = re.search(r"\?sv=(.+)", new_code)
        self.config['code'] = "sv=" + code_search.group(1) if code_search else ""
        self.save_config()
        self.containerDir = os.path.join(self.dataDir, self.config['container'])
        self.modelDir = os.path.join(self.containerDir, 'models')
        self.batchDir = os.path.join(self.containerDir, 'batches')
        self.unload()
        self.batchList = list_folders_in_folder_azure(self.config['url'], self.config['container'], self.config['code'], "batches")
        if len(self.batchList) > 0:
            self.batchSelector['values'] = self.batchList
            self.batchSelector.current(0)

    def unload(self):
        self.del_all_bboxes()
        self.mainPanel.delete(self.tkimg)
        self.selectedBbox = 0
        self.STATE = {}
        self.bboxIdList = []
        self.curBBoxId = None
        self.horizontalLine = None
        self.verticalLine = None
        self.currentBatchDir = ''
        self.imageList = []
        self.cur = 0
        self.total = 0
        self.imgRootName = None
        self.imageName = ''
        self.batchList = []
        self.batchSelector['values'] = [""]
        self.batchSelector.current(0)
        self.labelsDir = None
        self.labelFileName = ''
        self.tkimg = None

    def reload_model(self, event=None):
        thread = threading.Thread(target=download_folder, args=(self.config['url'], self.config['container'], self.config['code'], 'models', self.containerDir))
        thread.start()
        thread.join()
        self.load_model()

    def load_model(self):
        file = os.path.join(self.modelDir, 'best.pt')
        if os.path.exists(file):
            self.model = YOLO(file)
        else:
            self.model = None

    def batch_download_select(self, event=None):
        self.download_batch()
        self.batch_select()

    def batch_select(self, event=None):
        index = self.batchSelector.current()
        if index < 0 or index >= len(self.batchList):
            return

        batch = self.batchList[index]

        if not batch:
            return

        self.load_dir(os.path.join(self.batchDir, batch))

    def download_batch(self, event=None):
        index = self.batchSelector.current()
        if index < 0 or index >= len(self.batchList):
            return

        batch = self.batchList[index]

        if not batch:
            return

        thread = threading.Thread(target=download_folder, args=(self.config['url'], self.config['container'], self.config['code'], f"batches/{batch}", self.containerDir))
        thread.start()

        messagebox.showinfo("Batch", message=f"Downloading batch {batch}...\n\nProgress bar is in the command line.")

        thread.join()

        return

    def upload_labels(self, event=None):
        if not self.currentBatchDir:
            print("No batch selected for upload.")
            
            messagebox.showerror('Upload failed', 'No batch selected for upload.')

            return

        batch = os.path.basename(self.currentBatchDir)

        res = messagebox.askquestion('Upload labels', 'Warning, all labels from current batch will be uploaded to cloud storage, do you want to proceed?')
        if res == 'Yes':
            threading.Thread(target=upload_folder, args=(os.path.join(self.currentBatchDir, 'labels'), self.config['url'], self.config['container'], self.config['code'], f"batches/{batch}/labels")).start()

            messagebox.showinfo("Labels", message=f"Uploading labels from batch {batch}...\n\nProgress bar is in the command line.")

        return

    def load_dir(self, directory):
        self.rootPanel.focus()

        if not directory:
            return

        if not os.path.isdir(directory):
            return

        self.currentBatchDir = directory

        self.labelsDir = os.path.join(self.currentBatchDir, 'labels')
        if not os.path.isdir(self.labelsDir):
            os.makedirs(self.labelsDir, exist_ok=True)

        filelist = glob.glob(os.path.join(self.currentBatchDir, f"*.{self.fileNameExt}"))
        filelist = [file.split("\\")[-1] for file in filelist]  # in form of filename
        filelist = [os.path.splitext(file)[0] for file in filelist]  # remove extension
        self.imageList = filelist.copy()

        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

        # Load a model

        self.load_image()

        self.annotationsList.focus_set()

    def load_image(self):
        self.selectedBbox = -1
        self.tkimg = [0, 0, 0]

        # load image
        self.imgRootName = self.imageList[self.cur - 1]
        img_file_path = os.path.join(self.currentBatchDir, f"{self.imgRootName}.{self.fileNameExt}")
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
        if xyxy_list is None and self.model is not None:
            xyxy_list = self.get_predictions_from_yolo()

        if xyxy_list is not None:
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
        if self.model is None:
            return None

        rgb_img_file_path = os.path.join(self.batchDir, f"{self.imgRootName}.f{self.fileNameExt}")
        if not os.path.exists(rgb_img_file_path):
            return None

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
        annotation_file_path = os.path.join(self.labelsDir, f"{annotation_file_name}.txt")
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
        self.config['next_box_after_class_set'] = not self.config['next_box_after_class_set']
        self.config['next_box_after_class_set'] = self.config['next_box_after_class_set']
        new_text = "ON" if self.config['next_box_after_class_set'] else "OFF"
        self.bNextBboxAfterClass.config(text=new_text)
        self.save_config()

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

        self.annotationsList.focus_set()

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

        if self.config['next_box_after_class_set']:
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
    root.focus_force()
    root.mainloop()
