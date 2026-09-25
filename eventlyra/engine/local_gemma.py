"""TranslateGemma 4B en 8-bit. La carga ocurre una sola vez por instancia."""

from __future__ import annotations

import threading

from eventlyra.config import TRANSLATION_QUANT_8BIT, Settings

_IDIOMAS = {"es", "en"}


class LocalTranslateGemma:
    """Una instancia, una copia de los pesos en la GPU."""

    def __init__(self, settings: Settings) -> None:
        if settings.translation_quantization != TRANSLATION_QUANT_8BIT:
            raise ValueError("LocalTranslateGemma solo carga el modelo en 8-bit.")
        self.settings = settings
        self._model = None
        self._processor = None
        self._load_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        with self._load_lock:
            if self._model is not None:
                return
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

            model_id = self.settings.translation_model_id
            quantization = BitsAndBytesConfig(load_in_8bit=True)
            # device_map fijo a la GPU 0: una sola copia, sin partir el modelo.
            model = AutoModelForImageTextToText.from_pretrained(
                model_id,
                quantization_config=quantization,
                device_map={"": 0},
            )
            model.eval()
            processor = AutoProcessor.from_pretrained(model_id)
            tokenizer = getattr(processor, "tokenizer", processor)
            if getattr(model.generation_config, "pad_token_id", None) is None:
                eos = getattr(tokenizer, "eos_token_id", None)
                if eos is not None:
                    model.generation_config.pad_token_id = eos
            self._model = model
            self._processor = processor
            self._torch = torch

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            return ""
        if source_lang not in _IDIOMAS or target_lang not in _IDIOMAS:
            raise ValueError(
                "La traducción local de este corte acepta solo 'es' y 'en'. "
                f"Llegaron {source_lang!r} → {target_lang!r}."
            )
        if source_lang == target_lang:
            return cleaned
        self.load()
        return self._generate(cleaned, source_lang, target_lang)

    def _generate(self, text: str, source_lang: str, target_lang: str) -> str:
        assert self._model is not None
        assert self._processor is not None
        torch = self._torch
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "source_lang_code": source_lang,
                        "target_lang_code": target_lang,
                        "text": text,
                    }
                ],
            }
        ]
        inputs = self._processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        device = self._model.device
        moved = {
            key: value.to(device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }
        input_len = moved["input_ids"].shape[-1]
        max_new_tokens = min(256, max(32, len(text.split()) * 3))
        with torch.inference_mode():
            output = self._model.generate(
                **moved,
                do_sample=False,
                max_new_tokens=max_new_tokens,
            )
        generated = output[0][input_len:]
        tokenizer = getattr(self._processor, "tokenizer", self._processor)
        return tokenizer.decode(generated, skip_special_tokens=True).strip()
