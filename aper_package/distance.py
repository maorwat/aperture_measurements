import pandas as pd
import numpy as np
import xtrack as xt
import plotly.graph_objects as go

from aper_package.utils import match_indices

from aper_package.twiss import Twiss
from aper_package.aperture_plot import Aper

def calc_distance_from_nominal(aper, twiss):

