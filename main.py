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
                Answer in plaintext in thi schema: "Question: Answer"
                """

# Load API key from .env
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

root = None
overlay = None
label = None


def initialize_overlay():
    """Initialize the Tkinter overlay window with zero transparency."""
    global root, overlay, label
    print("Initializing Tkinter overlay...")

    root = tk.Tk()
    root.withdraw()  # Hide the main root window

    # Create an overlay window
    overlay = tk.Toplevel(root)
    overlay.geometry("400x200+100+100")  # Adjust size and position
    overlay.attributes('-topmost', True)  # Always on top
    overlay.attributes('-alpha', 0)  # Initially invisible
    overlay.overrideredirect(True)  # No borders or title bar
    overlay.configure(bg="black")

    # Add a label to the overlay
    label = tk.Label(overlay, text="", font=("Helvetica", 14), fg="white", bg="black", wraplength=380)
    label.pack(expand=True, padx=10, pady=10)

    print("Tkinter overlay initialized.")


def update_overlay(text):
    """Update the overlay window with text and make it visible for 5 seconds."""
    global overlay, label
    print("Updating overlay with new text...")
    label.config(text=text)  # Update the label's text
    overlay.attributes('-alpha', 0.8)  # Make the overlay visible
    # Make the overlay truly topmost and always on top
    overlay.wm_attributes('-topmost', 1)
    root.after(5000, lambda: overlay.attributes('-alpha', 0.0))  # Hide after 5 seconds
    print(f"Overlay updated with: {text}")
    #bring the window to the front


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
    print(f"Image encoded to Base64 successfully.")
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
    try:
        key_char = key.char if hasattr(key, 'char') else None
        if key_char == '-':  # Check for the '-' key
            print("'-' key pressed. Running main function...")
            main()
        elif key == keyboard.Key.esc:  # Exit on 'esc'
            print("Exiting program...")
            root.quit()  # Stop the Tkinter loop
            return False
    except AttributeError:
        print(f"Special key {key} pressed. Ignoring...")


def main():
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

    # Step 4: Update the overlay with the GPT output
    update_overlay(gpt_output)
    print("Main function completed.")


if __name__ == "__main__":
    print("Press '-' to activate the script. Press 'esc' to exit.")

    # Initialize the Tkinter overlay
    initialize_overlay()

    # Start the key listener
    print("Starting key listener...")
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # Start the Tkinter main loop on the main thread
    root.mainloop()