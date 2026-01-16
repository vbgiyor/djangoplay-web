import time
from threading import Lock

stdout_lock = Lock()


def animate_processing(stop_event, stdout):
    dots = ['.', '..', '...']
    i = 0
    while not stop_event.is_set():
        with stdout_lock:
            stdout.write(f'\rProcessing{dots[i % len(dots)]}', ending='')
            stdout.flush()
        time.sleep(0.5)  # Increase from 0.2 to 0.5 seconds
        i += 1
    with stdout_lock:
        stdout.write('\r' + ' ' * 20 + '\r', ending='')
        stdout.flush()
