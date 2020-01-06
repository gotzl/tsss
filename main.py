#!/usr/bin/env python
# TheSuperSimpleSampler

DEBUG = False


def main(device_name, samplerate, samplewidth, channels, frame_count):
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
                if (p.get_device_info_by_host_api_device_index(0, i).get('name') == device_name):
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
                            ch['keys'],
                            out_samplerate=samplerate,
                            out_channels=channels
                        )
                    except Exception as e:
                        print("Unable to open %s (Exception: %s)"%(regname,e))
                        print("")

        if len(registers) == 0:
            raise Exception("Could not find any sample! Please check path in '%s'"%yml)

        print("Loading of instruments took %.2f seconds"%(time.time()-now))
        print("Starting Audio stream and MIDI input loop. You may start hitting the keys!")

        midihandler = MidiInputHandler(port_name, registers, mutex)
        midiin.set_callback(midihandler)

        stream = AudioStream(
            p, outdev,
            channels,
            samplewidth,
            samplerate,
            frame_count,
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


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', default=48000, dest='samplerate', type=int, help='Output sample rate. Has to be an even divider of the samples samplerate.')
    parser.add_argument('-w', default=3, dest='samplewidth', type=int, help='Output sample width. 3=24bit, 2=16bit, 1=8bit.')
    parser.add_argument('-c', default=2, dest='channels', type=int, help='Number of output channels (currently the only valid choice is 2).')
    parser.add_argument('-f', dest='frame_count', type=int, help='Number of frames per period. Lower numbers result in more responsive feeling. Defaults to ~10ms buffer length.')
    parser.add_argument('-d', default='pulse', dest='device_name', help='The name of the output device to be used.')

    args = parser.parse_args()

    if args.channels != 2:
        print("Only 2 channel output is supported.")
        sys.exit(1)

    if args.samplewidth == 1:
        print("Output sample width of 8bit is not supported.")
        sys.exit(1)

    frame_count = 2048 // (192000 // args.samplerate)
    if args.frame_count:
        frame_count = args.frame_count

    main(args.device_name, args.samplerate, args.samplewidth, args.channels, frame_count)

