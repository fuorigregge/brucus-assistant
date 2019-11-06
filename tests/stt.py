# [START speech_transcribe_streaming]
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import io

#https://cloud.google.com/speech-to-text/docs/streaming-recognize#speech-streaming-mic-recognize-python
def transcribe_streaming(stream_file):
    """Streams transcription of the given audio file."""
    
    client = speech.SpeechClient()

    # [START speech_python_migration_streaming_request]
    with io.open(stream_file, 'rb') as audio_file:
        content = audio_file.read()

    # In practice, stream should be a generator yielding chunks of audio data.
    stream = [content]
    requests = (types.StreamingRecognizeRequest(audio_content=chunk)
                for chunk in stream)

    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code='it-IT')
    streaming_config = types.StreamingRecognitionConfig(config=config)

    # streaming_recognize returns a generator.
    # [START speech_python_migration_streaming_response]
    responses = client.streaming_recognize(streaming_config, requests)
    # [END speech_python_migration_streaming_request]

    for response in responses:
        # Once the transcription has settled, the first result will contain the
        # is_final result. The other results will be for subsequent portions of
        # the audio.
        for result in response.results:
            print('Finished: {}'.format(result.is_final))
            print('Stability: {}'.format(result.stability))
            alternatives = result.alternatives
            # The alternatives are ordered from most likely to least.
            for alternative in alternatives:
                print('Confidence: {}'.format(alternative.confidence))
                print(u'Transcript: {}'.format(alternative.transcript))
    # [END speech_python_migration_streaming_response]
# [END speech_transcribe_streaming]


transcribe_streaming("/opt/brucu-assistant/test-ita.wav")