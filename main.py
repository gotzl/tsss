#!/usr/bin/env python
# TheSuperSimpleSampler
from multiprocessing import Lock

DEBUG = False

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bit
# SAMPLERATE = 24000
# SAMPLERATE = 41000
SAMPLERATE = 48000
# SAMPLERATE = 192000
# FRAMESPERBUFFER = 256
FRAMESPERBUFFER = 512
# FRAMESPERBUFFER = 1024
# FRAMESPERBUFFER = 2048
# FRAMESPERBUFFER = 4096


registers = {}
mutex = Lock()


def mixer(frame_count):
    mutex.acquire()
    try:
        frames = getframes(registers.values(), frame_count)
    finally:
        mutex.release()

    return bytes(wavdecode.mix(
        frames,
        frame_count,
        CHANNELS,
        SAMPLEWIDTH, 0))


def callback(in_data, frame_count, time_info, status):
    dd = mixer(frame_count)
    return (dd, pyaudio.paContinue)


if __name__ == '__main__':
    from tsss import eventloop, getframes
    import Instrument

    from rtmidi.midiutil import open_midiinput
    import sys
    import time
    import pyaudio
    import yaml

    sys.path.append('tsss')
    import wavdecode

    stream, p, midiin = None, None, None

    try:
        midiin, port_name = open_midiinput(None)
        p = pyaudio.PyAudio()

        outdev = None
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
                print("Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
                if (p.get_device_info_by_host_api_device_index(0, i).get('name') == 'pulse'):
                    outdev = i

        stream = p.open(
            format=p.get_format_from_width(SAMPLEWIDTH),
            channels=CHANNELS,
            rate=SAMPLERATE,
            frames_per_buffer=FRAMESPERBUFFER,
            start=False,
            output=True,
            output_device_index=outdev,
            stream_callback=callback)

        now = time.time()
        yml = 'instruments.yaml'
        instruments = yaml.safe_load(open(yml))

        for name, inst in instruments.items():
            print('Opening %s'%name)
            for n, ch in inst['channel'].items():
                for reg, regname in ch['registers'].items():
                    try:
                        registers[n, tuple(map(int, reg.split()))] = Instrument.Instrument(
                            inst['path'],
                            inst['lowest'],
                            regname,
                            ch['keys']
                        )
                    except Exception as e:
                        print("Unable to open %s"%regname)
                        print("")

        if len(registers) == 0:
            raise Exception("Could not find any sample! Please check path in '%s'"%yml)

        print("Loading of instruments took %.2f seconds"%(time.time()-now))
        print("Starting Audio stream and MIDI input loop. You may start hitting the keys!")
        stream.start_stream()

        if DEBUG:
            registers[0, (203, 2)].active = True

        eventloop(midiin, port_name, registers, mutex)

    except (EOFError, KeyboardInterrupt, SystemExit):
        print('')
    finally:
        print("Exit.")

        if stream is not None:
            stream.stop_stream()
            stream.close()
        if p is not None:
            p.terminate()
        if midiin is not None:
            midiin.close_port()

        del midiin

