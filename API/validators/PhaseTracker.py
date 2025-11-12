"""
PhaseTracker - Tracks pipeline progress by phase

Provides phase-aware status tracking for the validator system.
Maps individual step validators to logical workflow phases.
"""

from typing import Dict, List, Optional


class PhaseTracker:
    """Tracks pipeline progress through workflow phases"""

    # Phase definitions with steps and metadata
    # Phases match the user-facing workflow: Setup → Prepare Content → Commercial Detection → Finalize Lineup
    PHASES = {
        0: {
            'name': 'Platform Setup',
            'steps': ['PlatformSelection', 'PlexAuth', 'FolderMaker'],
            'automated': False,  # Requires user interaction
            'description': 'Configure platform, authenticate Plex, create working folders'
        },
        1: {
            'name': 'Prepare Content',
            'steps': [
                'ToonamiChecker',  # Content discovery
                'LineupPrep',
                'BumpEncoder',
                'UncutEncoder',
                'Multilineup',  # First run (uncut)
                'Merger',  # First run (uncut)
                'EpisodeFilter'
            ],
            'automated': True,  # Automated after user selects shows in ToonamiChecker
            'description': 'Scan anime library, select shows, and prepare uncut lineup'
        },
        2: {
            'name': 'Commercial Detection',
            'steps': ['CommercialBreaker'],
            'automated': False,  # User runs CommercialBreaker
            'description': 'Detect commercial break points in episodes'
        },
        3: {
            'name': 'Prepare Cut Lineup',
            'steps': [
                'CommercialInjectorPrep',  # Traditional only
                'CommercialInjector',
                'BlockMaker',
                'PostCutBumpFilter',  # Optional
                'Multilineup',  # Second run (postcut) - optional
                'Merger',  # Second run (cut)
                'BumpCalculator',  # Cutless only
                'CutlessFinalizer'  # Cutless only
            ],
            'automated': True,  # Runs as single thread after CommercialBreaker
            'description': 'Inject commercials/bumps and create final lineup for platform export'
        }
    }

    def __init__(self):
        """Initialize phase tracker"""
        pass

    def get_current_phase(self, completed_steps: List[str]) -> Dict:
        """
        Determine current phase from completed steps

        Args:
            completed_steps: List of completed step names

        Returns:
            Dictionary with phase information:
            - If phase complete: {completed_phase, completed_phase_name, status: 'complete'}
            - If phase in progress: {current_phase, current_phase_name, status: 'in_progress', progress}
            - If not started: {current_phase: 0, status: 'not_started'}
        """
        # Find highest completed phase
        for phase_num in sorted(self.PHASES.keys(), reverse=True):
            phase = self.PHASES[phase_num]
            phase_steps = phase['steps']

            # Check if ALL required steps in this phase are complete
            # (accounting for conditional steps)
            if self._phase_completed(phase_num, completed_steps):
                return {
                    'completed_phase': phase_num,
                    'completed_phase_name': phase['name'],
                    'status': 'complete',
                    'automated': phase['automated'],
                    'description': phase['description']
                }

        # Find in-progress phase (has some completed steps)
        for phase_num in sorted(self.PHASES.keys()):
            phase = self.PHASES[phase_num]
            phase_steps = phase['steps']

            # Find steps in this phase that are completed
            completed_in_phase = [s for s in phase_steps if s in completed_steps]

            if len(completed_in_phase) > 0:
                return {
                    'current_phase': phase_num,
                    'current_phase_name': phase['name'],
                    'status': 'in_progress',
                    'progress': f"{len(completed_in_phase)}/{len(phase_steps)} steps",
                    'completed_steps': completed_in_phase,
                    'remaining_steps': [s for s in phase_steps if s not in completed_steps],
                    'automated': phase['automated'],
                    'description': phase['description']
                }

        # No steps completed - at phase 0
        return {
            'current_phase': 0,
            'current_phase_name': self.PHASES[0]['name'],
            'status': 'not_started',
            'automated': False
        }

    def _phase_completed(self, phase_num: int, completed_steps: List[str]) -> bool:
        """
        Check if a phase is complete (accounting for conditional steps)

        Args:
            phase_num: Phase number to check
            completed_steps: List of completed step names

        Returns:
            True if phase is complete, False otherwise
        """
        phase = self.PHASES[phase_num]
        phase_steps = phase['steps']

        # Special handling for phases with conditional steps
        if phase_num == 0:
            # Platform Setup: PlexAuth is conditional
            # Complete if PlatformSelection and FolderMaker done (PlexAuth optional)
            required = ['PlatformSelection', 'FolderMaker']
            return all(s in completed_steps for s in required)

        elif phase_num == 3:
            # Prepare Cut Lineup: Several conditional steps
            # CommercialInjectorPrep (traditional only)
            # PostCutBumpFilter (optional)
            # BumpCalculator (cutless only)
            # CutlessFinalizer (cutless only)

            # Core required steps
            required = ['CommercialInjector', 'BlockMaker', 'Merger']
            return all(s in completed_steps for s in required)

        else:
            # For other phases, all steps must be complete
            return all(s in completed_steps for s in phase_steps)

    def get_phase_summary(self, phase_num: int, completed_steps: List[str],
                         version_status: Optional[Dict] = None) -> str:
        """
        Get human-readable summary for a phase

        Args:
            phase_num: Phase number
            completed_steps: List of completed step names
            version_status: Optional version information

        Returns:
            Human-readable phase summary
        """
        if phase_num not in self.PHASES:
            return "Invalid phase number"

        phase = self.PHASES[phase_num]
        phase_name = phase['name']

        # Check completion status
        if self._phase_completed(phase_num, completed_steps):
            status_text = "COMPLETE"
        else:
            phase_steps = phase['steps']
            completed_in_phase = [s for s in phase_steps if s in completed_steps]
            status_text = f"IN PROGRESS ({len(completed_in_phase)}/{len(phase_steps)} steps)"

        summary = f"Phase {phase_num} ({phase_name}): {status_text}"

        # Add version info if available
        if version_status:
            if phase_num == 1 and 'phase_1_uncut' in version_status:
                versions = version_status['phase_1_uncut']
                if versions:
                    summary += f"\n  Created versions: {versions}"

            elif phase_num == 3 and 'phase_3_cut' in version_status:
                versions = version_status['phase_3_cut']
                if versions:
                    summary += f"\n  Created versions: {versions}"

        # Add step details
        phase_steps = phase['steps']
        for step in phase_steps:
            if step in completed_steps:
                summary += f"\n  ✓ {step}"
            else:
                summary += f"\n  ✗ {step}"

        return summary

    def get_all_phases(self) -> Dict:
        """Get all phase definitions"""
        return self.PHASES

    def get_phase_info(self, phase_num: int) -> Optional[Dict]:
        """Get information about a specific phase"""
        return self.PHASES.get(phase_num)
