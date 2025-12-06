#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <linux/joystick.h>
#include <linux/input.h>
#include <linux/uinput.h>

// --- Configuration Constants ---
#define JOYSTICK_DEVICE "/dev/input/js0"
#define UINPUT_DEVICE "/dev/uinput"
#define CONFIG_FILE "map.txt"
#define MAX_BUTTONS 30 
#define MAX_AXES 10 
#define AXIS_THRESHOLD 10000 // Analog value required to trigger a keypress (out of 32767)
#define MAX_LINE_LENGTH 64

// --- Global Mapping Structures ---
// Button Map: Index = Joystick Button Number, Value = Keyboard Key Code
int key_map_buttons[MAX_BUTTONS] = {0};

// Axis Map: Index 0 = Axis Number, Index 1/2 = Key Code for NEG(-1)/POS(+1)
// axis_map_axes[AXIS_NUM][0] -> NEGATIVE KEY CODE (Left/Up)
// axis_map_axes[AXIS_NUM][1] -> POSITIVE KEY CODE (Right/Down)
int key_map_axes[MAX_AXES][2] = {0};

// State Tracking: Tracks if an axis direction is currently "pressed" (-1, 0, or 1)
int axis_state[MAX_AXES] = {0};


/**
 * Maps a string key name (e.g., "KEY_X") to its integer code.
 * Includes all required RetroArch movement keys.
 */
int key_name_to_code(const char *key_name) {
    if (strcmp(key_name, "KEY_X") == 0) return KEY_X;
    if (strcmp(key_name, "KEY_C") == 0) return KEY_C;
    if (strcmp(key_name, "KEY_S") == 0) return KEY_S;
    if (strcmp(key_name, "KEY_D") == 0) return KEY_D;
    if (strcmp(key_name, "KEY_Q") == 0) return KEY_Q;
    if (strcmp(key_name, "KEY_W") == 0) return KEY_W;
    if (strcmp(key_name, "KEY_A") == 0) return KEY_A;
    if (strcmp(key_name, "KEY_Z") == 0) return KEY_Z;
    if (strcmp(key_name, "KEY_LEFTSHIFT") == 0) return KEY_LEFTSHIFT;
    if (strcmp(key_name, "KEY_ENTER") == 0) return KEY_ENTER;
    if (strcmp(key_name, "KEY_1") == 0) return KEY_1;
    if (strcmp(key_name, "KEY_2") == 0) return KEY_2;
    
    // Movement Keys
    if (strcmp(key_name, "KEY_LEFT") == 0) return KEY_LEFT;
    if (strcmp(key_name, "KEY_RIGHT") == 0) return KEY_RIGHT;
    if (strcmp(key_name, "KEY_UP") == 0) return KEY_UP;
    if (strcmp(key_name, "KEY_DOWN") == 0) return KEY_DOWN;
    
    // Right Stick WASD (already covered by KEY_W, KEY_A, KEY_S, KEY_D)

    return -1; // Unknown key
}

/**
 * Loads the button and axis mappings from the configuration file.
 */
int load_mapping() {
    FILE *file = fopen(CONFIG_FILE, "r");
    if (!file) {
        perror("Error opening map.txt");
        return -1;
    }

    char line[MAX_LINE_LENGTH];
    while (fgets(line, sizeof(line), file)) {
        // Skip comments and empty lines
        if (line[0] == '#' || line[0] == '\n' || line[0] == ' ') continue;

        int button_num, axis_num, direction;
        char key_name[MAX_LINE_LENGTH];
        int key_code;

        // Try to parse Axis format: AXIS_NUM_DIRECTION=KEY_NAME
        if (sscanf(line, "%d_%d=%s", &axis_num, &direction, key_name) == 3) {
            key_code = key_name_to_code(key_name);
            
            if (key_code != -1 && axis_num >= 0 && axis_num < MAX_AXES && (direction == -1 || direction == 1)) {
                int map_index = (direction == -1) ? 0 : 1; // 0 for NEG, 1 for POS
                key_map_axes[axis_num][map_index] = key_code;
                printf("Mapped Axis %d, Dir %d to Key %s (%d)\n", axis_num, direction, key_name, key_code);
            } else if (key_code == -1) {
                fprintf(stderr, "Warning: Unknown key name '%s' in map.txt\n", key_name);
            }
        }
        // Try to parse Button format: BUTTON_NUM=KEY_NAME
        else if (sscanf(line, "%d=%s", &button_num, key_name) == 2) {
            key_code = key_name_to_code(key_name);

            if (key_code != -1 && button_num >= 0 && button_num < MAX_BUTTONS) {
                key_map_buttons[button_num] = key_code;
                printf("Mapped Button %d to Key %s (%d)\n", button_num, key_name, key_code);
            } else if (key_code == -1) {
                fprintf(stderr, "Warning: Unknown key name '%s' in map.txt\n", key_name);
            }
        }
    }

    fclose(file);
    return 0;
}

/**
 * Sends a keyboard event (key down or key up) via the virtual device.
 */
int emit_event(int fd, int type, int code, int value) {
    struct input_event ev;

    memset(&ev, 0, sizeof(ev));
    ev.type = type;
    ev.code = code;
    ev.value = value;
    
    if (write(fd, &ev, sizeof(ev)) < 0) {
        perror("Error writing event");
        return -1;
    }
    return 0;
}

/**
 * Sets up the virtual uinput device.
 */
int setup_uinput_device(int *uinput_fd_out) {
    int fd = open(UINPUT_DEVICE, O_WRONLY | O_NONBLOCK);
    if (fd < 0) {
        perror("Error opening uinput device. Is 'uinput' kernel module loaded? Try: 'sudo modprobe uinput'");
        return -1;
    }

    // Enable key events for all mapped keys
    ioctl(fd, UI_SET_EVBIT, EV_KEY);
    for (int i = 0; i < MAX_BUTTONS; ++i) {
        if (key_map_buttons[i] != 0) {
            ioctl(fd, UI_SET_KEYBIT, key_map_buttons[i]);
        }
    }
    for (int i = 0; i < MAX_AXES; ++i) {
        if (key_map_axes[i][0] != 0) {
            ioctl(fd, UI_SET_KEYBIT, key_map_axes[i][0]);
        }
        if (key_map_axes[i][1] != 0) {
            ioctl(fd, UI_SET_KEYBIT, key_map_axes[i][1]);
        }
    }

    struct uinput_user_dev uidev;
    memset(&uidev, 0, sizeof(uidev));
    snprintf(uidev.name, UINPUT_MAX_NAME_SIZE, "Virtual Gamepad Mapper");
    uidev.id.bustype = BUS_VIRTUAL;
    uidev.id.vendor  = 0x1234;
    uidev.id.product = 0x5678;
    uidev.id.version = 1;

    if (write(fd, &uidev, sizeof(uidev)) < 0) {
        perror("Error writing uinput device info");
        close(fd);
        return -1;
    }

    if (ioctl(fd, UI_DEV_CREATE) < 0) {
        perror("Error creating uinput device");
        close(fd);
        return -1;
    }
    
    *uinput_fd_out = fd;
    printf("Virtual keyboard device created successfully.\n");
    return 0;
}


/**
 * Handles the logic for mapping axis movement to key presses.
 */
void handle_axis_event(int uinput_fd, int axis_num, short axis_value) {
    if (axis_num >= MAX_AXES) return;

    // Determine the current direction state based on the threshold
    int current_direction = 0;
    if (axis_value < -AXIS_THRESHOLD) {
        current_direction = -1; // Negative direction (Left/Up)
    } else if (axis_value > AXIS_THRESHOLD) {
        current_direction = 1;  // Positive direction (Right/Down)
    }
    
    // Check if the state has changed
    if (current_direction != axis_state[axis_num]) {
        
        // 1. Release the old key, if one was pressed (state != 0)
        if (axis_state[axis_num] != 0) {
            int old_key_code = (axis_state[axis_num] == -1) 
                                ? key_map_axes[axis_num][0] // Negative key
                                : key_map_axes[axis_num][1]; // Positive key

            if (old_key_code != 0) {
                printf("Axis %d released (Key %d)\n", axis_num, old_key_code);
                emit_event(uinput_fd, EV_KEY, old_key_code, 0); // Key UP
            }
        }
        
        // 2. Press the new key, if a new direction is active (current_direction != 0)
        if (current_direction != 0) {
            int new_key_code = (current_direction == -1) 
                                ? key_map_axes[axis_num][0] // Negative key
                                : key_map_axes[axis_num][1]; // Positive key

            if (new_key_code != 0) {
                printf("Axis %d pressed (Key %d)\n", axis_num, new_key_code);
                emit_event(uinput_fd, EV_KEY, new_key_code, 1); // Key DOWN
            }
        }

        // 3. Update the state and synchronize the events
        axis_state[axis_num] = current_direction;
        emit_event(uinput_fd, EV_SYN, SYN_REPORT, 0);
    }
}


/**
 * Main loop to read joystick events and map them to keyboard events.
 */
int main_loop(int joystick_fd, int uinput_fd) {
    struct js_event jse;

    printf("Ready to map events. Threshold: %d. Press Ctrl+C to stop.\n", AXIS_THRESHOLD);

    while (1) {
        if (read(joystick_fd, &jse, sizeof(jse)) != sizeof(jse)) {
            if (errno == EAGAIN) {
                usleep(1000); 
                continue;
            } else if (errno == EIO) {
                fprintf(stderr, "Controller disconnected.\n");
                break;
            }
            perror("Error reading joystick event");
            break;
        }

        // --- BUTTON EVENT HANDLING (Same as before) ---
        if (jse.type & JS_EVENT_BUTTON) {
            int button_num = jse.number;
            int button_value = jse.value; 

            if (button_num >= 0 && button_num < MAX_BUTTONS) {
                int key_code = key_map_buttons[button_num];
                
                if (key_code != 0) {
                    printf("Button %d (%s) -> Key %d\n", button_num, button_value ? "PRESS" : "RELEASE", key_code);
                    emit_event(uinput_fd, EV_KEY, key_code, button_value);
                    emit_event(uinput_fd, EV_SYN, SYN_REPORT, 0);
                }
            }
        }
        
        // --- AXIS EVENT HANDLING (NEW) ---
        else if (jse.type & JS_EVENT_AXIS) {
            handle_axis_event(uinput_fd, jse.number, jse.value);
        }
    }
    return 0;
}

int main() {
    int joystick_fd = -1;
    int uinput_fd = -1;
    
    // 1. Load mappings
    if (load_mapping() != 0) {
        return 1;
    }

    // 2. Open joystick device (set non-blocking for cleaner reads)
    joystick_fd = open(JOYSTICK_DEVICE, O_RDONLY | O_NONBLOCK);
    if (joystick_fd < 0) {
        perror("Error opening joystick device. Check permissions or if controller is connected (e.g., /dev/input/js0).");
        return 1;
    }
    printf("Joystick device opened: %s\n", JOYSTICK_DEVICE);

    // 3. Set up virtual keyboard
    if (setup_uinput_device(&uinput_fd) != 0) {
        close(joystick_fd);
        return 1;
    }

    // 4. Run the main loop
    main_loop(joystick_fd, uinput_fd);
    
    // --- Cleanup ---
    if (uinput_fd >= 0) {
        ioctl(uinput_fd, UI_DEV_DESTROY);
        close(uinput_fd);
    }
    if (joystick_fd >= 0) {
        close(joystick_fd);
    }
    printf("Mapper terminated and virtual device destroyed.\n");
    return 0;
}