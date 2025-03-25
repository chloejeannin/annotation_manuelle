import tkinter as tk
from tkinter import simpledialog, ttk
import pandas as pd
import os
import time
from PIL import Image, ImageTk, ImageDraw


num_video="02"
# Configuration
data_path = "images/"+num_video
output_txt = "annotations_"+num_video+".txt"
if not os.path.exists(output_txt):
    open(output_txt,"a").close()

users = ["Chloé", "Lucie", "Corentin","Mathis","Julien", "Aina", "Cédric", "Philipe", "Carl"]
classes = ["Car", "Truck", "Cyclist", "Pedestrian", "Van", "Misc", "Person_sitting","Tram","DontCare"]

class_colors = {
    "Car": "red",
    "Truck": "green",
    "Pedestrian": "cyan",
    "Cyclist": "yellow",
    "Van": "white",
    "Misc": "black",
    "Person_sitting": "orange",
    "Tram": "purple",
    "DontCare": "Blue"
}

class AnnotationTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Annotation Tool")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.root.state('zoomed')  # Open in maximized windowed mode
        
        self.user = simpledialog.askstring("Utilisateur", "Entrez votre nom:", initialvalue=users[0])
        if self.user not in users:
            self.user = users[0]
        
        self.selected_class = tk.StringVar(value=classes[0])
        self.zoom_level = 1.0
        self.zoom_center = (0, 0)
        
        self.create_toolbar()
        
        self.image_files = [f for f in os.listdir(data_path) if f.endswith((".png", ".jpg", ".jpeg"))]
        self.image_index = 0
        
        self.annotations = []
        self.rectangles = []
        self.selected_rectangle = None
        self.dragging = False
        self.resizing = False
        self.resize_handle_size = 8
        
        self.canvas = tk.Canvas(root, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.zoom)  # Windows
        self.canvas.bind("<Button-4>", self.zoom)  # Linux (Zoom in)
        self.canvas.bind("<Button-5>", self.zoom)  # Linux (Zoom out)
        
        self.total_counter = tk.Label(root, text="Total: 0")
        self.total_counter.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.class_counters = {cls: tk.Label(root, text=f"{cls}: 0") for cls in classes}
        for counter in self.class_counters.values():
            counter.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.load_image()

    def update_counters(self):
        total = len(self.rectangles)
        self.total_counter.config(text=f"Total: {total}")
        
        class_counts = {cls: 0 for cls in classes}
        for rect in self.rectangles:
            class_counts[rect['class']] += 1
        
        for cls, count in class_counts.items():
            self.class_counters[cls].config(text=f"{cls}: {count}")

    def create_toolbar(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Combobox(toolbar, textvariable=self.selected_class, values=classes, state="readonly").pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar, text="Précédent", command=self.previous_image).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Suivant", command=self.next_image).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Sauvegarder", command=self.save_annotations).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Supprimer la sélection", command=self.delete_selected_rectangle).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Supprimer la dernière", command=self.delete_last_rectangle).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Reset Zoom", command=self.reset_zoom).pack(side=tk.LEFT, padx=5)

    def delete_last_rectangle(self):
        if self.rectangles:
            last_rectangle = self.rectangles[-1]
            self.canvas.delete(last_rectangle['id'])
            self.rectangles.remove(last_rectangle)
            if last_rectangle in self.annotations:
                self.annotations.remove(last_rectangle)
            if self.selected_rectangle == last_rectangle:
                self.selected_rectangle = None
            self.update_counters()
                
    def load_image(self):
        if self.image_index < 0:
            self.image_index = 0
        if self.image_index >= len(self.image_files):
            self.on_close()
            return
        
        self.image_path = os.path.join(data_path, self.image_files[self.image_index])
        self.pil_image = Image.open(self.image_path)
        self.original_width, self.original_height = self.pil_image.size
        
        self.zoom_level = 1.0
        self.zoom_center = (self.original_width // 2, self.original_height // 2)
        
        self.update_image_display()
        
        self.annotations.clear()
        self.rectangles.clear()
        self.update_counters()

    def update_image_display(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        new_width = screen_width
        new_height = int(self.original_height * (screen_width / self.original_width))
        
        if new_height > screen_height:
            new_height = screen_height
            new_width = int(self.original_width * (screen_height / self.original_height))
        
        resized_image = self.pil_image.resize((new_width, new_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized_image)
        
        self.canvas.delete("all")
        self.canvas.config(width=new_width, height=new_height)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        
        self.root.geometry(f"{new_width}x{new_height+40}")
        
        self.redraw_rectangles()

    def redraw_rectangles(self):
        for rect in self.rectangles:
            x1, y1, x2, y2 = rect['original_coords']
            
            scaled_coords = [
                x1 * self.zoom_level,
                y1 * self.zoom_level,
                x2 * self.zoom_level,
                y2 * self.zoom_level
            ]
            
            if 'id' in rect:
                self.canvas.coords(rect['id'], *scaled_coords)
            else:
                rect['id'] = self.canvas.create_rectangle(*scaled_coords, outline=self.get_class_color(rect['class']), width=2)
            
            rect['coords'] = scaled_coords

    def find_rectangle(self, x, y):
        x_orig = x / self.zoom_level
        y_orig = y / self.zoom_level
        tolerance = max(5 / self.zoom_level, 2)
        
        for rect in reversed(self.rectangles):
            x1, y1, x2, y2 = rect['original_coords']
            
            if (min(x1,x2) - tolerance <= x_orig <= max(x1,x2) + tolerance and
                min(y1,y2) - tolerance <= y_orig <= max(y1,y2) + tolerance):
                return rect
        return None

    def on_press(self, event):
        x = event.x / self.zoom_level
        y = event.y / self.zoom_level
        
        self.start_x, self.start_y = x, y
        self.selected_rectangle = self.find_rectangle(event.x, event.y)
        
        if self.selected_rectangle:
            self.dragging = True
            rect_coords = self.selected_rectangle['original_coords']
            self.offset_x = x - rect_coords[0]
            self.offset_y = y - rect_coords[1]
            self.highlight_rectangle(self.selected_rectangle['id'])
            
            if self.is_on_handle(x, y, rect_coords):
                self.resizing = True
                self.dragging = False
        else:
            self.dragging = False
            self.resizing = False

    def on_drag(self, event):
        x = event.x / self.zoom_level
        y = event.y / self.zoom_level
        
        if self.dragging and self.selected_rectangle:
            dx = x - self.start_x
            dy = y - self.start_y
            
            original_coords = self.selected_rectangle['original_coords']
            new_coords = [
                original_coords[0] + dx,
                original_coords[1] + dy,
                original_coords[2] + dx,
                original_coords[3] + dy
            ]
            
            self.selected_rectangle['original_coords'] = self.crop_coords(new_coords)
            self.redraw_rectangles()
            
            self.start_x = x
            self.start_y = y
        
        elif self.resizing and self.selected_rectangle:
            original_coords = self.selected_rectangle['original_coords']
            new_coords = [
                original_coords[0],
                original_coords[1],
                x,
                y
            ]
            
            self.selected_rectangle['original_coords'] = self.crop_coords(new_coords)
            self.redraw_rectangles()

    def on_release(self, event):
        if not self.dragging and not self.resizing:
            x1, y1 = self.start_x, self.start_y
            x2 = event.x / self.zoom_level
            y2 = event.y / self.zoom_level
            
            rect_id = self.canvas.create_rectangle(
                x1 * self.zoom_level,
                y1 * self.zoom_level,
                x2 * self.zoom_level,
                y2 * self.zoom_level,
                outline=self.get_class_color(), 
                width=2
            )
            
            annotation = {
                'id': rect_id,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'user': self.user,
                'image': self.image_files[self.image_index],
                'class': self.selected_class.get(),
                'original_coords': self.crop_coords([x1, y1, x2, y2]),
                'coords': [
                    x1 * self.zoom_level,
                    y1 * self.zoom_level,
                    x2 * self.zoom_level,
                    y2 * self.zoom_level
                ]
            }
            self.rectangles.append(annotation)
            self.annotations.append(annotation)
            self.update_counters()
        
        self.dragging = False
        self.resizing = False

    def crop_coords(self, coords):
        x1, y1, x2, y2 = coords
        x1 = max(0, min(self.original_width, x1))
        y1 = max(0, min(self.original_height, y1))
        x2 = max(0, min(self.original_width, x2))
        y2 = max(0, min(self.original_height, y2))
        return [x1, y1, x2, y2]

    def is_on_handle(self, x, y, coords):
        handle_x, handle_y = coords[2], coords[3]
        handle_size = self.resize_handle_size / self.zoom_level
        return abs(x - handle_x) <= handle_size and abs(y - handle_y) <= handle_size
    
    def highlight_rectangle(self, rect_id):
        for rect in self.rectangles:
            outline_color = self.get_class_color(rect['class'])
            width = 2
            if rect['id'] == rect_id:
                outline_color = "blue"
                width = 3
            self.canvas.itemconfig(rect['id'], outline=outline_color, width=width)
    
    def delete_selected_rectangle(self):
        if self.selected_rectangle:
            self.canvas.delete(self.selected_rectangle['id'])
            self.rectangles.remove(self.selected_rectangle)
            self.annotations.remove(self.selected_rectangle)
            self.selected_rectangle = None
            self.update_counters()
    
    def zoom(self, event):
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            zoom_factor = 1.2
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            zoom_factor = 0.8
        else:
            return
        
        if hasattr(event, 'x') and hasattr(event, 'y'):
            mouse_x = event.x / self.zoom_level
            mouse_y = event.y / self.zoom_level
        else:
            mouse_x = self.original_width / 2
            mouse_y = self.original_height / 2
        
        new_zoom = self.zoom_level * zoom_factor
        if 0.1 <= new_zoom <= 5.0:
            self.zoom_level = new_zoom
            self.zoom_center = (mouse_x, mouse_y)
            self.update_image_display()
    
    def reset_zoom(self):
        self.zoom_level = 1.0
        self.zoom_center = (self.original_width // 2, self.original_height // 2)
        self.update_image_display()
    
    def save_annotations(self):
        if self.annotations:
            with open(output_txt, "a") as file:
                for ann in self.annotations:
                    data = f"{ann['image'][:-4]} {ann['class']} {' '.join(map(str, ann['original_coords']))} {ann['timestamp']} {ann['user']}\n"
                    file.write(data)
            print("Annotations sauvegardées.")
            self.annotations.clear()
    
    def previous_image(self):
        self.save_annotations()
        self.image_index -= 1
        self.load_image()

    def next_image(self):
        self.save_annotations()
        self.image_index += 1
        self.load_image()
    
    def on_close(self):
        self.save_annotations()
        self.root.destroy()

    def get_class_color(self, class_name=None):
        if not class_name:
            class_name = self.selected_class.get()
        return class_colors.get(class_name, "black")

if __name__ == "__main__":
    root = tk.Tk()
    app = AnnotationTool(root)
    root.mainloop()