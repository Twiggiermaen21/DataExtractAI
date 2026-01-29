"""
Serwis do ulepszania obrazów przed OCR.
Poprawia jakość rozpoznawania tekstu.
"""

import cv2
import numpy as np
import os
from PIL import Image


def enhance_image_for_ocr(image_path: str, scale_factor: float = 2.0) -> str:
    """
    Ulepsza obraz przed OCR:
    1. Skalowanie (powiększenie)
    2. Konwersja do skali szarości
    3. Usuwanie szumu
    4. Zwiększenie kontrastu
    5. Binaryzacja adaptacyjna
    
    Args:
        image_path: Ścieżka do obrazu
        scale_factor: Współczynnik skalowania (domyślnie 2.0)
        
    Returns:
        Ścieżka do ulepszonego obrazu (tymczasowy plik)
    """
    print(f"  ✨ Ulepszanie obrazu: {os.path.basename(image_path)}")
    
    # Wczytaj obraz
    img = cv2.imread(image_path)
    if img is None:
        # Spróbuj przez PIL (obsługuje więcej formatów)
        pil_img = Image.open(image_path)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    original_height, original_width = img.shape[:2]
    
    # 1. Skalowanie (powiększenie) - pomaga przy małych czcionkach
    if scale_factor != 1.0:
        new_width = int(original_width * scale_factor)
        new_height = int(original_height * scale_factor)
        img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        print(f"    📐 Skalowanie: {original_width}x{original_height} -> {new_width}x{new_height}")
    
    # 2. Konwersja do skali szarości
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. Usuwanie szumu (denoising)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    print(f"    🔇 Usunięto szum")
    
    # 4. Zwiększenie kontrastu (CLAHE - Contrast Limited Adaptive Histogram Equalization)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(denoised)
    print(f"    🎨 Zwiększono kontrast")
    
    # 5. Binaryzacja adaptacyjna (lepiej działa na nierównomiernie oświetlonych obrazach)
    binary = cv2.adaptiveThreshold(
        contrast,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2
    )
    print(f"    ⬛ Binaryzacja zakończona")
    
    # 6. Opcjonalne: deskewing (korekcja przechylenia)
    binary = deskew_image(binary)
    
    # Zapisz do tymczasowego pliku
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    temp_dir = os.path.dirname(image_path)
    enhanced_path = os.path.join(temp_dir, f"{base_name}_enhanced.png")
    
    cv2.imwrite(enhanced_path, binary)
    print(f"    💾 Zapisano ulepszony obraz: {enhanced_path}")
    
    return enhanced_path


def deskew_image(image: np.ndarray) -> np.ndarray:
    """
    Korekcja przechylenia obrazu (deskewing).
    Ograniczona do maksymalnie 5 stopni aby uniknąć błędnych obrotów.
    """
    try:
        # Znajdź wszystkie niezerowe piksele
        coords = np.column_stack(np.where(image < 128))
        
        if len(coords) < 100:
            return image
        
        # Oblicz minimalny prostokąt obejmujący
        angle = cv2.minAreaRect(coords)[-1]
        
        # Korekta kąta
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # OGRANICZENIE: korekta tylko dla małych kątów (max 5 stopni)
        # To zapobiega błędnym obrotom o 90 stopni
        if abs(angle) < 0.5 or abs(angle) > 5:
            return image
        
        # Obróć obraz
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        print(f"    🔄 Korekcja przechylenia: {angle:.2f}°")
        return rotated
        
    except Exception as e:
        print(f"    ⚠️ Nie udało się skorygować przechylenia: {e}")
        return image


def enhance_for_ocr_simple(image_path: str) -> str:
    """
    Prostsze ulepszenie - tylko skalowanie i zwiększenie ostrości.
    Użyj jeśli pełne ulepszenie powoduje problemy.
    """
    print(f"  ✨ Proste ulepszanie: {os.path.basename(image_path)}")
    
    img = cv2.imread(image_path)
    if img is None:
        pil_img = Image.open(image_path)
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    # Skalowanie 1.5x
    h, w = img.shape[:2]
    img = cv2.resize(img, (int(w * 1.5), int(h * 1.5)), interpolation=cv2.INTER_CUBIC)
    
    # Zwiększenie ostrości
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(img, -1, kernel)
    
    # Zapisz
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    temp_dir = os.path.dirname(image_path)
    enhanced_path = os.path.join(temp_dir, f"{base_name}_enhanced.png")
    
    cv2.imwrite(enhanced_path, sharpened)
    print(f"    💾 Zapisano: {enhanced_path}")
    
    return enhanced_path
