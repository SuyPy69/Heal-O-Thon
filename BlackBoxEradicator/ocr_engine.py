import cv2
import pytesseract
import os


# --- IMPORTANT FOR WINDOWS USERS ---
# If you are on Windows, you usually need to point pytesseract to the .exe file.
# Uncomment the line below and ensure the path matches your installation!
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_path):
    """
    Uses OpenCV to preprocess a medical report image (makes it black and white for clarity),
    then uses Tesseract OCR to extract the text.
    """
    if not os.path.exists(image_path):
        return "Error: Image file not found."

    try:
        # 1. Read the image using OpenCV
        img = cv2.imread(image_path)

        # 2. Convert to Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 3. Apply thresholding to make the text pop (helps with noisy hospital scans)
        # cv2.THRESH_OTSU automatically calculates the best threshold value
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        # 4. Run Tesseract to extract the text
        extracted_text = pytesseract.image_to_string(gray)

        return extracted_text.strip()

    except Exception as e:
        return f"OCR Extraction Failed: {e}\n(Did you install Tesseract-OCR on your system?)"