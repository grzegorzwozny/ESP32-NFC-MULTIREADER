from application import App
import uasyncio as asyncio

try:
    app = App()
except OSError:
    import machine
    machine.reset()
    pass

loop = asyncio.get_event_loop()
loop.create_task(app.led_bar())
loop.create_task(app.buttons())
loop.create_task(app.nfc_readers())
loop.run_forever()
