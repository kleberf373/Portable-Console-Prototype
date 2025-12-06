import tkinter as tk
from tkinter import ttk, Toplevel, messagebox, Canvas 
from .mapper_utility import GamepadMapperUtility 

# --- Key Mappings and Definitions (No changes here) ---
MAPPING_KEYS = {
    'Cross (X)': '0', 'Circle (C)': '1', 'Square (S)': '2', 'Triangle (D)': '3', 'L1 (Q)': '4',
    'R1 (W)': '5', 'L2 (A)': '6', 'R2 (Z)': '7', 'Select (LSHIFT)': '8', 'Start (ENTER)': '9',
    'L3 (1)': '10', 'R3 (2)': '11', 'D-Pad UP': '7_-1', 'D-Pad DOWN': '7_1', 'D-Pad LEFT': '6_-1',
    'D-Pad RIGHT': '6_1', 'L-Stick UP': '1_-1', 'L-Stick DOWN': '1_1', 'L-Stick LEFT': '0_-1',
    'L-Stick RIGHT': '0_1', 'R-Stick UP': '3_-1', 'R-Stick DOWN': '3_1', 'R-Stick LEFT': '2_-1',
    'R-Stick RIGHT': '2_1',
}

# Comprehensive list of Linux Key Codes for validation (Same as before)
LINUX_KEY_CODES = [
    'KEY_UNKNOWN', 'KEY_ESC', 'KEY_1', 'KEY_2', 'KEY_3', 'KEY_4', 'KEY_5', 'KEY_6', 'KEY_7', 
    'KEY_8', 'KEY_9', 'KEY_0', 'KEY_MINUS', 'KEY_EQUAL', 'KEY_BACKSPACE', 'KEY_TAB', 
    'KEY_Q', 'KEY_W', 'KEY_E', 'KEY_R', 'KEY_T', 'KEY_Y', 'KEY_U', 'KEY_I', 'KEY_O', 
    'KEY_P', 'KEY_LEFTBRACE', 'KEY_RIGHTBRACE', 'KEY_ENTER', 'KEY_LEFTCTRL', 'KEY_A', 
    'KEY_S', 'KEY_D', 'KEY_F', 'KEY_G', 'KEY_H', 'KEY_J', 'KEY_K', 'KEY_L', 'KEY_SEMICOLON', 
    'KEY_APOSTROPHE', 'KEY_GRAVE', 'KEY_LEFTSHIFT', 'KEY_BACKSLASH', 'KEY_Z', 'KEY_X', 
    'KEY_C', 'KEY_V', 'KEY_B', 'KEY_N', 'KEY_M', 'KEY_COMMA', 'KEY_DOT', 'KEY_SLASH', 
    'KEY_RIGHTSHIFT', 'KEY_KPASTERISK', 'KEY_LEFTALT', 'KEY_SPACE', 'KEY_CAPSLOCK', 
    'KEY_F1', 'KEY_F2', 'KEY_F3', 'KEY_F4', 'KEY_F5', 'KEY_F6', 'KEY_F7', 'KEY_F8', 
    'KEY_F9', 'KEY_F10', 'KEY_NUMLOCK', 'KEY_SCROLLLOCK', 'KEY_KP7', 'KEY_KP8', 'KEY_KP9', 
    'KEY_KPMINUS', 'KEY_KP4', 'KEY_KP5', 'KEY_KP6', 'KEY_KPPLUS', 'KEY_KP1', 'KEY_KP2', 
    'KEY_KP3', 'KEY_KP0', 'KEY_KPDOT', 'KEY_ZEND', 'KEY_RIGHTALT', 'KEY_KPENTER', 
    'KEY_RIGHTCTRL', 'KEY_KPSLASH', 'KEY_SYSRQ', 'KEY_RIGHTMETA', 'KEY_LEFTMETA', 
    'KEY_DELETE', 'KEY_HOME', 'KEY_END', 'KEY_UP', 'KEY_DOWN', 'KEY_LEFT', 'KEY_RIGHT', 
    'KEY_PAGEUP', 'KEY_PAGEDOWN', 'KEY_INSERT', 'KEY_PAUSE', 'KEY_F11', 'KEY_F12', 
    'KEY_F13', 'KEY_F14', 'KEY_F15', 'KEY_F16', 'KEY_F17', 'KEY_F18', 'KEY_F19', 
    'KEY_F20', 'KEY_F21', 'KEY_F22', 'KEY_F23', 'KEY_F24',
    'KEY_HANGEUL', 'KEY_HANJA', 'KEY_ZENKAKUHANKAKU', 'KEY_MUTE', 'KEY_VOLUMEDOWN', 
    'KEY_VOLUMEUP'
]

GRID_COLUMNS = 5 


# --- Key Selection Modal (Controller-Friendly) ---
class KeyGridPicker(Toplevel):
    """A controller-friendly modal to select a key code from a grid of buttons."""
    def __init__(self, parent, controller, friendly_name):
        super().__init__(parent)
        self.transient(parent)
        self.controller = controller
        self.parent = parent
        self.result = None
        self.title(f"Select Key for: {friendly_name}")
        
        self.geometry("800x600")
        self.update_idletasks()
        
        # Style
        self.configure(bg=self.controller.style.lookup('Main.TFrame', 'background'))
        
        ttk.Label(self, text=f"Select New Key for:\n{friendly_name}", 
                  style='Header.TLabel').pack(pady=(10, 20))
        
        # --- Scrollable Area for Keys ---
        self.canvas = Canvas(self, background=self.controller.style.lookup('Main.TFrame', 'background'), highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style='Main.TFrame', padding=10)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        # --- Key Grid ---
        self.navigable_widgets = []
        self.max_cols = GRID_COLUMNS
        self.create_key_grid()
        
        # --- Setup Navigation and focus management ---
        self.grab_set()
        
        # ### MODIFIED: Bind the directional and selection events ###
        self.bind_events()
        
        # IMPORTANT: Tell the main controller to switch focus to this modal's buttons
        self.controller.push_frame_navigable_widgets(self.navigable_widgets)
        self.after(50, lambda: self.scroll_to_selected_widget(self.controller.current_focus_index))

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.wait_window(self)

    def create_key_grid(self):
        # Filter out KEY_UNKNOWN as it's not a useful mapping target
        key_codes = [key.replace('KEY_', '') for key in LINUX_KEY_CODES if key not in ['KEY_UNKNOWN', 'KEY_ZEND']]
        
        row = 0
        col = 0
        
        grid_frame = ttk.Frame(self.scrollable_frame, style='Main.TFrame')
        grid_frame.pack(fill='x', padx=10, pady=10)

        for key_name in key_codes:
            btn = ttk.Button(grid_frame, text=key_name, 
                             command=lambda code=f"KEY_{key_name}": self.select_key(code),
                             style='Small.TButton')
            btn.grid(row=row, column=col, sticky='nsew', padx=5, pady=5)
            self.navigable_widgets.append(btn)
            
            grid_frame.grid_columnconfigure(col, weight=1)
            
            col += 1
            if col >= self.max_cols:
                col = 0
                row += 1
                
        # Add a CANCEL button at the end
        cancel_btn = ttk.Button(self.scrollable_frame, text="CANCEL",
                                command=self.on_closing,
                                style='Small.TButton')
        cancel_btn.pack(pady=(20, 10))
        self.navigable_widgets.append(cancel_btn)
        
    def bind_events(self):
        """Binds directional events to the Toplevel window for 2D navigation and selection."""
        # Binds directional inputs to 2D navigation logic
        self.bind('<Up>', lambda e: self.handle_navigation('up'), add='+')
        self.bind('<Down>', lambda e: self.handle_navigation('down'), add='+')
        self.bind('<Left>', lambda e: self.handle_navigation('left'), add='+')
        self.bind('<Right>', lambda e: self.handle_navigation('right'), add='+')
        
        # ### NEW: Bind selection key (Enter) to invoke the button click ###
        self.bind('<Return>', self.handle_selection, add='+') 
        self.bind('<KP_Enter>', self.handle_selection, add='+')
        
    def handle_selection(self, event):
        """Triggers the click event on the currently focused widget."""
        current_index = self.controller.current_focus_index
        if 0 <= current_index < len(self.navigable_widgets):
            # Programmatically call the command associated with the button
            self.navigable_widgets[current_index].invoke() 
            return 'break' # Stop propagation

    def handle_navigation(self, direction):
        """Calculates the next focus index based on 2D grid movement."""
        if not self.navigable_widgets:
            return

        current_index = self.controller.current_focus_index
        num_widgets = len(self.navigable_widgets)
        
        # The CANCEL button is always the last element, located outside the grid structure.
        # We must handle movement into/out of the CANCEL button area specifically.
        grid_size = num_widgets - 1
        
        new_index = current_index
        
        if direction == 'up':
            if current_index == grid_size: # Moving UP from CANCEL
                # Land on the last button in the key grid
                new_index = grid_size - 1
            elif current_index >= self.max_cols:
                # Standard grid move up
                new_index = current_index - self.max_cols
        
        elif direction == 'down':
            if current_index < grid_size and current_index >= grid_size - self.max_cols:
                # Moving DOWN from the last row of the grid into CANCEL
                new_index = grid_size
            elif current_index < grid_size - self.max_cols:
                # Standard grid move down
                new_index = current_index + self.max_cols
        
        elif direction == 'left':
            if current_index == grid_size:
                # Left from CANCEL: Go to the last button on the bottom-most row
                new_index = grid_size - 1
            elif current_index % self.max_cols != 0:
                # Standard grid move left (not in the first column)
                new_index = current_index - 1
        
        elif direction == 'right':
            if current_index < grid_size and (current_index + 1) % self.max_cols != 0:
                # Standard grid move right (not in the last column of a full row)
                # Ensure we don't land outside the grid bounds
                if new_index + 1 < grid_size:
                    new_index = current_index + 1
        else:
            return

        # Ensure index is within bounds (0 to len-1)
        if 0 <= new_index < num_widgets:
            self.controller.set_focus(new_index)
            # After moving focus, scroll to the newly focused widget
            self.after(50, lambda: self.scroll_to_selected_widget(new_index))
        
        # ### MODIFIED: Ensure the event propagation is stopped after handling ###
        return 'break' 

    def scroll_to_selected_widget(self, index):
        """Scrolls the canvas to ensure the widget at the given index is visible."""
        if index < 0 or index >= len(self.navigable_widgets):
            return
            
        widget = self.navigable_widgets[index]
        self.update_idletasks() 

        # Get total height of the scrollable content
        scrollable_height = self.scrollable_frame.winfo_reqheight() 
        canvas_height = self.canvas.winfo_height()

        if scrollable_height <= canvas_height:
             return

        # Get the widget's position within the scrollable_frame
        widget_y_start = widget.winfo_y()
        widget_height = widget.winfo_height()
        
        # Calculate the current view position (top of the view)
        view_start_frac, _ = self.canvas.yview()
        view_start_pixel = int(view_start_frac * scrollable_height)
        
        widget_top = widget_y_start
        widget_bottom = widget_y_start + widget_height

        # 1. Scroll DOWN if the widget is below the visible area
        if widget_bottom > (view_start_pixel + canvas_height):
            # Calculate the fractional position to make the widget appear at the bottom of the view + a buffer
            target_pos_pixel = widget_bottom - canvas_height + 30
            target_pos = target_pos_pixel / scrollable_height
            self.canvas.yview_moveto(max(0.0, target_pos))
            
        # 2. Scroll UP if the widget is above the visible area
        elif widget_top < view_start_pixel:
            # Calculate the fractional position to make the widget appear at the top of the view - a buffer
            target_pos_pixel = widget_top - 30
            target_pos = target_pos_pixel / scrollable_height
            self.canvas.yview_moveto(max(0.0, target_pos))


    def select_key(self, key_code):
        self.result = key_code
        self.destroy()

    def on_closing(self):
        self.result = None
        self.destroy()
        
    def destroy(self):
        # IMPORTANT: Restore navigation state on the main frame
        self.controller.pop_frame_navigable_widgets()
        super().destroy()


# --- Main Remapper Frame (No changes here, remains for context) ---

class ControllerRemapperFrame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        self.mapper_utility = GamepadMapperUtility()
        self.mapper_utility.read_mappings()
        self.selected_key_friendly = None
        self.button_labels = {} 
        self.navigable_widgets = [] 

        self.canvas = Canvas(self, background=self.controller.style.lookup('Main.TFrame', 'background'), highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style='Main.TFrame')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="top", fill="both", expand=True, padx=20, pady=20)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        self.create_widgets()
        
    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def create_widgets(self):
        ttk.Label(self.scrollable_frame, text="Controller Remapper", 
                  style='Header.TLabel').pack(pady=(10, 30))
        
        mapping_frame = ttk.Frame(self.scrollable_frame, style='Main.TFrame', padding=20)
        mapping_frame.pack(padx=50, pady=10, fill="x", expand=True)

        current_mappings = self.mapper_utility.get_all_mappings()
        mapping_frame.columnconfigure(0, weight=1) 
        mapping_frame.columnconfigure(1, weight=1) 

        row = 0
        for friendly_name, map_key in MAPPING_KEYS.items():
            ttk.Label(mapping_frame, text=friendly_name, 
                      style='Remapper.TLabel', anchor='w').grid(row=row, column=0, sticky='w', padx=10, pady=5)
            
            key_code = current_mappings.get(map_key, "KEY_???")
            display_text = key_code.replace('KEY_', '')
            
            label = ttk.Label(mapping_frame, text=display_text, 
                              style='Remapper.TLabel', anchor='e', width=15)
            label.grid(row=row, column=1, sticky='e', padx=10, pady=5)
            self.button_labels[friendly_name] = label 
            
            action_btn = ttk.Button(mapping_frame, text="Set", 
                                    command=lambda name=friendly_name: self.start_remapping(name),
                                    style='Small.TButton')
            action_btn.grid(row=row, column=2, sticky='e', padx=(30, 0), pady=5)
            
            self.navigable_widgets.append(action_btn)
            row += 1

        save_btn = ttk.Button(self.scrollable_frame, text="✓ Save Changes and Exit",
                              command=self.save_and_return,
                              style='Small.TButton')
        save_btn.pack(pady=(30, 20))
        self.navigable_widgets.append(save_btn) 
        
        self.controller.set_navigable_widgets(self.navigable_widgets)
        self.controller.set_focus(0) 
        self.after(50, lambda: self.scroll_to_selected_widget(self.controller.current_focus_index)) 


    def scroll_to_selected_widget(self, index):
        if not self.navigable_widgets:
            return
            
        widget = self.navigable_widgets[index]
        self.update_idletasks() 

        scrollable_height = self.scrollable_frame.winfo_height() 
        canvas_height = self.canvas.winfo_height()

        if scrollable_height <= canvas_height:
             return

        widget_y_start = widget.winfo_y()
        widget_height = widget.winfo_height()
        
        view_start, _ = self.canvas.yview()
        view_start_pixel = int(view_start * scrollable_height)
        
        widget_top = widget_y_start
        widget_bottom = widget_y_start + widget_height

        if widget_bottom > (view_start_pixel + canvas_height):
            target_pos = (widget_bottom - canvas_height + 30) / scrollable_height
            self.canvas.yview_moveto(max(0.0, target_pos))
            
        elif widget_top < view_start_pixel:
            target_pos = (widget_top - 30) / scrollable_height
            self.canvas.yview_moveto(max(0.0, target_pos))

    def get_navigable_widgets(self):
        return self.navigable_widgets
        
    def start_remapping(self, friendly_name):
        if self.selected_key_friendly in self.button_labels:
            self.button_labels[self.selected_key_friendly].configure(style='Remapper.TLabel')
        self.selected_key_friendly = friendly_name
        self.button_labels[friendly_name].configure(style='Focus.TLabel')
        self.open_key_grid_picker(friendly_name)

    def open_key_grid_picker(self, friendly_name):
        picker = KeyGridPicker(self, self.controller, friendly_name)
        new_key_code = picker.result
        if new_key_code:
            map_key = MAPPING_KEYS[friendly_name]
            if self.mapper_utility.update_mapping(map_key, new_key_code):
                self.update_labels()
        
        if self.selected_key_friendly in self.button_labels:
            self.button_labels[self.selected_key_friendly].configure(style='Remapper.TLabel')
            self.selected_key_friendly = None

    def update_labels(self):
        current_mappings = self.mapper_utility.get_all_mappings()
        for friendly_name, label in self.button_labels.items():
            map_key = MAPPING_KEYS[friendly_name]
            key_code = current_mappings.get(map_key, "KEY_???")
            display_text = key_code.replace('KEY_', '')
            label.configure(text=display_text)

    def save_and_return(self):
        self.mapper_utility.write_mappings()
        messagebox.showinfo("Success", "Controller mappings saved to map.txt!")
        self.controller.show_frame("MainMenuFrame")