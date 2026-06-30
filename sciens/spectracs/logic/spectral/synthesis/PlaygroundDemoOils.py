from sciens.spectracs.logic.spectral.verdict.RoastState import RoastState


class PlaygroundDemoOil:
    def __init__(self, roastState: RoastState, label: str, targetHue: float):
        self.roastState = roastState
        self.label = label
        self.targetHue = targetHue


# Three demo oils along the green->brown hue axis. The achievable range is naturally narrow — oil-like
# transmission only spans ~35-72° through the (correct) colour pipeline (the colours don't "breathe"
# far) — so these are the realistic, distinct, reliably-tunable hues, ordered under -> perfect -> over.
PLAYGROUND_DEMO_OILS = [
    PlaygroundDemoOil(RoastState.UNDER_ROASTED, "Under-roasted", 72.0),
    PlaygroundDemoOil(RoastState.PERFECT_ROASTED, "Perfect-roasted", 60.0),
    PlaygroundDemoOil(RoastState.OVER_ROASTED, "Over-roasted", 35.0),
]
