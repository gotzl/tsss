#!/usr/bin/env python
# TheSuperSimpleSampler

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


if __name__ == '__main__':
    from tsss import MidiInputHandler, loop, AudioStream
    import Instrument

    from multiprocessing import Lock
    from rtmidi.midiutil import open_midiinput
    import pyaudio
    import time
    import yaml

    stream, p, midiin = None, None, None

    registers = {}
    mutex = Lock()

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

        midihandler = MidiInputHandler(port_name, registers, mutex)
        midiin.set_callback(midihandler)

        stream = AudioStream(
            p, outdev,
            CHANNELS,
            SAMPLEWIDTH,
            SAMPLERATE,
            FRAMESPERBUFFER,
            mutex, registers)
        stream.start_stream()

        if DEBUG:
            registers[0, (203, 2)].active = True

        loop(registers, mutex, midihandler)

    except (EOFError, KeyboardInterrupt, SystemExit):
        print('')
    finally:
        print("Exit.")

        if stream is not None:
            stream.close()
        if p is not None:
            p.terminate()
        if midiin is not None:
            midiin.close_port()

        del midiin

