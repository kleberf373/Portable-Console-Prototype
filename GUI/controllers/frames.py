import tkinter as tk
from tkinter import ttk, Canvas, messagebox
import os
from .remapper_gui import ControllerRemapperFrame # Remapper is used inside SettingsFrame

# List of common ROM extensions for the GamesListFrame logic
ROM_EXTENSIONS = ('.smc', '.gb', '.gbc', '.gba', '.gen', '.md', '.smd', '.iso', '.cue', '.bin', '.ps1', '.sfc')

class BaseFrame(ttk.Frame):
    """Base class for all application frames."""
    def __init__(self, parent, controller, name):
        ttk.Frame.__init__(self, parent, style='Main.TFrame')
        self.controller = controller
        self.name = name
        self.navigable_buttons = []

    def get_navigable_widgets(self):
        """Returns the list of widgets available for D-pad navigation."""
        # Note: If the frame contains a canvas/scrollbar (like GamesListFrame), 
        # this will be the buttons *inside* the scrollable area.
        return self.navigable_buttons

    def on_show(self):
        """Method called when the frame is brought to the front."""
        # Used for refreshing data, like the game list
        pass


class MainMenuFrame(BaseFrame):
    """The main application menu with options for Games, Settings, and Quit."""
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "MainMenuFrame")
        
        # Header
        ttk.Label(self, text="Portable Console Menu", font=controller.big_font, 
                  background='#2c3e50', foreground='white', padding=20).pack(pady=(50, 20), padx=50, fill="x")

        # --- 1. Container for Console Buttons (The main horizontal list) ---
        self.console_container = ttk.Frame(self, style='Main.TFrame') 
        self.console_container.pack(pady=20, padx=50, fill="x")

        # --- 2. Container for Settings/Quit Buttons (Place these below the console buttons) ---
        # *** ADD THIS BLOCK ***
        self.button_container = ttk.Frame(self, style='Main.TFrame') 
        self.button_container.pack(pady=20, padx=50, fill="x")
        
        # --- 3. Create Settings Button (Uses the new self.button_container) ---
        self.settings_btn = ttk.Button(self.button_container, text="Settings (Mapper)",
                                       command=lambda: controller.show_frame("ControllerRemapperFrame"),
                                       style='Small.TButton')
        self.settings_btn.pack(side=tk.LEFT, padx=10, pady=10)

        # You should also add the Quit button here, using self.button_container:
        self.quit_btn = ttk.Button(self.button_container, text="Quit Application",
                                   command=controller.root.quit, # or controller.quit_app
                                   style='Small.TButton')
        self.quit_btn.pack(side=tk.LEFT, padx=10, pady=10)


        # --- 4. Call Generation (Must be last) ---
        # Initialize navigable buttons list with the Settings/Remapper button(s)
        self.navigable_buttons = [self.settings_btn, self.quit_btn]
        
        # Now call the method to dynamically generate the console buttons
        self.generate_console_buttons() 

    def generate_console_buttons(self):
        for widget in self.console_container.winfo_children():
            widget.destroy()
        
        # ### NEW: Clear and repopulate the console buttons in the navigation list ###
        # We keep the remapper button and add the console buttons after it.
        self.navigable_buttons = self.navigable_buttons[:1]

        consoles = self.controller.games_data.keys() # <--- Gets the console names (keys)
        if not consoles:
            ttk.Label(self.console_container, text="No consoles found in games.json.").pack()
            return
            
        for console_name in consoles:
            btn = ttk.Button(self.console_container, text=console_name, 
                       command=lambda c=console_name: self.controller.show_frame("GameListFrame", console_name=c),
                       style='Small.TButton')
            btn.pack(side=tk.LEFT, padx=10, pady=10)
            self.navigable_buttons.append(btn)

class GamesListFrame(BaseFrame):
    """Displays a list of consoles/platforms based on available games."""
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "GamesListFrame")
        self.console_name = None
        self.header_label = ttk.Label(self, text="Select Console", 
                                      font=controller.big_font, background='#34495e', 
                                      foreground='white', padding=15)
        self.header_label.pack(pady=(20, 10), padx=50, fill="x")

        # --- Scrollable Area Setup ---
        # 1. Create a Canvas that takes up the main space
        self.canvas = Canvas(self, background='#34495e', bd=0, highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True, padx=50)

        # 2. Create the scrollbar and link it
        v_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        v_scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        # 3. Create the list frame (content container inside the canvas)
        self.list_frame = ttk.Frame(self.canvas, style='Main.TFrame')
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw", tags="self.list_frame")

        # Ensure the list frame resizes with the canvas/window
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all"),
            width=e.width # Adjust canvas width to match frame width
        ))
        
        # Initial call to populate list frame when data is ready
        # REMOVED: self.cget("state") == "normal"
        # The on_show method is a more appropriate place for this logic, 
        # but for initial load, this simplified binding works:
        self.bind("<Map>", lambda e: self.generate_console_list() if not self.navigable_buttons else None)
        # --- End Scrollable Area Setup ---


        # Back Button
        back_btn = ttk.Button(self, text="← Back to Menu",
                   command=lambda: controller.show_frame("MainMenuFrame"), 
                   style='Small.TButton')
        back_btn.pack(pady=20, padx=50, fill="x")
        self.back_button = back_btn
        self.navigable_buttons.append(self.back_button) # Add back button to navigation list

    def on_show(self):
        """Called when games list is shown. Ensures data is fresh."""
        self.generate_console_list()

    def generate_console_list(self):
        """Populates the list with console buttons."""
        # Clear existing widgets, except the back button which is outside the scroll frame
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        # Clear navigation list, keeping only the back button at the end
        self.navigable_buttons = [self.back_button] 
        
        console_names = sorted(self.controller.games_data.keys())
        
        if not console_names:
            ttk.Label(self.list_frame, text="No games found.", 
                      background='#34495e', foreground='white', padding=20).pack(pady=20)
            return

        for console in console_names:
            btn = ttk.Button(self.list_frame, text=console, 
                       command=lambda c=console: self.generate_game_list(c),
                       style='Small.TButton')
            btn.pack(fill='x', pady=5, padx=10)
            self.navigable_buttons.insert(len(self.navigable_buttons) - 1, btn) # Insert before the back button
            
        # Must reconfigure the canvas scroll region after adding widgets
        self.list_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def generate_game_list(self, console_name):
        """Switches the view to show games for the selected console."""
        
        # Clear list frame
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        # Update header
        self.console_name = console_name
        self.header_label.config(text=f"Games - {console_name}")
        
        # Change the back button command to return to console list
        self.back_button.config(text="← Back to Consoles", command=lambda: self.generate_console_list())
        
        # Clear navigation list, keeping only the updated back button at the end
        self.navigable_buttons = [self.back_button] 

        games = self.controller.games_data.get(console_name, [])
        if not games:
            ttk.Label(self.list_frame, text="No games available for this console.", 
                      background='#34495e', foreground='white', padding=20).pack(pady=20)
            return
            
        for game in games:
            btn = ttk.Button(self.list_frame, text=game['name'], 
                       command=lambda g=game: self.controller.launch_game(g),
                       style='Small.TButton')
            btn.pack(fill='x', pady=5, padx=10)
            self.navigable_buttons.insert(len(self.navigable_buttons) - 1, btn) # Insert before the back button

        # Must reconfigure the canvas scroll region after adding widgets
        self.list_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
class SettingsFrame(BaseFrame):
    """Container for system settings and the Controller Remapper."""
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "SettingsFrame")

        ttk.Label(self, text="Settings", font=controller.big_font, 
                  background='#2c3e50', foreground='white', padding=20).pack(pady=(50, 20), padx=50, fill="x")

        # Embed the ControllerRemapperFrame
        # Note: ControllerRemapperFrame handles its own save/return, but we pass the controller for navigation
        self.remapper = ControllerRemapperFrame(self, controller)
        self.remapper.pack(fill="both", expand=True, padx=50, pady=10)

        # ControllerRemapperFrame already includes a button that calls save_and_return, 
        # which uses controller.show_frame("MainMenuFrame"). 
        # We don't need a separate back button here unless we add more settings.
        
        # Expose the remapper's buttons for navigation (e.g., the key buttons and the Save button)
        self.navigable_buttons = self.remapper.get_navigable_widgets()

    def on_show(self):
        """Called when settings frame is shown. Refreshes the remapper's view."""
        self.remapper.update_labels()


class PlaceholderFrame(BaseFrame):
    """A generic placeholder frame for future expansion."""
    def __init__(self, parent, controller):
        super().__init__(parent, controller, "PlaceholderFrame")
        ttk.Label(self, text="Future Content Here", font=controller.big_font).pack(pady=100)
        
        back_btn = ttk.Button(self, text="← Back to Menu",
                   command=lambda: controller.show_frame("MainMenuFrame"), 
                   style='Small.TButton')
        back_btn.pack(pady=20)
        self.navigable_buttons.append(back_btn)