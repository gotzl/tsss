TheSuperSimpleSampler is a sampler writen to play samples from [realsamples](https://www.realsamples.de),
specifically the samples of the `German Harpsichord 1741`.
It is used together with a [Johannus](https://www.johannus.com) digital organ so some things are very specific
for this combination, eg the selection of registers via MIDI commands send by the organ and usage of two manuals (respectively MIDI channels).


# Install
I assume that python3 is your system default. The following will fetch the code and install dependencies.
For this to work, you need a CPP compiler installed on your system (eg `sudo apt-get install build-essential`).
For Windows, I'd recomment to install [python 3.6](https://www.python.org/downloads/release/python-368/) (this installs pip as well) and [Build Tools for Visual Studio 2019](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2019).


```bash
git clone https://github.com/gotzl/tsss.git
pip install -r requirements.txt # --user
python setup.py build_ext --inplace
``` 


# Running it
First, adapt the path in the `instruments.yaml` to the location of your samples.
In this file, you can also choose the MIDI command to select a certain register.
The default values map the MIDI signals of the register selectors of the foot-manual.

To start the sampler, type

```bash
./main.py
```
There are some commandline options to control the output samplerate/width and buffer size.
Note that the output samplerate has to be an even divider of the samples samplrate.
The default is 48000, so if your samples have a rate of 44100 or 88200, use
the '-r 44100' switch.

As of now, only 24bit 2 channel samples @192KHz have been tested.

# ISSUES
* For keys where no sample exists, the samples are resampled to lower/higher pitch. 
This takes a large amount of time (and RAM).
* Samples are expected to start with a number that reflects their tune relative to each other
* Samples are expected to have 2 channels
