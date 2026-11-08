import asyncio
import threading
import logging

from zigbee.zigbee_service import ZigbeeService, start_zigbee

log = logging.getLogger("homeos")

class ZigbeeThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.service: ZigbeeService | None = None
        self._ready = threading.Event()

    def start(self, timeout: float = 30):
        threading.Thread(target=self._run, name="zigbee", daemon=True).start()
        self._ready.wait(timeout)

    def _run(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.service = self.loop.run_until_complete(start_zigbee())
        except Exception:
            log.exception("Zigbee se nepodarilo nastartovat")
        finally:
            self._ready.set()
        if self.service:
            self.loop.run_forever()

    def call(self, coro, timeout: float = 10):
        """Spusti korutinu v Zigbee smycce a pocka na vysledek."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)