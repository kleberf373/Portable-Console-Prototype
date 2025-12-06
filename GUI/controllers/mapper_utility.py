import os
import sys

# Path to map.txt: Assumes it's in the project root (two directories up from GUI/controllers)
MAP_FILE = os.path.join(os.path.abspath("."), "Portable-Console-Prototype", "GUI","map.txt")

# ### NEW: Default Mapping Content ###
DEFAULT_MAPPINGS = """\
# Portable Console Controller Mappings
#
# Button Mappings (Face Buttons)
0=KEY_X          # Cross (A button) -> X
1=KEY_C          # Circle (B button) -> C
2=KEY_S          # Square (Y button) -> S
3=KEY_D          # Triangle (X button) -> D

# Shoulder Buttons (Top)
4=KEY_Q          # L1 -> Q
5=KEY_W          # R1 -> W
6=KEY_A          # L2 -> A
7=KEY_Z          # R2 -> Z

# Center Buttons
8=KEY_LEFTSHIFT  # Select -> Left Shift
9=KEY_ENTER      # Start -> Enter

# Stick Clicks
10=KEY_1         # L3 (Left Stick Click) -> 1
11=KEY_2         # R3 (Right Stick Click) -> 2

# D-Pad
7_-1=KEY_UP      # D-Pad UP
7_1=KEY_DOWN     # D-Pad DOWN
6_-1=KEY_LEFT    # D-Pad LEFT
6_1=KEY_RIGHT    # D-Pad RIGHT

# Analog Sticks (Mapped to standard WASD/IJKL for simple use)
1_-1=KEY_W       # L-Stick UP
1_1=KEY_S        # L-Stick DOWN
0_-1=KEY_A       # L-Stick LEFT
0_1=KEY_D        # L-Stick RIGHT
3_-1=KEY_I       # R-Stick UP
3_1=KEY_K        # R-Stick DOWN
2_-1=KEY_J       # R-Stick LEFT
2_1=KEY_L        # R-Stick RIGHT
"""

class GamepadMapperUtility:
    """
    Utility class to read, modify, and write the custom map.txt file.
    """
    def __init__(self, file_path=MAP_FILE):
        self.file_path = file_path
        self.mappings_data = {}
        self.comments_data = {} # ### CHANGE: Use dict for easier lookup
        self.line_order = []
        self._comment_counter = 0
        print(f"Mapper Utility initialized. Using map.txt at: {self.file_path}")

    def _parse_line(self, line: str):
        line = line.strip()
        if not line or line.startswith('#'):
            return None
        if '=' in line:
            parts = line.split('=', 1)
            map_key = parts[0].strip()
            key_code = parts[1].split('#')[0].strip()
            if map_key and key_code:
                # Mapping keys are either numbers (buttons) or AXIS_DIR (e.g., 7_-1 for D-Pad Up)
                if map_key.isdigit() or ('_' in map_key and map_key.split('_')[0].isdigit()):
                    return map_key, key_code
        return None

    def read_mappings(self):
        """Reads the map.txt file and populates the internal data structures."""
        if not os.path.exists(self.file_path):
            print(f"Warning: map.txt not found at {self.file_path}. Creating a default one.")
            # ### NEW: Create file with default content ###
            try:
                with open(self.file_path, 'w') as f:
                    f.write(DEFAULT_MAPPINGS)
                # Re-read the newly created file to populate the internal data
                with open(self.file_path, 'r') as f:
                    for line in f:
                        map_result = self._parse_line(line)
                        if map_result:
                            map_key, key_code = map_result
                            self.mappings_data[map_key] = key_code
                            self.line_order.append(('mapping', map_key))
                        else:
                            comment_key = f"c{self._comment_counter}"
                            self.comments_data[comment_key] = line.rstrip('\n')
                            self.line_order.append(('comment', comment_key))
                            self._comment_counter += 1
                return True
            except Exception as e:
                print(f"Error creating map.txt: {e}")
                return False

        with open(self.file_path, 'r') as f:
            for line in f:
                map_result = self._parse_line(line)
                if map_result:
                    map_key, key_code = map_result
                    self.mappings_data[map_key] = key_code
                    self.line_order.append(('mapping', map_key))
                else:
                    # Store as a comment, retaining the full line content
                    comment_key = f"c{self._comment_counter}"
                    self.comments_data[comment_key] = line.rstrip('\n')
                    self.line_order.append(('comment', comment_key))
                    self._comment_counter += 1
        return True

    def update_mapping(self, map_key: str, new_key_code: str):
        """Updates an existing mapping key."""
        if map_key in self.mappings_data:
            self.mappings_data[map_key] = new_key_code.strip().upper()
            return True
        else:
            # ### ADDED: Automatically add new key if missing, useful for default setup ###
            self.mappings_data[map_key] = new_key_code.strip().upper()
            self.line_order.append(('mapping', map_key))
            print(f"Info: Map key '{map_key}' not found, adding new mapping.")
            return True


    def write_mappings(self):
        """Writes the current mappings data back to the file, preserving line order and comments."""
        try:
            with open(self.file_path, 'w') as f:
                for line_type, key in self.line_order:
                    if line_type == 'mapping':
                        line = f"{key}={self.mappings_data[key]}\n"
                        # ### FIX: Pad the key code to align with comments if needed (optional formatting) ###
                        # key_code = self.mappings_data[key].ljust(15) 
                        # line = f"{key}={key_code}"
                        # f.write(line + '\n')
                        f.write(line)
                    elif line_type == 'comment':
                        line = self.comments_data[key]
                        f.write(line + '\n')
            print(f"Successfully wrote mappings to {self.file_path}")
            return True
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def get_all_mappings(self):
        """Returns the current mappings dictionary."""
        return self.mappings_data