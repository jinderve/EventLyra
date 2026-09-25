"""TranslateGemma 4B en BF16. La carga ocurre una sola vez por instancia."""

from __future__ import annotations

import logging
import threading

from eventlyra.config import TRANSLATION_DTYPE_BF16, Settings

_IDIOMAS = {"es", "en"}
_logger = logging.getLogger(__name__)
_aviso_8bit_silenciado = False


def traduccion_degenerada(texto: str) -> bool:
    """Marca salidas con escrituras que no corresponden a en/es (alucinación)."""
    if not texto or not texto.strip():
        return True
    for ch in texto:
        code = ord(ch)
        if (
            0x0900 <= code <= 0x0D7F
            or 0x0E00 <= code <= 0x0E7F
            or 0x3040 <= code <= 0x30FF
            or 0x4E00 <= code <= 0x9FFF
            or 0xAC00 <= code <= 0xD7AF
            or 0x0600 <= code <= 0x06FF
        ):
            return True
    return False


def _silenciar_aviso_matmul_8bit() -> None:
    global _aviso_8bit_silenciado
    if _aviso_8bit_silenciado:
        return
    logging.getLogger("bitsandbytes.autograd._functions").setLevel(logging.ERROR)
    _aviso_8bit_silenciado = True


class LocalTranslateGemma:
    """Una instancia, una copia de los pesos en la GPU."""

    def __init__(self, settings: Settings) -> None:
        if settings.translation_quantization != TRANSLATION_DTYPE_BF16:
            raise ValueError("LocalTranslateGemma carga el 4B en bf16.")
        self.settings = settings
        self._model = None
        self._processor = None
        self._dtype = None
        self._load_lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        with self._load_lock:
            if self._model is not None:
                return
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor

            model_id = self.settings.translation_model_id
            dtype = (
                torch.bfloat16
                if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
                else torch.float16
            )
            # Una sola copia en la GPU 0. El 8-bit de bitsandbytes degeneraba la salida.
            model = AutoModelForImageTextToText.from_pretrained(
                model_id,
                torch_dtype=dtype,
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
            self._dtype = dtype
            self._torch = torch
            _logger.info("TranslateGemma 4B cargado en %s, una copia en la GPU 0.", dtype)

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
        moved = inputs.to(device, dtype=self._dtype)
        input_len = len(moved["input_ids"][0])
        palabras = max(1, len(text.split()))
        max_new_tokens = min(128, max(24, palabras * 3))
        tokenizer = getattr(self._processor, "tokenizer", self._processor)
        eos = getattr(tokenizer, "eos_token_id", None)
        generate_kwargs = {
            "do_sample": False,
            "max_new_tokens": max_new_tokens,
        }
        if eos is not None:
            generate_kwargs["eos_token_id"] = eos
            generate_kwargs["pad_token_id"] = eos
        with torch.inference_mode():
            output = self._model.generate(**moved, **generate_kwargs)
        generated = output[0][input_len:]
        decoded = self._processor.decode(generated, skip_special_tokens=True).strip()
        decoded = decoded.split("\n\n")[0].strip()
        if traduccion_degenerada(decoded):
            _logger.warning(
                "La traducción salió degenerada (%s); se muestra el original.",
                decoded[:80],
            )
            return text
        return decoded
