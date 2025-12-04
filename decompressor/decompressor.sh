#!/bin/bash

# Decompressor script that handles various archive formats and filenames with spaces
# Usage: ./decompressor.sh <file_path> <extract_dir> <output_file>

# Consistent log function with monitor.sh
LOG_FILE="$HOME/Portable-Console-Prototype/decompressor/decompression.log"
log_message() {
    local timestamped_message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$timestamped_message" >&2
    echo "$timestamped_message" >> "$LOG_FILE"
}

# Function to detect file type
detect_file_type() {
    local file="$1"
    local extension="${file##*.}"
    local filename=$(basename "$file")
    
    # Check using file command first
    local file_type=$(file -b "$file" | tr '[:upper:]' '[:lower:]')
    
    # Common ROM file extensions (expanded list)
    local rom_extensions=("smc" "gb" "gbc" "gba" "gen" "md" "smd" "iso" "cue" "bin" "ps1" "sfc")
    
    # Check if it's a known ROM extension
    for ext in "${rom_extensions[@]}"; do
        if [[ "${filename,,}" == *".$ext" ]]; then
            echo "rom"
            return
        fi
    done
    
    # Check archive types
    case "$extension" in
        zip)
            if [[ "$file_type" == *"zip archive"* ]]; then
                echo "archive"
                return
            fi
            ;;
        rar)
            if [[ "$file_type" == *"rar archive"* ]]; then
                echo "archive"
                return
            fi
            ;;
        7z)
            if [[ "$file_type" == *"7-zip archive"* ]]; then
                echo "archive"
                return
            fi
            ;;
        tar|gz|bz2|xz)
            if [[ "$file_type" == *"tar archive"* || "$file_type" == *"gzip compressed"* || "$file_type" == *"bzip2 compressed"* || "$file_type" == *"xz compressed"* ]]; then
                echo "archive"
                return
            fi
            ;;
    esac
    
    # If not a known type
    echo "unknown"
}

# Function to extract archives
extract_file() {
    local file_path="$1"
    local extract_dir="$2"
    local extension="${file_path##*.}"
    
    log_message "Extracting to: $extract_dir"
    
    # Use -o to overwrite files without prompting
    case "${extension,,}" in
        zip)
            unzip -o "$file_path" -d "$extract_dir" >/dev/null 2>&1
            ;;
        rar)
            unrar x -o+ "$file_path" "$extract_dir" >/dev/null 2>&1
            ;;
        7z)
            7z x -o"$extract_dir" "$file_path" >/dev/null 2>&1
            ;;
        tar|tgz|tbz|txz)
            # Tar archives can have various compression types
            tar -xf "$file_path" -C "$extract_dir" >/dev/null 2>&1
            ;;
        *)
            log_message "WARNING: Unknown archive format for: $file_path"
            return 1
            ;;
    esac
    
    # Check if the command was successful
    if [ $? -eq 0 ]; then
        return 0
    else
        log_message "ERROR: Failed to extract $file_path"
        return 1
    fi
}

# Function to check and move files if they are in a subfolder
check_and_flatten() {
    local dir="$1"
    
    # Check if there's only one subdirectory and nothing else
    local num_items=$(find "$dir" -maxdepth 1 | wc -l)
    local num_dirs=$(find "$dir" -maxdepth 1 -type d | wc -l)
    local num_files=$((num_items - num_dirs))
    
    log_message "Directory analysis: $((num_items-1)) total items, $((num_dirs-1)) directories, $num_files files"
    
    if [ "$((num_items-1))" -eq 1 ] && [ "$((num_dirs-1))" -eq 1 ] && [ "$num_files" -eq 0 ]; then
        local sub_dir=$(find "$dir" -maxdepth 1 -type d | sed '1d')
        log_message "Files found in subfolder: $(basename "$sub_dir"). Moving..."
        mv "$sub_dir"/* "$dir"/
        rmdir "$sub_dir"
    else
        log_message "Files are already in root directory, no action needed"
    fi
}

# MODIFIED FUNCTION: Move ROM files to main games directory and add to list, checking for duplicates
move_roms_to_main_dir() {
    local specific_extract_dir="$1"
    local main_extract_dir="$2"
    local output_file="$3"
    
    log_message "Checking for new ROMs in $specific_extract_dir..."
    
    local rom_extensions=("smc" "gb" "gbc" "gba" "gen" "md" "smd" "iso" "cue" "bin" "ps1" "sfc")
    
    local moved_count=0
    
    # Find and process ROM files
    find "$specific_extract_dir" -type f -print0 | while IFS= read -r -d '' file; do
        local extension="${file##*.}"
        local is_rom=0
        
        for ext in "${rom_extensions[@]}"; do
            if [[ "${extension,,}" == "$ext" ]]; then
                is_rom=1
                break
            fi
        done
        
        if [ $is_rom -eq 1 ]; then
            local filename=$(basename "$file")
            
            # *** NEW: Check if the game is already in the list ***
            if grep -q -x "$filename" "$output_file"; then
                log_message "Duplicate found, skipping: $filename"
                # Clean up the duplicate file
                rm "$file"
            else
                local dest_path="$main_extract_dir/$filename"
                
                # Handle filename conflicts in the destination directory
                if [[ -f "$dest_path" ]]; then
                    local counter=1
                    local name_part="${filename%.*}"
                    local ext_part="${filename##*.}"
                    
                    while [[ -f "$dest_path" ]]; do
                        dest_path="$main_extract_dir/${name_part}_${counter}.${ext_part}"
                        ((counter++))
                    done
                    log_message "File conflict resolved: $filename -> $(basename "$dest_path")"
                fi
                
                # Move the new ROM file
                if mv "$file" "$dest_path"; then
                    log_message "New game found: $(basename "$file") -> $(basename "$dest_path")"
                    # Add the new, unique filename to the list
                    printf "%s\n" "$(basename "$dest_path")" >> "$output_file"
                    ((moved_count++))
                else
                    log_message "ERROR: Failed to move $file"
                fi
            fi
        fi
    done
    
    if [ "$moved_count" -gt 0 ]; then
        log_message "Added $moved_count new ROM(s) to the list."
    else
        log_message "No new ROMs found to add."
    fi
    
    # Remove the specific directory if it's now empty
    if [ -d "$specific_extract_dir" ] && [ -z "$(ls -A "$specific_extract_dir")" ]; then
        rmdir "$specific_extract_dir"
        log_message "Removed empty temporary directory: $specific_extract_dir"
    else
        log_message "Keeping directory (non-ROM or duplicate files remain): $specific_extract_dir"
    fi
    
    return $moved_count
}

# Main function
main() {
    if [ $# -ne 3 ]; then
        echo "Usage: $0 <file_path> <extract_dir> <output_file>" >&2
        exit 1
    fi
    
    local file_path="$1"
    local main_extract_dir="$2"
    local output_file="$3"
    
    if [ ! -f "$file_path" ]; then
        log_message "ERROR: File not found: $file_path"
        exit 1
    fi

    # Create the output file if it doesn't exist, to prevent grep errors
    touch "$output_file"
    
    local filename=$(basename "$file_path")
    local archive_name="${filename%.*}"
    local temp_extract_dir="$main_extract_dir/.temp_$archive_name"
    mkdir -p "$temp_extract_dir"
    
    log_message "Starting extraction of: $filename"
    
    if extract_file "$file_path" "$temp_extract_dir"; then
        log_message "Successfully extracted: $filename"
        log_message "Deleting original compressed file: $file_path"
        rm "$file_path"
        
        check_and_flatten "$temp_extract_dir"
        move_roms_to_main_dir "$temp_extract_dir" "$main_extract_dir" "$output_file"
        
        log_message "ROM list updated for: $filename"
    else
        log_message "Failed to extract: $filename"
        rm -rf "$temp_extract_dir" 2>/dev/null
        return 1
    fi
    
    return 0
}

# Call the main function
main "$@"