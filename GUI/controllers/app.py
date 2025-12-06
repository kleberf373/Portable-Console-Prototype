import tkinter as tk
from tkinter import ttk, Canvas
from tkinter.font import Font
import os
import subprocess
import json
import pygame
import time
from PIL import Image, ImageTk

os.path.dirname(os.path.abspath(__file__))
from .remapper_gui import ControllerRemapperFrame

class TouchMenuApp:
    def __init__(self, root: tk.Tk): 
        self.root = root
        self.root.title("Touch Menu")
        self.root.geometry("1024x600")
        self.root.configure(background="dark green")
        self.root.resizable(True, True)
        self.root.minsize(width=788, height=588)

        self.big_font = Font(family='Helvetica', size=24, weight='bold')
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('Main.TFrame', bg= "dark green")
        # Define a base style for the button to make sure it looks good
        self.style.configure('Small.TButton', font=self.big_font, padding=30, relief='flat', foreground='white')
        self.style.map('Small.TButton', background=[('active', '#2980b9'), ('pressed', '#1c638e')])
        
        # --- Styles for Navigation Focus (NEW/MODIFIED) ---
        # The base style for labels in the remapper
        self.style.configure('Remapper.TLabel', font=('Helvetica', 16), background='lightgrey', foreground='black', padding=5)
        # Style for the currently focused/selected item (used for D-Pad navigation)
        self.style.configure('Focus.TButton', background='#2980b9', foreground='white', font=self.big_font, padding=30, relief='solid', borderwidth=3, bordercolor='white')
        self.style.configure('Focus.TLabel', background='#2980b9', foreground='white', font=('Helvetica', 16), padding=5, relief='solid', borderwidth=3, bordercolor='white')
        # Map Focus style back to the base style when not active
        self.style.map('Small.TButton', background=[('active', '#2980b9'), ('pressed', '#1c638e'), ('focus', '#3498db')])
        # --- END Styles ---
        
        self.joystick = None
        self.held_shoulder_buttons = set()
        self.SHOULDER_BUTTONS = {4, 5, 6, 7} # L1, R1, L2, R2
        self.STICK_BUTTONS = {10, 11} # L3, R3

        # ### NEW: State management for menu navigation ###
        self.navigable_widgets = [] # List of buttons on the current page
        self.current_focus_index = -1 # Index of the currently "selected" button
        self.last_nav_time = 0 # For debouncing D-pad input
        self.NAV_DEBOUNCE_MS = 180 # Cooldown between navigation inputs (in milliseconds)
        # ### NEW: END ###

        self.games_data = {}
        self.load_games_data("games.json")
        
        self.setup_styles()
        
        container = ttk.Frame(self.root, style='Main.TFrame')
        container.pack(side="top", fill="both", expand=True)

        self.frames = {}
        # ### FIX: Initialize current_frame before frame instantiation starts ###
        self.current_frame = None 
        # ### NEW FIX: Initialize current_frame_name to prevent AttributeError in navigation logic ###
        self.current_frame_name = None 
        
        self.navigation_stack = []

        # We need to import frames here to avoid circular dependency
        from .frames import MainMenuFrame, GamesListFrame, SettingsFrame
        
        # Initialize all frames
        for F in (MainMenuFrame, GamesListFrame, SettingsFrame, ControllerRemapperFrame): # Added ControllerRemapperFrame
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            # The frame is placed on top of the container, but only the current one is visible
            frame.grid(row=0, column=0, sticky="nsew")

        # The initial frame to show
        self.show_frame("MainMenuFrame")
        
        # Start Pygame and the polling loop
        self.start_pygame()
        self.root.after(100, self.poll_joystick_events)
        
    # --- Navigation Methods (NEW/MODIFIED) ---

    def set_navigable_widgets(self, widgets):
        """
        Sets the list of widgets that can be navigated by the controller (D-Pad).
        This method was missing, causing the AttributeError.
        """
        self.navigable_widgets = widgets
        self.current_focus_index = -1 # Reset focus whenever the list changes
        # Ensure the first element gets focus if the list is not empty
        if self.navigable_widgets:
            self.move_focus(1) # Move down once to select the first item

    def push_frame_navigable_widgets(self, widgets):
        """Temporarily saves current navigation state and sets a new list (for modals)."""
        # Save the current state (widgets list, focus index)
        self.navigation_stack.append({
            'widgets': self.navigable_widgets,
            'index': self.current_focus_index
        })
        
        self.navigable_widgets = widgets
        self.set_focus(0) # Start focus on the first item in the modal

    def pop_frame_navigable_widgets(self):
        """Restores the previous navigation state from the stack (after modal closes)."""
        if self.navigation_stack:
            previous_state = self.navigation_stack.pop()
            
            self.navigable_widgets = previous_state['widgets']
            
            # Restore the focus index, but ensure it's valid
            if 0 <= previous_state['index'] < len(self.navigable_widgets):
                self.set_focus(previous_state['index']) 
            else:
                 # If the index is no longer valid (e.g., list size changed), reset to 0
                self.set_focus(0)

    def move_focus(self, direction: int):
        """
        Moves the focus up (-1) or down (1) on the navigable widgets list.
        """
        if not self.navigable_widgets:
            return

        new_index = self.current_focus_index + direction
        num_widgets = len(self.navigable_widgets)

        # Handle wrap around
        if new_index < 0:
            new_index = num_widgets - 1
        elif new_index >= num_widgets:
            new_index = 0

        self.set_focus(new_index)

    def set_focus(self, new_index: int):
        """
        Applies focus style to the new widget and removes it from the old one.
        Also handles scrolling for frames with a scrollable Canvas.
        """
        if not self.navigable_widgets or self.current_focus_index == new_index:
            return

        # 1. Remove focus style from the old widget
        if self.current_focus_index != -1:
            old_widget = self.navigable_widgets[self.current_focus_index]
            # Determine the original style based on widget type
            if isinstance(old_widget, ttk.Button):
                old_widget.config(style='Small.TButton')
            elif isinstance(old_widget, ttk.Label):
                old_widget.config(style='Remapper.TLabel') # Assuming Remapper.TLabel is the base style
            # For other widgets, you might need more specific logic

        # 2. Apply focus style to the new widget
        new_widget = self.navigable_widgets[new_index]
        if isinstance(new_widget, ttk.Button):
            new_widget.config(style='Focus.TButton')
        elif isinstance(new_widget, ttk.Label):
            new_widget.config(style='Focus.TLabel') # Assuming Focus.TLabel is the focus style

        # 3. Update the index
        self.current_focus_index = new_index

        # 4. Handle scrolling if the current frame has a canvas (e.g., GamesListFrame)
        if self.current_frame is None: # Defensive check for initialization phase
            return

        current_frame = self.frames[self.current_frame_name] # or however you get the current frame
        if hasattr(current_frame, 'scroll_to_selected_widget'):
            current_frame.scroll_to_selected_widget(new_index)  

    def activate_focus(self):
        """
        Simulates a click on the currently focused widget.
        """
        if self.current_focus_index != -1 and self.navigable_widgets:
            focused_widget = self.navigable_widgets[self.current_focus_index]
            # Trigger the command/action associated with the widget
            if isinstance(focused_widget, ttk.Button) and focused_widget.cget('command'):
                focused_widget.invoke()
            elif isinstance(focused_widget, ttk.Label):
                # This is a label in the remapper (RemapperFrame).
                # The label's action is tied to its parent frame, which uses the click to trigger the picker.
                # In this specific case, we simulate the click event which the remapper_gui uses.
                current_frame_name = self.current_frame.__class__.__name__
                if current_frame_name == 'ControllerRemapperFrame':
                    # Need to get the friendly name from the label and call the handler
                    # The focused widget text is the key value (e.g., "ENTER"), which is not enough.
                    # This interaction needs to be handled within the ControllerRemapperFrame.
                    if hasattr(self.current_frame, 'activate_focus_element') and callable(self.current_frame.activate_focus_element):
                        # Assuming the remapper frame has a method to activate the selected element
                        self.current_frame.activate_focus_element(focused_widget)
                    else:
                        print("Warning: Remapper frame missing activate_focus_element method.")
                
            # After activation, remove the visual focus to ensure consistency when the frame changes
            # self.set_focus(-1) # Do not remove focus yet, let the frame change handle it
            
    # --- END: Navigation Methods ---
    

    def scroll_to_widget(self, widget):
        """
        Adjusts the canvas scroll position to ensure the target widget is visible.
        This is designed to work with GamesListFrame which has a Canvas setup.
        """
        current_frame_name = self.current_frame.__class__.__name__
        if current_frame_name != 'GamesListFrame' or not hasattr(self.current_frame, 'canvas'):
            return
            
        # 1. Get necessary dimensions and coordinates relative to the canvas's scroll region (list_frame)
        canvas = self.current_frame.canvas
        list_frame = self.current_frame.list_frame
        
        # Calculate widget's position and size
        widget.update_idletasks()
        widget_y_rel = widget.winfo_y() # y-coordinate relative to its master (list_frame)
        widget_height = widget.winfo_height()
        widget_y1 = widget_y_rel # Top of the widget relative to list_frame top
        widget_y2 = widget_y_rel + widget_height # Bottom of the widget relative to list_frame top

        # Get the total scrollable height
        list_frame.update_idletasks()
        list_frame_height = list_frame.winfo_reqheight() 

        # Get the current visible area of the canvas
        canvas.update_idletasks()
        canvas_height = canvas.winfo_height()
        
        canvas_view_start_fraction = float(canvas.yview()[0])
        canvas_view_start = canvas_view_start_fraction * list_frame_height
        canvas_view_end = canvas_view_start + canvas_height

        # 3. Calculate the required scroll
        # If the widget is above the view, scroll up
        if widget_y1 < canvas_view_start:
            # Scroll up so the top of the widget aligns with the top of the view
            target_fraction = (widget_y1) / list_frame_height 
            canvas.yview_moveto(max(0.0, target_fraction))
        
        # If the widget is below the view, scroll down
        elif widget_y2 > canvas_view_end:
            # Scroll down so the bottom of the widget aligns with the bottom of the view
            target_fraction = (widget_y2 - canvas_height) / list_frame_height 
            canvas.yview_moveto(min(1.0, target_fraction))


    # --- Remaining App Methods (show_frame, start_pygame, poll_joystick_events, etc.) ---
    
    def setup_styles(self):
        self.style.configure('Main.TFrame', background='dark green')
        # Define a base style for the button to make sure it looks good
        self.style.configure('Small.TButton', font=self.big_font, padding=30, relief='flat', foreground='white')
        self.style.map('Small.TButton', background=[('active', '#2980b9'), ('pressed', '#1c638e'), ('focus', '#3498db')])
        
        # Styles for the Remapper Frame
        self.style.configure('Remapper.TLabel', font=('Helvetica', 16), background='lightgrey', foreground='black', padding=5)
        self.style.configure('Focus.TLabel', background='#2980b9', foreground='white', font=('Helvetica', 16), padding=5, relief='solid', borderwidth=3)
        self.style.configure('Focus.TButton', background='#2980b9', foreground='white', font=self.big_font, padding=30, relief='solid', borderwidth=3)
        self.style.configure('Title.TLabel', font=('Helvetica', 24, 'bold'), foreground='white', background='dark green')
        
    def load_games_data(self, json_path):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        full_path = os.path.join(base_dir, json_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as f:
                    self.games_data = json.load(f) # <--- JSON data (console structure) is loaded here
            except Exception as e:
                print(f"Error reading games.json: {e}")
        else:
            print(f"JSON file not found at: {full_path}")

    def show_frame(self, page_name):
        """Show a frame for the given page name"""
        frame = self.frames[page_name]
        frame.tkraise()
        self.current_frame = frame
        # ### NEW FIX: Store the name of the current frame ###
        self.current_frame_name = page_name
        
        # Try to get navigable widgets from the new frame
        self.navigable_widgets = []
        self.current_focus_index = -1
        if hasattr(frame, 'get_navigable_widgets') and callable(frame.get_navigable_widgets):
            self.set_navigable_widgets(frame.get_navigable_widgets())
            
        # Call on_show lifecycle method if it exists (for refreshing data)
        if hasattr(frame, 'on_show') and callable(frame.on_show):
            frame.on_show()


    def start_pygame(self):
        # Initialize Pygame for joystick handling
        try:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                print(f"Joystick detected: {self.joystick.get_name()}")
            else:
                print("No joystick detected.")
        except pygame.error as e:
            print(f"Pygame/Joystick initialization error: {e}")

    def poll_joystick_events(self):
        # Process Pygame events
        # Use time.time() * 1000 for milliseconds instead of winfo_time()
        current_time_ms = int(time.time() * 1000) 
        
        for event in pygame.event.get():
            if event.type == pygame.JOYAXISMOTION:
                self.handle_axis_motion(event, current_time_ms)
            elif event.type == pygame.JOYBUTTONDOWN:
                self.handle_button_press(event)
            elif event.type == pygame.JOYBUTTONUP:
                self.handle_button_release(event)
            elif event.type == pygame.JOYHATMOTION:
                self.handle_hat_motion(event, current_time_ms)

        # Re-schedule the polling
        self.root.after(10, self.poll_joystick_events)

    def handle_axis_motion(self, event, current_time_ms):
        # Simplified threshold for D-pad simulation on analog sticks
        axis = event.axis
        value = event.value
        THRESHOLD = 0.5
        
        # Check for L-Stick (Axis 0 horizontal, Axis 1 vertical)
        if axis == 0 and abs(value) > THRESHOLD: # X-axis
            if current_time_ms - self.last_nav_time > self.NAV_DEBOUNCE_MS:
                self.last_nav_time = current_time_ms
                if value < 0: # Left
                    pass # Not typically used for vertical menu navigation
                else: # Right
                    pass # Not typically used for vertical menu navigation
        elif axis == 1 and abs(value) > THRESHOLD: # Y-axis
            if current_time_ms - self.last_nav_time > self.NAV_DEBOUNCE_MS:
                self.last_nav_time = current_time_ms
                if value < 0: # Up
                    self.move_focus(-1)
                else: # Down
                    self.move_focus(1)

    def handle_hat_motion(self, event, current_time_ms):
        # D-pad (hat 0) movement
        x, y = event.value
        if y != 0 and current_time_ms - self.last_nav_time > self.NAV_DEBOUNCE_MS:
            self.last_nav_time = current_time_ms
            self.move_focus(-y) # y is 1 (down) or -1 (up)

    def handle_button_press(self, event):
        button = event.button
        
        # A button (confirm action) - Assuming button 0 (Cross/X on some controllers)
        if button == 0:
            self.activate_focus()

        # B button (back action) - Assuming button 1 (Circle/C on some controllers)
        elif button == 1:
            # Simple back logic: go back to the MainMenuFrame if not there
            current_frame_name = self.current_frame.__class__.__name__
            if current_frame_name == 'GamesListFrame':
                self.show_frame('MainMenuFrame')
            elif current_frame_name == 'ControllerRemapperFrame':
                # The remapper frame should handle its own back/save logic
                # For now, we'll assume the Save & Return button is the only way out
                pass 
            elif current_frame_name != 'MainMenuFrame':
                self.show_frame('MainMenuFrame')

        # Shoulder buttons for quick frame navigation
        if button in self.SHOULDER_BUTTONS:
            self.held_shoulder_buttons.add(button)
            # Example: R1 + L1 to quit
            if 4 in self.held_shoulder_buttons and 5 in self.held_shoulder_buttons:
                self.root.quit()
        
        # Stick buttons (e.g., L3/R3) for fast console switching if needed
        # elif button in self.STICK_BUTTONS:
        #     # Quick console switch logic could go here
        #     pass

    def handle_button_release(self, event):
        button = event.button
        if button in self.held_shoulder_buttons:
            self.held_shoulder_buttons.discard(button)

    def launch_game(self, game_data):
        """
        Launches the game using the RetroArch core and file path.
        """
        RETROARCH_BIN = "retroarch"
        
        # Construct the command
        command = [
            RETROARCH_BIN,
            '-L', game_data['core'], 
            game_data['path']
            # '-f' # Uncomment for fullscreen
        ]

        print(f"Executing command: {' '.join(command)}")
        
        try:
            # Hide the GUI window before launching the game
            self.root.withdraw() 
            
            # Use subprocess.run to block until the game exits
            subprocess.run(command, check=True)
            
            # Show the GUI window again after the game exits
            self.root.deiconify()
            
        except FileNotFoundError:
            print("Error: RetroArch executable not found. Please ensure it is installed and in your PATH.")
            # Use messagebox.showerror if this were a production app
            # messagebox.showerror("Error", "RetroArch executable not found.")
            self.root.deiconify()
        except subprocess.CalledProcessError as e:
            print(f"Error launching game: {e}")
            # messagebox.showerror("Error", f"Game failed to launch: {e}")
            self.root.deiconify()
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            # messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.root.deiconify()

    # --- END: Game Launch Methods ---


if __name__ == '__main__':
    # This block is for testing only, not part of the main application flow
    # It assumes the existence of other frames like MainMenuFrame and GamesListFrame
    pass