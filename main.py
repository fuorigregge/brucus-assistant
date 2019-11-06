
from services import wakeword, stt

from queue import Queue,Full
import threading
import pyaudio
from constants import *

msg_q = Queue()
stream_q = Queue()

pa = pyaudio.PyAudio()

# define callback for pyaudio to store the recording in queue
def pyaudio_callback(in_data, frame_count, time_info, status):
    try:
        stream_q.put(in_data)
    except Full:
        pass # discard
    return (None, pyaudio.paContinue)

def get_audio_stream():        
    return pa.open(
        rate=RATE,
        channels=CHANNELS, #1 def
        format=pyaudio.paInt16,
        input=True,
        stream_callback=pyaudio_callback,
        frames_per_buffer=CHUNK,
        input_device_index=INPUT_DEVICE_INDEX)    

def run():
    base_thread_count = threading.active_count()        

    print("Enter CTRL+C to end recording...")

    audio_stream = get_audio_stream()

    audio_stream.start_stream()

    try:
        t = threading.Thread(target=wakeword.run, args=(1, msg_q, stream_q))
        t.start()
        while threading.active_count() > base_thread_count:        
            event = msg_q.get() #1/0
            if event == 1:       
                print("wake up....")         
                stt.run(stream_q)

    except KeyboardInterrupt:
        print('stopping ...')
    finally:
        audio_stream.stop_stream()
        audio_stream.close()
        pa.terminate()
        #audio_source.completed_recording()

        
  
if __name__== "__main__":
    run()