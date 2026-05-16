import base64
import logging

import requests
from PIL import Image

log = logging.getLogger(__name__)


class Pixoo64:
    def __init__(self, host: str, brightness: int = 100):
        self._url = f"http://{host}/post"
        self._session = requests.Session()
        self._timeout = 5
        self._set_brightness(brightness)

    def push(self, image: Image.Image) -> None:
        img = image.convert("RGB").resize((64, 64), Image.NEAREST)
        b64 = base64.b64encode(img.tobytes()).decode()

        self._post({"Command": "Draw/ResetHttpGifId"})
        self._post(
            {
                "Command": "Draw/SendHttpGif",
                "PicNum": 1,
                "PicWidth": 64,
                "PicOffset": 0,
                "PicID": 1,
                "PicSpeed": 86400000,
                "PicData": b64,
            }
        )

    def _set_brightness(self, level: int) -> None:
        try:
            self._post(
                {
                    "Command": "Channel/SetBrightness",
                    "Brightness": max(0, min(100, level)),
                }
            )
        except Exception as e:
            log.debug("brightness set skipped: %s", e)

    def _post(self, payload: dict) -> dict:
        resp = self._session.post(self._url, json=payload, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error_code", 0) != 0:
            log.warning("Pixoo64 API error: %s", data)
        return data
