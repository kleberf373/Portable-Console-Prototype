import tkinter as tk
from tkinter import ttk, Toplevel, messagebox
# ### CHANGE: No longer needs simpledialog
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

LINUX_KEY_CODES = [
    'KEY_ESC', 'KEY_1', 'KEY_2', 'KEY_3', 'KEY_4', 'KEY_5', 'KEY_6', 'KEY_7', 'KEY_8', 'KEY_9', 'KEY_0', 'KEY_MINUS', 'KEY_EQUAL', 'KEY_BACKSPACE',
    'KEY_TAB', 'KEY_Q', 'KEY_W', 'KEY_E', 'KEY_R', 'KEY_T', 'KEY_Y', 'KEY_U', 'KEY_I', 'KEY_O', 'KEY_P', 'KEY_LEFTBRACE', 'KEY_RIGHTBRACE', 'KEY_ENTER',
    'KEY_CAPSLOCK', 'KEY_A', 'KEY_S', 'KEY_D', 'KEY_F', 'KEY_G', 'KEY_H', 'KEY_J', 'KEY_K', 'KEY_L', 'KEY_SEMICOLON', 'KEY_APOSTROPHE', 'KEY_BACKSLASH',
    'KEY_LEFTSHIFT', 'KEY_Z', 'KEY_X', 'KEY_C', 'KEY_V', 'KEY_B', 'KEY_N', 'KEY_M', 'KEY_COMMA', 'KEY_DOT', 'KEY_SLASH', 'KEY_RIGHTSHIFT',
    'KEY_LEFTCTRL', 'KEY_LEFTALT', 'KEY_SPACE', 'KEY_RIGHTALT', 'KEY_RIGHTCTRL',
    'KEY_LEFT', 'KEY_RIGHT', 'KEY_UP', 'KEY_DOWN', 
]

# --- Keyboard Picker Dialog (No changes here) ---
class KeyboardPicker(Toplevel):
    # This class remains a Toplevel because modal dialogs are a correct use case.
    # ... (no changes needed in this class)
    """Modal window to select a new keyboard key for the mapping."""
    def __init__(self, parent, map_key_friendly):
        super().__init__(parent)
        self.transient(parent)
        self.title(f"Select Key for: {map_key_friendly}")
        self.result = None
        self.grab_set()
        self.initial_focus = self
        self.parent = parent
        self.style = ttk.Style()
        self.style.configure('Key.TButton', font=('Helvetica', 12, 'bold'), padding=10, relief='raised', borderwidth=3, background='#c0c0c0')
        self.style.map('Key.TButton', background=[('active', '#5CB85C')])
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        self.wait_window(self)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10 10 10 10", style='Main.TFrame')
        main_frame.grid(row=0, column=0, sticky="nsew")
        col, row = 0, 0
        for key_code in LINUX_KEY_CODES:
            display_text = key_code.replace('KEY_', '').replace('LEFT', 'L-').replace('RIGHT', 'R-').replace('SHIFT', 'SH').replace('CTRL', 'CR').replace('ALT', 'AL')
            width = 15 if 'SPACE' in key_code else 6 if any(k in key_code for k in ['SHIFT', 'ENTER', 'BACKSPACE']) else 3
            button = ttk.Button(main_frame, text=display_text, command=lambda kc=key_code: self.select_key(kc), width=width, style='Key.TButton')
            if key_code == 'KEY_TAB': row = 1; col = 0
            elif key_code == 'KEY_CAPSLOCK': row = 2; col = 0
            elif key_code == 'KEY_LEFTSHIFT': row = 3; col = 0
            elif key_code == 'KEY_LEFTCTRL': row = 4; col = 0
            elif key_code == 'KEY_LEFT': row = 5; col = 10 
            elif key_code == 'KEY_UP': row = 5; col = 11
            elif key_code == 'KEY_DOWN': row = 6; col = 11
            button.grid(row=row, column=col, padx=2, pady=2, sticky='ew')
            col += 1
            if col > 13 and row < 4: col = 0; row += 1
        ttk.Button(main_frame, text="Cancel", command=self.cancel, style='Key.TButton').grid(row=7, column=0, columnspan=14, pady=10)

    def select_key(self, key_code):
        self.result = key_code; self.destroy()

    def cancel(self):
        self.result = None; self.destroy()

# ### CHANGE: Renamed ControllerRemapper to ControllerRemapperFrame and made it a ttk.Frame ###
class ControllerRemapperFrame(ttk.Frame):
    """Main page for drawing the controller and managing mappings."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(style='TFrame')
        
        self.selected_key_friendly = None 
        self.mapper_utility = GamepadMapperUtility()
        self.mapper_utility.read_mappings()
        
        # ... (restante do código)
        
        self.button_labels = {}
        # ### NOVO: Lista para armazenar todos os widgets navegáveis ###
        self.navigable_widgets = [] 
        
        self.create_widgets()
        self.update_labels()
    
    # ### NOVO: Método para expor os widgets navegáveis ao TouchMenuApp ###
    def get_navigable_widgets(self):
        return self.navigable_widgets
    
    def create_widgets(self):
        """Draws the DualShock-style layout."""
        # ### CHANGE: No Toplevel methods like title() or geometry()
        main_frame = ttk.Frame(self, padding="20", style='TFrame')
        main_frame.pack(fill="both", expand=True)
        # (The rest of the widget creation logic is identical)
        ttk.Label(main_frame, text="DualShock Remapper", font=('Helvetica', 20, 'bold')).grid(row=0, column=0, columnspan=5, pady=(0, 20))
        self._add_button(main_frame, 'L1 (Q)', row=1, col=0, padx=(0, 10))
        self._add_button(main_frame, 'R1 (W)', row=1, col=4, padx=(10, 0))
        self._add_button(main_frame, 'L2 (A)', row=2, col=0, padx=(0, 10))
        self._add_button(main_frame, 'R2 (Z)', row=2, col=4, padx=(10, 0))
        
        left_frame = ttk.Frame(main_frame, style='TFrame'); left_frame.grid(row=3, column=0, rowspan=3, padx=(0, 30))
        
        self._add_button(left_frame, 'D-Pad UP', row=0, col=1); self._add_button(left_frame, 'D-Pad DOWN', row=2, col=1)
        self._add_button(left_frame, 'D-Pad LEFT', row=1, col=0); self._add_button(left_frame, 'D-Pad RIGHT', row=1, col=2)

        self._add_stick_group(main_frame, 'L-Stick', 'L3 (1)', row=3, col=1)
        self._add_button(main_frame, 'Select (LSHIFT)', row=4, col=2); self._add_button(main_frame, 'Start (ENTER)', row=5, col=2)
        
        right_frame = ttk.Frame(main_frame, style='TFrame'); right_frame.grid(row=3, column=4, rowspan=3, padx=(30, 0))
        
        self._add_button(right_frame, 'Triangle (D)', row=0, col=1); self._add_button(right_frame, 'Cross (X)', row=2, col=1)
        self._add_button(right_frame, 'Square (S)', row=1, col=0); self._add_button(right_frame, 'Circle (C)', row=1, col=2)
        
        self._add_stick_group(main_frame, 'R-Stick', 'R3 (2)', row=3, col=3)
        
        footer = ttk.Frame(main_frame, style='TFrame'); footer.grid(row=6, column=0, columnspan=5, pady=30)
        
        save_btn = ttk.Button(footer, text="Save and Return", command=self.save_and_return, style='Map.TButton')
        save_btn.pack(side=tk.LEFT, padx=10)
        
        discard_btn = ttk.Button(footer, text="Discard and Return", command=lambda: self.controller.show_frame("MainMenuFrame"), style='Map.TButton')
        discard_btn.pack(side=tk.LEFT, padx=10)
        
        # ### NOVO: Adiciona os botões de ação à lista de navegação ###
        self.navigable_widgets.append(save_btn)
        self.navigable_widgets.append(discard_btn)        
        # ### CHANGE: Button commands now call the controller to switch frames
        ttk.Button(footer, text="Save and Return", command=self.save_and_return, style='Map.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(footer, text="Discard and Return", command=lambda: self.controller.show_frame("MainMenuFrame"), style='Map.TButton').pack(side=tk.LEFT, padx=10)

    def _add_button(self, parent, friendly_name, row, col, padx=5, pady=5):
        btn_frame = ttk.Frame(parent, style='TFrame'); btn_frame.grid(row=row, column=col, padx=padx, pady=pady, sticky='nsew')
        ttk.Label(btn_frame, text=friendly_name.split('(')[0].strip(), style='TLabel').pack(pady=(0, 2))
        # ### CORREÇÃO: Usar o novo estilo base para Labels do Remapper ###
        label = ttk.Label(btn_frame, text="KEY_?", cursor="hand2", style='Remapper.TLabel', relief='raised', borderwidth=2)
        label.pack(ipady=5, ipadx=5)
        label.bind("<Button-1>", lambda e, name=friendly_name: self.select_button(name))
        self.button_labels[friendly_name] = label
        
        # ### NOVO: Adiciona o Label clicável à lista de navegação ###
        self.navigable_widgets.append(label)
        
    def _add_stick_group(self, parent, stick_name, click_name, row, col):
        group_frame = ttk.Frame(parent, style='TFrame'); group_frame.grid(row=row, column=col, rowspan=3, padx=10, pady=10)
        self._add_button(group_frame, click_name, row=0, col=0, padx=0, pady=(0, 20))
        ttk.Label(group_frame, text=f"{stick_name} Axes", font=('Helvetica', 16, 'bold')).grid(row=1, column=0, columnspan=3, pady=(5, 5))
        self._add_button(group_frame, f'{stick_name} UP', row=2, col=1); self._add_button(group_frame, f'{stick_name} DOWN', row=4, col=1)
        self._add_button(group_frame, f'{stick_name} LEFT', row=3, col=0); self._add_button(group_frame, f'{stick_name} RIGHT', row=3, col=2)
        group_frame.grid_columnconfigure(1, weight=1)

    def select_button(self, friendly_name):
        if self.selected_key_friendly in self.button_labels:
            # ### CORRIGIDO: Restaura para o estilo base do Remapper ###
            self.button_labels[self.selected_key_friendly].configure(style='Remapper.TLabel')
        self.selected_key_friendly = friendly_name
        # ### CORRIGIDO: Usa o novo estilo de foco/seleção unificado ###
        self.button_labels[friendly_name].configure(style='Focus.TLabel')
        self.open_keyboard_picker(friendly_name)

    def open_keyboard_picker(self, friendly_name):
        # ... (código existente)
        if self.selected_key_friendly in self.button_labels:
            # ### CORRIGIDO: Restaura para o estilo base do Remapper ###
            self.button_labels[self.selected_key_friendly].configure(style='Remapper.TLabel')
            self.selected_key_friendly = None

    def update_labels(self):
        current_mappings = self.mapper_utility.get_all_mappings()
        for friendly_name, label in self.button_labels.items():
            map_key = MAPPING_KEYS[friendly_name]
            key_code = current_mappings.get(map_key, "KEY_???")
            display_text = key_code.replace('KEY_', '')
            label.configure(text=display_text)

    # ### CHANGE: New save method that navigates back to the main menu
    def save_and_return(self):
        """Writes changes to map.txt and returns to the main menu."""
        self.mapper_utility.write_mappings()
        messagebox.showinfo("Success", "Configuration saved to map.txt!")
        self.controller.show_frame("MainMenuFrame")