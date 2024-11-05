import pytesseract
from PIL import Image
import cv2
import os
import numpy as np
from pdf2image import convert_from_path
import openai
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = api_key


def purify_and_extract_text_from_pdf(file_path):
    openai.api_key = openai.api_key

    images = convert_from_path(file_path, size=1000)

    extracted_text = ''

    def preprocess_and_extract_text(image):
        image_np = np.array(image)
        gray_image = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        _, thresh_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh_image_pil = Image.fromarray(thresh_image)
        text = pytesseract.image_to_string(thresh_image_pil, lang='eng+hin')
        text = text.replace('\n', ' ').strip()
        return text

    for img in images:
        extracted_text += '\n\n' + preprocess_and_extract_text(img) + '\n\n'

    def purify_ocr_text(ocr_text):
        client = openai.ChatCompletion
        max_retries = 5
        retry_delay = 10
        for attempt in range(max_retries):
            try:
                chat_response = client.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that corrects and purifies OCR text to remove all possible errors and mistakes, ensuring 100% correct English and Hindi words."},
                        {"role": "user", "content": f"Purify the following OCR text:\n\n{ocr_text}"},
                    ],
                )
                return chat_response.choices[0].message.content
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    print(f"Rate limit exceeded. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
            except Exception as e:
                return ocr_text

    purified_text = purify_ocr_text(extracted_text)
    print("____*____*_____Pytesserract worked____*____*____")
    print(purified_text)
    return purified_text

