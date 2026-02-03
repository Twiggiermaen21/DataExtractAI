import cv2
import numpy as np
import os
from PIL import Image


def enhance_image_for_ocr(image_path: str, scale_factor: float = 2.0) -> str:
    print(f"  ✨ Ulepszanie obrazu: {os.path.basename(image_path)}")
    
    img = cv2.imread(image_path)
    if img is None:
        pil_img = Image.open(image_path)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    original_height, original_width = img.shape[:2]
    
    if scale_factor != 1.0:
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(denoised)
    
    binary = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    binary = _deskew(binary)
    
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    enhanced_path = os.path.join(os.path.dirname(image_path), f"{base_name}_enhanced.png")
    cv2.imwrite(enhanced_path, binary)
    
    return enhanced_path


def _deskew(image: np.ndarray) -> np.ndarray:
    try:
        coords = np.column_stack(np.where(image < 128))
        if len(coords) < 100:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        
        if abs(angle) < 0.5 or abs(angle) > 5:
            return image
        
        h, w = image.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    except:
        return image
