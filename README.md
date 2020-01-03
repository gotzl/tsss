TheSuperSimpleSampler is a sampler writen to play samples from [realsamples](https://www.realsamples.de),
specifically the samples of the `German Harpsichord 1741`.
It is used together with a [Johannus](https://www.johannus.com) digital organ so some things are very specific
for this combination, eg the selection of registers via MIDI commands send by the organ and usage of two manuals (respectively MIDI channels).


# Install
```bash
git clone https://github.com/gotzl/tsss.git
pip3 install -r requirements.txt # --user
python3 setup.py build_ext --inplace
``` 
For this to work, you need a CPP compiler and portaudio installed on your system.


# Running it
First, adapt the path in the `instruments.yaml` to the location of your samples.
In this file, you can also choose the MIDI command to select a certain register.
The default values map the MIDI signals of the register selectors of the foot-manual.

To start the sampler, type

```bash
./main.py
```


# ISSUES
* For keys where no sample exists, the samples are resampled to lower/higher pitch. 
This takes a large amount of time.
* Samples are expected to start with a number that reflects their tune relative to each other
* Code is a bit messy...
* Expects 24bit LE 2 channel wavs