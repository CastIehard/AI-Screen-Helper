import os
import pyautogui
import tkinter as tk
from dotenv import load_dotenv
from openai import OpenAI
import base64
from pynput import keyboard

SYSTEMPROMT = """I am doing a quizz that is in this image.
                If its a sentence with a word missing then just return the word.
                If its a dropdown provide the information needed to map all the left side stuff to the right side stuff.
                If its an open Question return an normal answer as text.
                Answer in plaintext."
                """

# Load API key from .env
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

root = None
overlay = None
label = None
overlay_visible = False  # Tracks the visibility state of the overlay


def initialize_overlay():
    """Initialize the Tkinter overlay window."""
    global root, overlay, label
    print("Initializing Tkinter overlay...")

    root = tk.Tk()
    root.withdraw()  # Hide the main root window

    # Create an overlay window
    overlay = tk.Toplevel(root)
    overlay.geometry("400x200+100+100")  # Adjust size and position
    overlay.attributes('-topmost', True)  # Always on top
    overlay.attributes('-alpha', 0.0)  # Initially invisible
    overlay.overrideredirect(True)  # No borders or title bar
    overlay.configure(bg="white")  # Set background to white

    # Add a label to the overlay
    label = tk.Label(
        overlay,
        text="",
        font=("Helvetica", 14),
        fg="black",  # Text color black for white background
        bg="white",  # Label background white
        wraplength=380
    )
    label.pack(expand=True, padx=10, pady=10)

    print("Tkinter overlay initialized.")


def update_overlay_visibility(text=None):
    """
    Show or hide the overlay. If text is provided, update and show.
    Otherwise, toggle visibility based on current state.
    """
    global overlay, label, overlay_visible
    
    if text is not None:  # Called by main() to show with new content
        print("Updating overlay with new text...")
        label.config(text=text)
        overlay.attributes('-alpha', 0.9)  # Make overlay visible (0.9 for slightly transparent white)
        # overlay.attributes('-alpha', 1.0) # Use 1.0 for fully opaque white
        overlay.wm_attributes('-topmost', 1)
        overlay_visible = True
        print(f"Overlay updated and shown with: {text}")
    else:  # Called by on_press to toggle
        if overlay_visible:
            print("Hiding overlay...")
            overlay.attributes('-alpha', 0.0)
            overlay_visible = False
        else:
            # This case should ideally not be hit if only main shows it initially
            # but if we want '-' to show it even without new content (e.g. last content)
            # then we'd need to handle it. For now, main() handles showing.
            print("Showing overlay (no new text, using previous)...") # Or handle as error
            if label["text"]: # Only show if there's something to show
                overlay.attributes('-alpha', 0.9)
                overlay.wm_attributes('-topmost', 1)
                overlay_visible = True
            else:
                print("No content to show in overlay.")


def take_screenshot(margin_percent=10):
    """Take a screenshot of the entire screen with an optional margin."""
    print("Taking a screenshot...")
    screenshot = pyautogui.screenshot()
    width, height = screenshot.size

    # Calculate the margin in pixels
    margin_x = int(width * margin_percent / 100)
    margin_y = int(height * margin_percent / 100)

    # Crop the screenshot with the calculated margins
    cropped_screenshot = screenshot.crop(
        (margin_x, margin_y, width - margin_x, height - margin_y)
    )

    screenshot_path = "screenshot.png"
    cropped_screenshot.save(screenshot_path)
    print(f"Screenshot saved at {screenshot_path}")
    return screenshot_path


def encode_image_to_base64(image_path):
    """Encode an image file to a base64 string."""
    print(f"Encoding image {image_path} to Base64...")
    with open(image_path, "rb") as image_file:
        img_b64_str = base64.b64encode(image_file.read()).decode('utf-8')
    img_type = "image/png"  # Update if using a different image format
    print("Image encoded to Base64 successfully.")
    return img_b64_str, img_type


def send_to_gpt_with_image(prompt, img_b64_str, img_type):
    """Send a text-based instruction and a base64-encoded image to GPT."""
    print("Sending data to GPT...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Ensure model name is accurate
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{img_type};base64,{img_b64_str}"},
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error while communicating with GPT: {e}")
        return f"Error communicating with GPT: {e}"


def on_press(key):
    """Handle key press events."""
    global overlay_visible # Needed to modify its value
    try:
        key_char = key.char if hasattr(key, 'char') else None
        if key_char == '-':
            if not overlay_visible:
                print("'-' key pressed. Running main function to show overlay...")
                main_process() # This will show the overlay with new content
            else:
                print("'-' key pressed. Hiding overlay...")
                overlay.attributes('-alpha', 0.0) # Hide overlay
                overlay_visible = False
        elif key == keyboard.Key.esc:  # Exit on 'esc'
            print("Exiting program...")
            if root:
                root.quit()  # Stop the Tkinter loop
            return False  # Stop the listener
    except AttributeError:
        print(f"Special key {key} pressed. Ignoring...")


def main_process():
    """
    Main logic: take screenshot, process with GPT, and update overlay.
    This function is called when '-' is pressed and overlay is not visible.
    """
    print("Main function started.")
    # Step 1: Take a screenshot
    screenshot_path = take_screenshot()

    # Step 2: Encode the image to Base64
    img_b64_str, img_type = encode_image_to_base64(screenshot_path)

    # Step 3: Send the instruction and image to GPT
    prompt = SYSTEMPROMT
    try:
        gpt_output = send_to_gpt_with_image(prompt, img_b64_str, img_type)
        print(f"GPT output: {gpt_output}")
    except Exception as e:
        gpt_output = f"Error: {e}"

    # Step 4: Update and show the overlay with the GPT output
    update_overlay_visibility("Answer: " + gpt_output)
    print("Main function completed.")


if __name__ == "__main__":
    print("Press '-' to activate/deactivate the script. Press 'esc' to exit.")

    # Initialize the Tkinter overlay
    initialize_overlay()

    # Start the key listener
    print("Starting key listener...")
    # Using a try-finally block to ensure listener stops if Tkinter loop errors
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        # Start the Tkinter main loop on the main thread
        if root:
            root.mainloop()
    finally:
        print("Stopping key listener...")
        listener.stop()
        listener.join() # Wait for listener thread to finish
        print("Program terminated.")

