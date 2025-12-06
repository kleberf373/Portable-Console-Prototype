#!/bin/bash

# Configuration constants from monitor.sh for consistency
DOWNLOAD_DIR="$HOME/Downloads"
LOG_FILE="$HOME/Portable-Console-Prototype/decompression.log" # Use the same log file
ROM_EXTENSIONS=(
    "smc" "gb" "gbc" "gba" "gen" "md" "smd" "iso" "cue" "bin" "ps1" "sfc"
    "zip" "rar" "7z" "tar" "gz" "bz2" "xz" "tar.gz" "tar.bz2" "tar.xz" "tgz" "tbz"
)

# Function to log messages (same as in monitor.sh)
log_message() {
    local timestamped_message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$timestamped_message" >&2
    echo "$timestamped_message" >> "$LOG_FILE"
}

# Function to safely create the destination directory
create_download_dir() {
    if [ ! -d "$DOWNLOAD_DIR" ]; then
        mkdir -p "$DOWNLOAD_DIR"
        log_message "Created download directory: $DOWNLOAD_DIR"
    fi
}

# --- Core Logic: Search and Copy ---
copy_files_from_usb() {
    create_download_dir
    local found_count=0
    
    # Common mount points for removable drives on Linux
    local USB_MOUNTS=(\
        "/media/$USER" \
        "/run/media/$USER" \
        "/mnt" \
    )

    log_message "Starting USB file search..."

    # Iterate over common mount points
    for mount_point in "${USB_MOUNTS[@]}"; do
        if [ -d "$mount_point" ]; then
            # Find all directories one level deep within the mount point (the actual USB drive)
            for usb_drive_dir in "$mount_point"/*; do
                if [ -d "$usb_drive_dir" ]; then
                    log_message "Searching USB drive: $(basename "$usb_drive_dir")"

                    # 💥 FIX: Use find -print0 and explicit Bash pattern matching for safety
                    # This safely handles filenames with spaces and complex extensions.
                    # The file paths are read using a null delimiter.
                    find "$usb_drive_dir" -type f -print0 | while IFS= read -r -d $'\0' file_path; do
                        
                        local filename=$(basename "$file_path")
                        local should_copy=false
                        
                        # Case-insensitive check for ROM extensions
                        for ext in "${ROM_EXTENSIONS[@]}"; do
                            # Check if filename (converted to lowercase) ends with the extension
                            if [[ "${filename,,}" == *".$ext" ]]; then
                                should_copy=true
                                break
                            fi
                        done
                        
                        if [ "$should_copy" = true ]; then
                            local destination="$DOWNLOAD_DIR/$filename"

                            # Check if file already exists in Downloads to avoid unnecessary copies
                            if [ ! -f "$destination" ]; then
                                log_message "Copying: $filename"
                                # Note: 'cp -v' output is redirected to the log file for monitoring
                                cp -v "$file_path" "$DOWNLOAD_DIR" >> "$LOG_FILE" 2>&1
                                found_count=$((found_count + 1))
                            else
                                log_message "Skipping existing file: $filename"
                            fi
                        fi
                    done
                fi
            done
        fi
    done

    log_message "Finished USB file search. Copied $found_count new files."
    return $found_count
}

# Main execution
main() {
    log_message "=== USB COPIER SCRIPT START ==="
    copy_files_from_usb
    log_message "=== USB COPIER SCRIPT END ==="
}

# Execute main function
main