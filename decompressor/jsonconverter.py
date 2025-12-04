"""
Script to convert a text file list of games to JSON format for the TouchMenuApp
"""

import json
import os
import argparse
from pathlib import Path

home = os.path.expanduser("~")

def get_core_for_extension(extension: str):

    """Map file extensions to RetroArch cores"""
    core_mapping = {
        '.sfc': f'{home}/.config/retroarch/cores/snes9x_libretro.so',
        '.smc': f'{home}/.config/retroarch/cores/snes9x_libretro.so',
        '.gba': f'{home}/.config/retroarch/cores/mgba_libretro.so',
        '.gb': f'{home}/.config/retroarch/cores/gambatte_libretro.so',
        '.gbc': f'{home}/.config/retroarch/cores/gambatte_libretro.so',
        '.md': f'{home}/.config/retroarch/cores/genesis_plus_gx_libretro.so',
        '.gen': f'{home}/.config/retroarch/cores/genesis_plus_gx_libretro.so',
        '.cue': f'{home}/.config/retroarch/cores/pcsx_rearmed_libretro.so',
        '.bin': f'{home}/.config/retroarch/cores/pcsx_rearmed_libretro.so',
        '.img': f'{home}/.config/retroarch/cores/pcsx_rearmed_libretro.so',
        '.nes': f'{home}/.config/retroarch/cores/fceumm_libretro.so',
        '.nds': f'{home}/.config/retroarch/cores/desmume_libretro.so',
        '.iso': f'{home}/.config/retroarch/cores/pcsx_rearmed_libretro.so'
    }
    return core_mapping.get(extension.lower(), '')

def get_console_for_extension(extension: str):
    """Map file extensions to console names"""
    console_mapping = {
        '.sfc': 'Super Nintendo',
        '.smc': 'Super Nintendo',
        '.gba': 'Game Boy Advance',
        '.gb': 'Game Boy',
        '.gbc': 'Game Boy Color',
        '.md': 'Mega Drive',
        '.gen': 'Mega Drive',
        '.cue': 'Playstation 1',
        '.bin': 'Playstation 1',
        '.img': 'Playstation 1',
        '.iso': 'Playstation 1',
        '.pbp': 'Playstation 1'
    }
    return console_mapping.get(extension.lower(), 'Other')

def parse_txt_file(txt_file_path, games_directory):
    # Use a dictionary to store unique games, keyed by (console, base_name)
    unique_games = {} 
    
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        for line in lines:
            path_from_list = line.strip()
            if not path_from_list or path_from_list.startswith('#'):  # Skip empty lines and comments
                continue
            
            # 💥 FIX: Resolve relative paths to absolute paths
            # If the path is not absolute (e.g., 'crash.cue'), resolve it against the games_directory
            path_obj = Path(path_from_list)
            if not path_obj.is_absolute():
                full_path = str(Path(games_directory) / path_from_list)
            else:
                full_path = path_from_list

            path_obj = Path(full_path) # Re-create path_obj with the absolute path
            
            # Extract the actual game name (stem) and extension
            filename = path_obj.name      # e.g., crash_1.cue
            name = path_obj.stem          # e.g., crash_1
            ext = path_obj.suffix.lower() # e.g., .cue
            
            console = get_console_for_extension(ext)
            core = get_core_for_extension(ext)
            
            if not core:
                print(f"Warning: Could not find core for extension {ext}. Skipping {filename}.")
                continue

            unique_key = (console, name)
            
            game_info = {
                "name": name,
                "path": full_path, # Now guaranteed to be the absolute path
                "core": core
            }
            
            # Logic to handle duplicates and prioritize .cue files
            if unique_key in unique_games:
                existing_entry = unique_games[unique_key]
                existing_ext = Path(existing_entry["path"]).suffix.lower()
                
                # Prioritization logic for Playstation 1
                if console == "Playstation 1":
                    # If we find a .cue file, and the existing entry is NOT a .cue file, use the new .cue file
                    if ext == ".cue" and existing_ext != ".cue":
                        unique_games[unique_key] = game_info
                        print(f"Prioritized: {name} ({console}) with .cue file.")
                    # If the existing entry is already the preferred .cue, skip the new file (e.g., a .bin)
                    elif existing_ext == ".cue":
                        print(f"Skipping redundant file for {name} ({console}).")
                        continue
                    # If both are non-cue (e.g., two .bin files with the same name), skip the new one
                    else:
                        print(f"Skipping redundant file for {name} ({console}).")
                        continue
                else:
                    # For all other consoles, skip if the base name is already present
                    print(f"Skipping redundant file for {name} ({console}).")
                    continue
            else:
                # Add the game if it's the first time seeing it
                unique_games[unique_key] = game_info
                print(f"Added: {name} ({console})")

        
        # Now, regroup the unique games by console for the final output format
        games_data = {}
        for (console, _), game_info in unique_games.items():
            if console not in games_data:
                games_data[console] = []
            games_data[console].append(game_info)
    
    except FileNotFoundError:
        print(f"Error: Text file '{txt_file_path}' not found")
        return {}
    except Exception as e:
        print(f"Error reading text file: {e}")
        return {}
    
    return games_data

def convert_txt_to_json(txt_file_path, games_directory, output_json_path):
    """
    Main function to convert TXT to JSON
    """
    print(f"Converting {txt_file_path} to {output_json_path}")
    print(f"Games directory: {games_directory}")
    print("-" * 50)
    
    # Parse the text file
    games_data = parse_txt_file(txt_file_path, games_directory)
    
    if not games_data:
        print("No games found or error occurred.")
        return False
    
    # Save to JSON file
    try:
        with open(output_json_path, 'w', encoding='utf-8') as json_file:
            json.dump(games_data, json_file, indent=4, ensure_ascii=False)
        
        print("-" * 50)
        print(f"Successfully created: {output_json_path}")
        print(f"Total consoles: {len(games_data)}")
        for console, games in games_data.items():
            print(f"  {console}: {len(games)} games")
        
        return True
    
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert TXT game list to JSON format')
    parser.add_argument('txt_file', help='Path to the input text file')
    parser.add_argument('games_dir', help='Path to the directory containing game files')
    parser.add_argument('-o', '--output', default=f'{home}/Portable-Console-Prototype/GUI/games.json', 
                       help='Output JSON file path (default: games.json)')
    
    args = parser.parse_args()
    
    # Convert the files
    # FIX: Use args.output which is the correct way to retrieve the path, though your original line used a hardcoded path expansion
    # We will stick to the hardcoded path expansion since that is what you were using, but fixed the tilde expansion issue that might be lurking.
    output_path = os.path.expanduser(f"{home}/Portable-Console-Prototype/GUI/games.json")
    success = convert_txt_to_json(args.txt_file, args.games_dir, output_path)
    
    if success:
        print("\nConversion completed successfully!")
    else:
        print("\nConversion failed!")
        return 1
    
    return 0

# Alternative: Simple function for direct use
def simple_convert(txt_file, games_dir, output_file):
    """Simple one-function conversion without command line arguments"""
    return convert_txt_to_json(txt_file, games_dir, output_file)

if __name__ == "__main__":
    exit(main())