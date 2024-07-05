import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ipywidgets as widgets

from twiss import Twiss
from aper import Aper
from elements import Elements
from collimators import Collimators

def plot(twiss, aper, plane, beam, machine_components = True, collimators = False):

