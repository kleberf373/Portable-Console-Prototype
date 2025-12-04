import tkinter as tk
from tkinter import ttk, Canvas
from tkinter.font import Font
import os
import subprocess
import json
import pygame
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
        self.style.configure('Small.TButton', font=self.big_font, padding=30, relief='flat', foreground='white')
        self.style.map('Small.TButton', background=[('active', '#2980b9'), ('pressed', '#1c638e')])
        
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

        self.load_console_images()

        
    def load_console_images(self): 
        self.console_images = {}  

        ICON_SIZE = (280, 90)

        image_paths = {"Super Nintendo": f"{os.path.dirname(os.path.abspath(__file__))}/../assets/supernintendo.png",
        "Mega Drive": f"{os.path.dirname(os.path.abspath(__file__))}/../assets/MegaDrive.png",
        "Game Boy": f"{os.path.dirname(os.path.abspath(__file__))}/../assets/gameboy.png",
        "Game Boy Advance": f"{os.path.dirname(os.path.abspath(__file__))}/../assets/gameboy_advance.png",
        "Playstation 1": f"{os.path.dirname(os.path.abspath(__file__))}/../assets/playstation.png",
        }
        for console, path in image_paths.items():
            if isinstance(path, str) and os.path.exists(path):
                img = Image.open(path).resize(ICON_SIZE, Image.LANCZOS)
                self.console_images[console] = ImageTk.PhotoImage(img)
            else:
                print(f"Erro: caminho inválido ou tipo incorreto para {console}: {path}")


        self.games_data = {}
        self.load_games_data("games.json")
        
        self.setup_styles()
        
        container = ttk.Frame(self.root, style='Main.TFrame')
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainMenuFrame, GameListFrame, ControllerRemapperFrame):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MainMenuFrame")
        self._initialize_gamepad_listener()

    # ### NEW: Method to register which buttons can be navigated on the current screen ###
    def register_navigable_widgets(self, widgets: list):
        """Sets the list of widgets for controller navigation on the current frame."""
        self.navigable_widgets = widgets
        # If there are any navigable widgets, set focus to the first one
        if self.navigable_widgets:
            self._update_focus(old_index=-1, new_index=0)
        else:
            self.current_focus_index = -1
    # ### NEW: END ###
            
    def show_frame(self, page_name, console_name=None):
        """Raises the requested frame to the top and prepares it for navigation."""
        frame = self.frames[page_name]
        if page_name == "GameListFrame" and console_name:
            frame.set_console(console_name)
            frame.generate_game_list()
        
        frame.tkraise()
        # ### NEW: After showing a frame, register its buttons for navigation ###
        # We call a method on the frame itself to get its buttons.
        if hasattr(frame, 'get_navigable_widgets'):
            self.register_navigable_widgets(frame.get_navigable_widgets())
        else:
            self.register_navigable_widgets([]) # Clear navigation for this frame
    # ### NEW: END ###

    def _initialize_gamepad_listener(self):
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"✅ Gamepad '{self.joystick.get_name()}' connected.")
            self._poll_gamepad_events()
        else:
            print("⚠️ No gamepad connected.")

    def _poll_gamepad_events(self):
        """Checks for pygame events for both shortcuts and menu navigation."""
        current_time = pygame.time.get_ticks()

        for event in pygame.event.get():
            # --- Return-to-home shortcut logic (unchanged) ---
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in self.SHOULDER_BUTTONS:
                    self.held_shoulder_buttons.add(event.button)
                if event.button in self.STICK_BUTTONS and self.SHOULDER_BUTTONS.issubset(self.held_shoulder_buttons):
                    self.show_frame("MainMenuFrame")
                
                # ### NEW: Handle "Select" button press (X button is usually button 0) ###
                if event.button == 0 and self.current_focus_index != -1:
                    focused_widget = self.navigable_widgets[self.current_focus_index]
                    print(f"Controller selected: {focused_widget.cget('text')}")
                    focused_widget.invoke() # Programmatically "click" the button
                # ### NEW: END ###

            elif event.type == pygame.JOYBUTTONUP:
                if event.button in self.SHOULDER_BUTTONS:
                    self.held_shoulder_buttons.discard(event.button)
            
            # ### NEW: Handle D-Pad navigation ###
            elif event.type == pygame.JOYHATMOTION:
                # event.value is a tuple (x, y); e.g., (0, 1) is UP, (0, -1) is DOWN
                hat_x, hat_y = event.value
                # Debounce to prevent rapid scrolling
                if current_time - self.last_nav_time > self.NAV_DEBOUNCE_MS:
                    if hat_y == 1 or hat_x == -1: # D-Pad UP
                        self._navigate_menu(-1)
                        self.last_nav_time = current_time
                    elif hat_y == -1 or hat_x == 1: # D-Pad DOWN
                        self._navigate_menu(1)
                        self.last_nav_time = current_time
            # ### NEW: END ###

        self.root.after(20, self._poll_gamepad_events) # Poll more frequently for responsiveness

    # ### NEW: Methods for managing focus ###
    def _navigate_menu(self, direction: int):
        """Move the focus up or down in the widget list."""
        if not self.navigable_widgets:
            return

        # Calculate the new index, wrapping around if necessary
        old_index = self.current_focus_index
        new_index = (old_index + direction) % len(self.navigable_widgets)
        
        self._update_focus(old_index, new_index)
        
        # Garantir que o widget focado esteja visível, especialmente em listas longas (GameListFrame)
        new_widget = self.navigable_widgets[new_index]
        current_frame = new_widget.winfo_toplevel().winfo_children()[0].winfo_children()[0]

        # Se o frame atual for GameListFrame e o widget focado estiver no canvas...
        if isinstance(current_frame, GameListFrame) and new_widget != current_frame.back_button:
            current_frame.scroll_to_widget(new_widget)

    def _update_focus(self, old_index: int, new_index: int):
        """Update the visual style of the buttons to show focus."""
        # 1. Remove focus from the old widget, if it exists
        if old_index != -1 and old_index < len(self.navigable_widgets):
            widget = self.navigable_widgets[old_index]
            
            # ### CORREÇÃO DE RESTAURAÇÃO DE FOCO (Baseado no tipo) ###
            if isinstance(widget, ttk.Label):
                # Se for Label, restaura para o estilo base do Remapper Label
                original_style = 'Remapper.TLabel' 
            else: # Deve ser um Button
                text = widget.cget('text')
                
                if "CONFIGURE" in text:
                    original_style = 'Remapper.TButton'
                elif "Back to Consoles" in text or not text: 
                     original_style = 'Small.TButton'
                else: 
                    original_style = 'Game.TButton'

            widget.configure(style=original_style)

        # 2. Apply focus to the new widget
        if new_index != -1 and new_index < len(self.navigable_widgets):
            widget = self.navigable_widgets[new_index]
            
            # ### CORREÇÃO CRÍTICA: USAR O ESTILO CORRETO (Baseado no tipo) ###
            if isinstance(widget, ttk.Button):
                focus_style = 'Focus.TButton'
            elif isinstance(widget, ttk.Label):
                # Aplicar o estilo específico de Label para manter a geometria
                focus_style = 'Focus.TLabel' 
            else:
                focus_style = 'Focus.TButton' # Fallback
                
            widget.configure(style=focus_style)
            self.current_focus_index = new_index
            
    def setup_styles(self):
        self.big_font = Font(family='Helvetica', size=24, weight='bold')
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('Main.TFrame', background="dark green")
        self.style.configure('Small.TButton', padding=15, relief='raised', foreground='black')
        self.style.configure('Game.TButton', font=('Helvetica', 20, 'bold'), padding=20, background='white', foreground='black', relief='raised')
        self.style.map('Small.TButton', background=[('active', "#2ad6d6")])
        self.style.map('Custom.TButton', background=[('active', 'white'),('pressed','light green')])
        self.style.configure('Remapper.TButton', font=('Helvetica', 18, 'bold'), foreground='black',
            background='white', padding=(25, 12), relief='raised', borderwidth=5)
        self.style.map('Remapper.TButton', background=[('active', '#2ad6d6')])
        
        # ### NEW: Style for the visually focused button ###
        self.style.configure(
            'Game.TButton', 
            font=('Helvetica', 18, 'bold'), # Ajustado para font 18 (igual ao Focus.TButton)
            padding=(25, 12), 
            background='white', 
            foreground='black', 
            relief='raised',
            borderwidth=5 
        )

        self.style.configure(
            'Remapper.TLabel', 
            font=('Helvetica', 16), 
            background='dark green', 
            foreground='white',
            relief='raised', 
            borderwidth=2,
            padding=(5, 5))
        
        self.style.configure(
            'Focus.TLabel', 
            font=('Helvetica', 16), 
            background='#52D171', # Cor de Foco
            foreground='black',
            relief='raised', 
            borderwidth=2,
            padding=(5, 5)
        )
        
    def load_games_data(self, json_path):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        full_path = os.path.join(base_dir, json_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as f:
                    self.games_data = json.load(f)
            except Exception as e:
                print(f"Error reading games.json: {e}")
        else:
            print(f"JSON file not found at: {full_path}")

    def launch_game(self, game):
        print(f"Launching: {game['name']}")
        core_path, rom_path = game.get("core"), game.get("path")
        try:
            command = ["retroarch"]
            if core_path and os.path.exists(core_path):
                command.extend(["-L", core_path])
            command.append(rom_path)
            subprocess.run(command)
        except Exception as e:
            print(f"Error launching game: {e}")

class MainMenuFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='Main.TFrame')
        self.controller = controller
        # ### NEW: Store buttons for navigation ###
        self.navigable_buttons = []     

        ttk.Label(self, text="Select Console", 
                  font=controller.big_font, 
                  foreground='green', 
                  padding=(25, 12), 
                  relief= 'flat', 
                  borderwidth=5,).pack(pady=40, padx=20)
        
        Remapper_btn = ttk.Button(self, text="GAMEPAD CONFIGURE ⌨️",
                   command=lambda: controller.show_frame("ControllerRemapperFrame"), 
                   style='Remapper.TButton')
        Remapper_btn.pack(pady=20, padx=50)
        self.navigable_buttons.append(Remapper_btn)

        # container dos botões dos consoles
        self.console_container = ttk.Frame(self, style="Console.TFrame")
        self.console_container.pack(fill="both", pady=20)

        self.console_container = ttk.Frame(self, style='Main.TFrame')
        self.console_container.pack(pady=20)
        
        self.generate_console_buttons()
    

    # ### NEW: Expose the list of buttons to the main controller ###
    def get_navigable_widgets(self):
        return self.navigable_buttons

    def generate_console_buttons(self):
        for widget in self.console_container.winfo_children():
            widget.destroy()

        self.navigable_buttons = self.navigable_buttons[:1]

        consoles = self.controller.games_data.keys()
        if not consoles:
            ttk.Label(self.console_container, text="No consoles found in games.json.").pack()
            return

        for console_name in consoles:
            image = self.controller.console_images.get(console_name)

            btn = ttk.Button(
                self.console_container,
                image=image if image else None,
                text="" if image else console_name,
                command=lambda c=console_name: self.controller.show_frame("GameListFrame", console_name=c),
                style='Small.TButton'
            )

            btn.pack(fill='x', pady=10)
            self.navigable_buttons.append(btn)


class GameListFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style='Main.TFrame')
        self.controller = controller
        self.console_name = None
        self.navigable_buttons = []
        
        # 1. Header (Top Row)
        self.header_label = ttk.Label(self, text="", font=controller.big_font)
        self.header_label.grid(row=0, column=0, columnspan=2, pady=10) # <-- USE GRID
        
        # 2. Setup Canvas and Scrollbar (Middle Row)
        self.canvas = tk.Canvas(self, bg='dark green', highlightthickness=0) # <-- CORRECT PARENT: self
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview) # <-- CORRECT PARENT: self

        self.canvas.grid(row=1, column=0, sticky="nsew", padx=50) # <-- USE GRID
        self.scrollbar.grid(row=1, column=1, sticky="ns") # <-- USE GRID
        
        # 3. Inner Frame for Buttons inside the Canvas
        # All game buttons will be packed inside this frame
        self.list_frame = ttk.Frame(self.canvas, style='Main.TFrame')
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        # Configure Canvas scrolling
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Altere o lambda para usar o método bbox na lista de quadros
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all"),
            width=self.canvas.winfo_width()
        ))
        
        # Otimização: Adicione uma reconfiguração do scrollregion inicial
        self.list_frame.bind("<Map>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        ))
        
        # 4. Back Button (Bottom Row)
        back_btn = ttk.Button(self, text="← Back to Consoles",
                   command=lambda: controller.show_frame("MainMenuFrame"), 
                   style='Small.TButton')
        back_btn.grid(row=2, column=0, columnspan=2, pady=20) # <-- USE GRID
        self.back_button = back_btn

        # Configure weights for the grid to make the canvas expand
        self.grid_rowconfigure(1, weight=1) # The Canvas row gets the extra space
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0) 
        
    # ### NEW: Expose the list of buttons to the main controller ###
    def get_navigable_widgets(self):
        return self.navigable_buttons

    def set_console(self, console_name):
        self.console_name = console_name
        self.header_label.config(foreground='green', borderwidth=5, padding=(25, 12), text=f"Games - {console_name}")

    def generate_game_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        
        # ### NEW: Clear and repopulate the game buttons in the navigation list ###
        self.navigable_buttons.clear()
        
        if not self.console_name: return

        for game in self.controller.games_data.get(self.console_name, []):
            btn = ttk.Button(self.list_frame, text=game['name'], 
                       command=lambda g=game: self.controller.launch_game(g),
                       style='Game.TButton', )
            btn.pack(fill='x', pady=5)
            self.navigable_buttons.append(btn)
        
        # Add the back button to the end of the navigation list
        self.navigable_buttons.append(self.back_button)
    
    def scroll_to_widget(self, widget):
        """Scrolls the canvas to ensure the given widget is visible."""
        # 1. Obter as coordenadas do widget (relativas ao list_frame)
        self.list_frame.update_idletasks()
        widget_y1 = widget.winfo_y()
        widget_height = widget.winfo_height()
        widget_y2 = widget_y1 + widget_height
        
        # Obter a altura total do frame interno (list_frame)
        list_frame_height = self.list_frame.winfo_height()
        if list_frame_height == 0:
            return

        # 2. Obter a área de visualização atual do canvas
        canvas_height = self.canvas.winfo_height()
        
        # A posição 0 (topo) da rolagem é uma fração. O denominador deve ser list_frame_height
        canvas_view_start_fraction = float(self.canvas.yview()[0])
        # Converter a fração da vista atual para pixels (referente ao list_frame)
        canvas_view_start = canvas_view_start_fraction * list_frame_height
        canvas_view_end = canvas_view_start + canvas_height

        # 3. Calcular a rolagem necessária
        # Se o widget estiver acima da vista, mova o topo do widget para o topo da vista
        if widget_y1 < canvas_view_start:
            # Rolar para que o topo do widget fique no topo da vista.
            # Adicione uma margem (padding) para que não fique colado no topo.
            target_fraction = (widget_y1 - widget_height) / list_frame_height # Desloca o topo do widget um pouco acima da vista
            self.canvas.yview_moveto(max(0.0, target_fraction))
        
        # Se o widget estiver abaixo da vista, mova o fundo do widget para o fundo da vista
        elif widget_y2 > canvas_view_end:
            # Rolar para que o fundo do widget fique no fundo da vista.
            # Adicione uma margem (padding) para que não fique colado no fundo.
            target_fraction = (widget_y2 - canvas_height + widget_height) / list_frame_height # Desloca o fundo do widget um pouco abaixo da vista
            self.canvas.yview_moveto(min(1.0, target_fraction))