#%%
import matplotlib.pyplot as plt
# %%
 # Import numpy symbols to scipy namespace
 import numpy as _num
 linalg = None
 from numpy import *
 from numpy.random import rand, randn
 from numpy.fft import fft, ifft
 from numpy.lib.scimath import *
 __all__ = []
 __all__ += _num.__all__
 __all__ += ['randn', 'rand', 'fft', 'ifft']
 del _num
 # Remove the linalg imported from numpy so that the scipy.linalg package can be
 # imported.
 del linalg
 __all__.remove('linalg')
# %%
