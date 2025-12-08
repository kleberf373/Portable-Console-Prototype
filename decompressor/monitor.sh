#!/bin/bash

# Configuration
DOWNLOAD_DIR="$HOME/Downloads"
EXTRACT_DIR="$HOME/Downloads/games"
DECOMPRESSOR_SCRIPT="$HOME/Portable-Console-Prototype/decompressor/decompressor.sh"
OUTPUT_FILE="$HOME/Portable-Console-Prototype/decompressor/cache.txt"
LOG_FILE="$HOME/decompression.log"
PYTHON_SCRIPT="$HOME/Portable-Console-Prototype/decompressor/jsonconverter.py"
PYTHON_SCRIPT_ARGS="$OUTPUT_FILE $EXTRACT_DIR -o $HOME/Portable-Console-Prototype/GUI/games.json"
# Add this line to the top of monitor.sh with your other configurations
USB_COPIER_SCRIPT="$HOME/Portable-Console-Prototype/decompressor/check_usb_devices.sh" 

check_usb_drives() {
    # Ensure the USB copier script is executable
    if [ ! -f "$USB_COPIER_SCRIPT" ]; then
        log_message "ERROR: USB Copier script not found at $USB_COPIER_SCRIPT"
        return 1
    fi
    if [ ! -x "$USB_COPIER_SCRIPT" ]; then
        chmod +x "$USB_COPIER_SCRIPT"
    fi
    
    log_message "Starting USB file transfer..."
    # Execute the dedicated script
    "$USB_COPIER_SCRIPT"
}


# Common ROM file extensions, used for USB and loose file checks
ROM_EXTENSIONS=(
    "smc" "gb" "gbc" "gba" "gen" "md" "smd" "iso" "cue" "bin" "ps1" "sfc"
)

# Function to log messages, now writing to stderr and the log file
log_message() {
    local timestamped_message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$timestamped_message" >&2
    echo "$timestamped_message" >> "$LOG_FILE"
}

# --- SCRIPT DEPENDENCY CHECKS (UNCHANGED) ---
check_decompressor_script() {
    if [ ! -f "$DECOMPRESSOR_SCRIPT" ]; then
        log_message "ERROR: Decompressor script not found at $DECOMPRESSOR_SCRIPT"
        exit 1
    fi
    if [ ! -x "$DECOMPRESSOR_SCRIPT" ]; then
        chmod +x "$DECOMPRESSOR_SCRIPT"
    fi
}
check_python_script() {
    if ! command -v python3 &> /dev/null; then log_message "WARNING: python3 not found. JSON conversion will be skipped."; return 1; fi
    if [ ! -f "$PYTHON_SCRIPT" ]; then log_message "WARNING: Python script not found at $PYTHON_SCRIPT. JSON conversion will be skipped."; return 1; fi
    log_message "Python3 and JSON converter script are available"
    return 0
}
run_json_converter() {
    local output_file="$1"
    if [ ! -f "$output_file" ]; then log_message "WARNING: Games list file not found: $output_file. Skipping JSON conversion."; return 1; fi
    local rom_count=$(wc -l < "$output_file" 2>/dev/null || echo 0)
    if [ "$rom_count" -eq 0 ]; then log_message "WARNING: No ROMs found in $output_file. Skipping JSON conversion."; return 1; fi
    log_message "Running JSON converter: python3 $PYTHON_SCRIPT $output_file $EXTRACT_DIR -o $HOME/Portable-Console-Prototype/GUI/games.json"
    if python3 "$PYTHON_SCRIPT" "$output_file" "$EXTRACT_DIR" -o "$HOME/Portable-Console-Prototype/GUI/games.json"; then
        log_message "✓ JSON conversion successful. Output: $HOME/Portable-Console-Prototype/GUI/games.json"
        log_message "✓ Converted $rom_count ROMs to JSON format"
        return 0
    else
        log_message "✗ JSON conversion failed with exit code $?"
        return 1
    fi
}

# --- DIRECTORY AND HELPER FUNCTIONS (UNCHANGED) ---
create_extract_dir() {
    if [ ! -d "$EXTRACT_DIR" ]; then mkdir -p "$EXTRACT_DIR"; log_message "Created extraction directory: $EXTRACT_DIR"; fi
}
find_compressed_files() {
    find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( \
        -name "*.zip" -o \
        -name "*.rar" -o \
        -name "*.7z" -o \
        -name "*.tar" -o \
        -name "*.tar.gz" -o \
        -name "*.tgz" -o \
        -name "*.tar.bz2" -o \
        -name "*.tbz" -o \
        -name "*.tar.xz" -o \
        -name "*.txz" -o \
        -name "*.gz" -o \
        -name "*.bz2" -o \
        -name "*.xz" \
    \) -print0
}
count_roms() {
    if [[ -f "$OUTPUT_FILE" ]]; then wc -l < "$OUTPUT_FILE" 2>/dev/null | tr -d ' '; else echo "0"; fi
}
cleanup_temp_dirs() {
    local temp_dirs=$(find "$EXTRACT_DIR" -name ".temp_*" -type d 2>/dev/null)
    if [[ -n "$temp_dirs" ]]; then
        log_message "Cleaning up temporary directories..."
        echo "$temp_dirs" | while read -r dir; do if [[ -d "$dir" ]]; then rm -rf "$dir"; log_message "Removed temporary directory: $dir"; fi; done
    fi
}

# --- NEW FUNCTION: Process loose ROMs in the Downloads folder ---
process_loose_roms() {
    log_message "=== Checking for loose ROM files in $DOWNLOAD_DIR ==="
    local found_roms=false
    # Define compressed extensions here for filtering against ROM_EXTENSIONS
    local compressed_extensions=("zip" "rar" "7z" "tar" "gz" "bz2" "xz" "tgz" "tbz" "txz")

    # Find loose ROMs in Downloads that are NOT compressed files
    # This uses find with null-separated output for safe handling of filenames with spaces
    while IFS= read -r -d $'\0' file_path; do
        
        local filename=$(basename "$file_path")
        # Declare and assign separately to avoid SC2155
        local extension
        extension="${filename##*.}"
        local new_path="$EXTRACT_DIR/$filename"
        local should_list=true

        log_message "Processing loose ROM: $filename"

        # 1. Move the ROM to the EXTRACT_DIR/games folder
        if mv "$file_path" "$new_path"; then
            log_message "Moved: $filename to $EXTRACT_DIR"

            # 2. Check extension for CUE/BIN logic (case-insensitive check)
            case "${extension,,}" in
                # BIN files should be copied but NOT written to the list
                bin)
                    log_message "BIN file found. Copying only, skipping addition to cache.txt."
                    should_list=false
                    ;;
                # CUE files act as the manifest and SHOULD be listed
                cue)
                    log_message "CUE file found. Writing to cache.txt."
                    should_list=true
                    ;;
                # Other ROMs are listed by default
                *)
                    log_message "Standard ROM file found. Writing to cache.txt."
                    should_list=true
                    ;;
            esac
            
            if [ "$should_list" = true ]; then
                # 3. Add to the games list file
                echo "$new_path" >> "$OUTPUT_FILE"
                found_roms=true
            fi
        else
            log_message "ERROR: Failed to move loose ROM: $filename"
        fi
    
    # 4. The filter logic for 'find':
    done < <(find "$DOWNLOAD_DIR" -maxdepth 1 -type f -print0 | \
             grep -z -i -E "\.($(IFS='|'; echo "${ROM_EXTENSIONS[*]}"))$" | \
             grep -z -v -E "\.($(IFS='|'; echo "${compressed_extensions[*]}"))$")

    if [ "$found_roms" = true ]; then
        log_message "New loose ROMs found and moved."
    else
        log_message "No new loose ROMs found."
    fi
}
# --- MAIN PROCESSING LOGIC (UNCHANGED CORE, MODIFIED FLOW) ---
process_compressed_files() {
    local file_count=0
    cleanup_temp_dirs
    log_message "Searching for compressed files in $DOWNLOAD_DIR..."
    file_count=$(find_compressed_files| tr '\0' '\n' | wc -l)
    
    if [ $file_count -eq 0 ]; then
        log_message "No compressed files found to process."
        return 0
    fi
    
    log_message "Found $file_count compressed file(s) to process."
    
    find_compressed_files | while IFS= read -r -d '' file; do
        local filename=$(basename "$file")
        log_message "=== Processing: $filename ==="
        if "$DECOMPRESSOR_SCRIPT" "$file" "$EXTRACT_DIR" "$OUTPUT_FILE"; then
            log_message "✓ Successfully processed: $filename"
        else
            log_message "✗ Failed to process: $filename"
        fi
        log_message "=== Completed: $filename ==="
    done
    
    cleanup_temp_dirs
    local rom_count=$(count_roms)
    log_message "Compressed file processing complete. Total ROMs in list: $rom_count."
    return 0
}

# --- MODIFIED Main execution flow ---
main() {
    log_message "======= SCRIPT START ======="
    check_decompressor_script
    create_extract_dir
    # Ensure the output file exists to prevent errors on the first run
    touch "$OUTPUT_FILE"

    # 1. Check for files on USB drives
    check_usb_drives
    
    # 2. Process any loose ROMs already in Downloads
    process_loose_roms

    # 3. Process compressed files
    process_compressed_files
    
    # 4. Convert to JSON if possible
    check_python_script
    local python_available=$?
    local rom_count=$(count_roms)
    
    if [ $python_available -eq 0 ] && [ "$rom_count" -gt 0 ]; then
        log_message "=== Starting JSON conversion ==="
        run_json_converter "$OUTPUT_FILE"
    elif [ "$rom_count" -eq 0 ]; then
        log_message "No ROMs in list, skipping JSON conversion."
    else
        log_message "Python not available, skipping JSON conversion."
    fi
    
    log_message "======= SCRIPT FINISHED ======="
}

# Run main function
main "$@"