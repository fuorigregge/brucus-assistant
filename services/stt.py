import re
import sys

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from queue import Empty
from constants import *
# Audio recording parameters
#share queue
class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, stream_q):
        self._stream_q = stream_q
        
        # Create a thread-safe buffer of audio data
        #self._buff = Queue()
        self.closed = True

    def __enter__(self):        

        #pcm = self._audio_stream.read(CHUNK)
        #pcm = struct.unpack_from("h" * CHUNK, pcm)
        self.closed = False        

        # for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        #     print("record {}....".format(i))
        #     data = self._audio_stream.read(CHUNK)
        #     self._buff.put(data)

        return self

    def __exit__(self, type, value, traceback):
        # self._audio_stream.stop_stream()
        # self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        # self._stream_q.put(None)
        #self._audio_interface.terminate()

    # def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
    #     """Continuously collect data from the audio stream, into the buffer."""
    #     self._buff.put(in_data)
    #     return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._stream_q.get()            

            chunk = struct.unpack_from("h" * CHUNK, chunk)

            if chunk is None:
                return 
            data = [chunk]

            print("chunk", chunk)

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._stream_q.get()
                    if chunk is None:
                        return 
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)


def listen_print_loop(responses):
    """Iterates through server responses and prints them.
    The responses passed is a generator that will block until a response
    is provided by the server.
    Each response may contain multiple results, and each result may contain
    multiple alternatives; for details, see https://goo.gl/tjCPAU.  Here we
    print only the transcription for the top alternative of the top result.
    In this case, responses are provided for interim results as well. If the
    response is an interim one, print a line feed at the end of it, to allow
    the next result to overwrite it, until the response is a final one. For the
    final one, print a newline to preserve the finalized transcription.
    """
    num_chars_printed = 0
    for response in responses:
        
        print(response.results)

        if not response.results:
            continue

        # The `results` list is consecutive. For streaming, we only care about
        # the first result being considered, since once it's `is_final`, it
        # moves on to considering the next utterance.
        result = response.results[0]
        if not result.alternatives:
            continue

        # Display the transcription of the top alternative.
        transcript = result.alternatives[0].transcript

        # Display interim results, but with a carriage return at the end of the
        # line, so subsequent lines will overwrite them.
        #
        # If the previous result was longer than this one, we need to print
        # some extra spaces to overwrite the previous result
        overwrite_chars = ' ' * (num_chars_printed - len(transcript))

        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + '\r')
            sys.stdout.flush()

            num_chars_printed = len(transcript)

        else:
            print(transcript + overwrite_chars)

            # Exit recognition if any of the transcribed phrases could be
            # one of our keywords.
            if re.search(r'\b(esci|stop|ferma)\b', transcript, re.I):
                print('Exiting..')
                break

            num_chars_printed = 0


def run(stream_q):
    # See http://g.co/cloud/speech/docs/languages
    # for a list of supported languages.
    language_code = 'it-IT'  # a BCP-47 language tag

    client = speech.SpeechClient()
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code)
    streaming_config = types.StreamingRecognitionConfig(
        config=config,
        interim_results=True)

    with MicrophoneStream(stream_q) as stream:
        audio_generator = stream.generator()
        requests = (types.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator)

        responses = client.streaming_recognize(streaming_config, requests)

        
        # Now, put the transcription responses to use.
        listen_print_loop(responses)