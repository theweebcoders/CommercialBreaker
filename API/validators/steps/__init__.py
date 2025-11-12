"""
Step Validators

Validators for individual pipeline steps, organized in sequential order.
"""

# Phase 0: Platform Setup
from API.validators.steps.PlatformSelectionValidator import PlatformSelectionValidator
from API.validators.steps.PlexAuthValidator import PlexAuthValidator
from API.validators.steps.FolderMakerValidator import FolderMakerValidator
from API.validators.steps.AppDataValidator import AppDataValidator

# Phase 1: Content Discovery
from API.validators.steps.ToonamiCheckerValidator import ToonamiCheckerValidator

# Phase 2: Prepare Uncut Content
from API.validators.steps.LineupPrepValidator import LineupPrepValidator
from API.validators.steps.BumpEncoderValidator import BumpEncoderValidator
from API.validators.steps.UncutEncoderValidator import UncutEncoderValidator
from API.validators.steps.MultilineupValidator import MultilineupValidator
from API.validators.steps.MergerValidator import MergerValidator
from API.validators.steps.EpisodeFilterValidator import EpisodeFilterValidator

# Phase 3: Commercial Detection
from API.validators.steps.CommercialBreakerValidator import CommercialBreakerValidator

# Phase 4: Prepare Cut Anime
from API.validators.steps.CommercialInjectorPrepValidator import CommercialInjectorPrepValidator
from API.validators.steps.CommercialInjectorValidator import CommercialInjectorValidator
from API.validators.steps.BlockMakerValidator import BlockMakerValidator
from API.validators.steps.PostCutBumpFilterValidator import PostCutBumpFilterValidator
from API.validators.steps.BumpCalculatorValidator import BumpCalculatorValidator
from API.validators.steps.CutlessFinalizerValidator import CutlessFinalizerValidator

__all__ = [
    # Phase 0
    'PlatformSelectionValidator',
    'PlexAuthValidator',
    'FolderMakerValidator',
    'AppDataValidator',

    # Phase 1
    'ToonamiCheckerValidator',

    # Phase 2
    'LineupPrepValidator',
    'BumpEncoderValidator',
    'UncutEncoderValidator',
    'MultilineupValidator',
    'MergerValidator',
    'EpisodeFilterValidator',

    # Phase 3
    'CommercialBreakerValidator',

    # Phase 4
    'CommercialInjectorPrepValidator',
    'CommercialInjectorValidator',
    'BlockMakerValidator',
    'PostCutBumpFilterValidator',
    'BumpCalculatorValidator',
    'CutlessFinalizerValidator',
]
