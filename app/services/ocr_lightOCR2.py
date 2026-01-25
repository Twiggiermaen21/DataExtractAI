import torch
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
from PIL import Image
import os
import json
import time
import gc

class LightOCRService:
    def __init__(self, model_name="lightonai/LightOnOCR-2-1B", device=None):
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.model = None
        self.processor = None

    def load_model(self):
        if self.model is None:
            print(f"⏳ Loading LightOCR model on {self.device}...")
            try:
                self.model = LightOnOcrForConditionalGeneration.from_pretrained(
                    self.model_name, 
                    torch_dtype=self.dtype
                ).to(self.device)
                self.processor = LightOnOcrProcessor.from_pretrained(self.model_name)
                print("✅ LightOCR model loaded.")
            except Exception as e:
                print(f"❌ Failed to load LightOCR model: {e}")
                raise e

    def unload_model(self):
        if self.model is not None:
            print("🔄 Unloading LightOCR model form memory...")
            del self.model
            del self.processor
            self.model = None
            self.processor = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            print("✅ LightOCR model unloaded.")

    def predict(self, image_path):
        if self.model is None:
            self.load_model()
            
        print(f"Processing: {image_path}...")
        try:
            image = Image.open(image_path)
            # Ensure image is in RGB mode for consistency
            if image.mode != "RGB":
                image = image.convert("RGB")

            conversation = [{"role": "user", "content": [{"type": "image", "image": image}]}]

            inputs = self.processor.apply_chat_template(
                conversation,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            )
            inputs = {k: v.to(device=self.device, dtype=self.dtype) if v.is_floating_point() else v.to(self.device) for k, v in inputs.items()}

            output_ids = self.model.generate(**inputs, max_new_tokens=1024)
            generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
            output_text = self.processor.decode(generated_ids, skip_special_tokens=True)
            
            return [OCRResult(output_text, image_path)]

        except Exception as e:
            print(f"❌ Error during OCR prediction: {e}")
            raise e

class OCRResult:
    def __init__(self, text, input_path):
        self.text = text
        self.input_path = input_path
        # Mimic structure expected by frontend/routes
        self.parsing_res_list = [{"block_content": text}] 

    def save_to_json(self, save_path):
        filename = os.path.basename(self.input_path)
        base_name = os.path.splitext(filename)[0]
        timestamp = int(time.time())
        output_filename = f"{base_name}_{timestamp}.json"
        full_output_path = os.path.join(save_path, output_filename)

        data = {
            "input_path": self.input_path,
            "parsing_res_list": self.parsing_res_list,
            "full_text": self.text 
        }

        try:
            with open(full_output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"💾 JSON saved to: {full_output_path}")
            return full_output_path
        except Exception as e:
            print(f"⚠️ Failed to save JSON: {e}")
            return None

