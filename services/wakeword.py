#
# Copyright 2018 Picovoice Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import os
import struct
import sys
from datetime import datetime
from threading import Thread

import numpy as np
import pyaudio
import soundfile
from constants import *

sys.path.append(os.path.join(os.path.dirname(__file__), '../../binding/python'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../resources/util/python'))

from pvporcupine import Porcupine, util

DEFAULT_KEYWORD = '/home/pi/envs/brucuenv/lib/python3.7/site-packages/pvporcupine/resources/keyword_files/raspberrypi/picovoice_raspberrypi.ppn'
#https://github.com/Picovoice/porcupine/issues/88
class WakeWord(Thread):   

    def __init__(
            self,
            library_path,
            model_file_path,
            keyword_file_paths,
            sensitivities,
            input_device_index=None,
            output_path=None,
            stream_q=None,
            msg_q=None):

        """
        Constructor.

        :param library_path: Absolute path to Porcupine's dynamic library.
        :param model_file_path: Absolute path to the model parameter file.
        :param keyword_file_paths: List of absolute paths to keyword files.
        :param sensitivities: Sensitivity parameter for each wake word. For more information refer to
        'include/pv_porcupine.h'. It uses the
        same sensitivity value for all keywords.
        :param input_device_index: Optional argument. If provided, audio is recorded from this input device. Otherwise,
        the default audio input device is used.
        :param output_path: If provided recorded audio will be stored in this location at the end of the run.
        """

        super(WakeWord, self).__init__()

        self._library_path = library_path
        self._model_file_path = model_file_path
        self._keyword_file_paths = keyword_file_paths
        self._sensitivities = sensitivities        
        self._stream_q = stream_q
        self._msg_q = msg_q

        self._output_path = output_path
        if self._output_path is not None:
            self._recorded_frames = []

    def run(self):
        """
         Creates an input audio stream, initializes wake word detection (Porcupine) object, and monitors the audio
         stream for occurrences of the wake word(s). It prints the time of detection for each occurrence and index of
         wake word.
         """

        num_keywords = len(self._keyword_file_paths)

        keyword_names = list()
        for x in self._keyword_file_paths:
            keyword_names.append(os.path.basename(x).replace('.ppn', '').replace('_compressed', '').split('_')[0])

        print('listening for:')
        for keyword_name, sensitivity in zip(keyword_names, self._sensitivities):
            print('- %s (sensitivity: %f)' % (keyword_name, sensitivity))

        porcupine = None        
        
        try:
            porcupine = Porcupine(
                library_path=self._library_path,
                model_file_path=self._model_file_path,
                keyword_file_paths=self._keyword_file_paths,
                sensitivities=self._sensitivities)                        

            while True:
                #pcm = self._audio_stream.read(porcupine.frame_length)
                pcm = self._stream_q.get()
                
                #print(porcupine.frame_length) #512
                pcm = struct.unpack_from("h" * CHUNK, pcm)
                
                #if self._output_path is not None:
                #    self._recorded_frames.append(pcm)

                result = porcupine.process(pcm)
                
                if num_keywords == 1 and result:
                    self._msg_q.put(1)
                    print('[%s] detected keyword' % str(datetime.now()))
                elif num_keywords > 1 and result >= 0:
                    self._msg_q.put(2)
                    print('[%s] detected %s' % (str(datetime.now()), keyword_names[result]))

        except KeyboardInterrupt:
            print('stopping ...')
        finally:
            if porcupine is not None:
                porcupine.delete()                    

            if self._output_path is not None and len(self._recorded_frames) > 0:
                recorded_audio = np.concatenate(self._recorded_frames, axis=0).astype(np.int16)
                soundfile.write(self._output_path, recorded_audio, samplerate=porcupine.sample_rate, subtype='PCM_16')    


class PorcupineConfig:
    def __init__(self):
        self.keywords = util.KEYWORDS
        self.keyword_file_paths = DEFAULT_KEYWORD
        self.library_path = util.LIBRARY_PATH
        self.model_file_path = util.MODEL_FILE_PATH
        self.sensitivities = 0.5        
        self.output_path = None

def run(index, msg_q, stream_q):    
    
    args = PorcupineConfig()

    if args.keyword_file_paths is None:
        if args.keywords is None:
            raise ValueError('either --keywords or --keyword_file_paths must be set')

        keywords = [x.strip() for x in args.keywords.split(',')]

        if all(x in KEYWORDS for x in keywords):
            keyword_file_paths = [KEYWORD_FILE_PATHS[x] for x in keywords]
        else:
            raise ValueError(
                'selected keywords are not available by default. available keywords are: %s' % ', '.join(KEYWORDS))
    else:
        keyword_file_paths = [x.strip() for x in args.keyword_file_paths.split(',')]

    if isinstance(args.sensitivities, float):
        sensitivities = [args.sensitivities] * len(keyword_file_paths)
    else:
        sensitivities = [float(x) for x in args.sensitivities.split(',')]

    WakeWord(
        library_path=args.library_path,
        model_file_path=args.model_file_path,
        keyword_file_paths=keyword_file_paths,
        sensitivities=sensitivities,
        output_path=args.output_path,    
        stream_q=stream_q,  
        msg_q=msg_q
        ).run()

