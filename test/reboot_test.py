import subprocess
import threading
import time

def run_command(cmd, timeout, output):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()
    while True:
        if process.poll() is not None:
            output[0], output[1] = process.communicate()
            output[2] = process.returncode  # Update index 2 directly
            break
        elif time.time() - start_time > timeout:
            process.terminate()
            output[2] = -1  # Update index 2 directly
            break

def reboot_Pcs(pc):
    try:
        cmd = f'shutdown -m \\\\{pc} -r -f -t 3'
        output = [None, None, None]
        thread = threading.Thread(target=run_command, args=(cmd, 5, output))
        thread.start()
        thread.join()

        if output[2] == 0:
            print(f'Reboot command sent to {pc} successfully!')
            return True
        elif output[2] == -1:
            print(f'Timeout occurred while sending reboot command to {pc}')
            return False
        else:
            error_msg = (output[1] or output[0] or b'').decode('utf-8').strip()
            print(f'Unable to send reboot command to {pc}. Error: {error_msg}')
            return False
    except Exception as e:
        print(f'An exception occurred: {e}')
        return False

reboot_Pcs('SC-L-PH-BC2-L05.yorku.yorku.ca')
