import math


class GaugeColorUtil:
    # SPEC_roast_ampel.md §8.2 — the Qt-free colour + classification maths behind a VerdictGaugeView. A faithful
    # port of the mockup's inline OKLab helpers (roast_ampel_mockup.html), generic over plugin-supplied data:
    # NO roast constants live here (§8.2). Colours are 6-digit hex strings in/out (§8.3a, D8-colour-format);
    # hexToRgb is used only internally for the OKLab gradient interpolation. Pure stdlib — no dependency.
    #
    # The four generic entry points a renderer / plugin uses:
    #   gradientColorAt(value, anchors)                 -> "#rrggbb"   (the swatch colour at a value)
    #   gradientStops(anchors, bandLeft, bandRight, n)  -> [(pos, "#rrggbb")]   (band fill, left->right)
    #   positionOf(value, bandLeft, bandRight)          -> 0..1        (marker position, clamped)
    #   classify(value, thresholds, bandLeft, bandRight)-> int         (which class; orientation-aware)

    # --- hex <-> rgb ---------------------------------------------------------
    def hexToRgb(self, hexColor):
        h = hexColor.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def rgbToHex(self, rgb):
        red, green, blue = rgb
        return "#%02x%02x%02x" % (int(round(red)), int(round(green)), int(round(blue)))

    # --- OKLab (verbatim port of the mockup helpers) -------------------------
    @staticmethod
    def __srgbToLin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    @staticmethod
    def __linToSrgb(c):
        s = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        return max(0.0, min(255.0, 255.0 * s))

    def __toOklab(self, rgb):
        r = self.__srgbToLin(rgb[0])
        g = self.__srgbToLin(rgb[1])
        b = self.__srgbToLin(rgb[2])
        l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
        m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
        s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
        return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)

    def __fromOklab(self, lab):
        big_l, a, b = lab
        l_ = big_l + 0.3963377774 * a + 0.2158037573 * b
        m_ = big_l - 0.1055613458 * a - 0.0638541728 * b
        s_ = big_l - 0.0894841775 * a - 1.2914855480 * b
        l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
        return (int(round(self.__linToSrgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s))),
                int(round(self.__linToSrgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s))),
                int(round(self.__linToSrgb(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s))))

    def __lerpOklab(self, rgbA, rgbB, t):
        labA, labB = self.__toOklab(rgbA), self.__toOklab(rgbB)
        mixed = tuple(labA[i] + (labB[i] - labA[i]) * t for i in range(3))
        return self.__fromOklab(mixed)

    # --- generic gauge maths -------------------------------------------------
    def gradientColorAt(self, value, anchors):
        # anchors: ordered list of (value, "#hex") stops along the metric axis (roast: descending 4.0/2.8/2.0).
        # Interpolate in OKLab within the bracketing segment; clamp to the end anchor beyond the range.
        rgbAnchors = [(v, self.hexToRgb(c)) for v, c in anchors]
        first, last = rgbAnchors[0], rgbAnchors[-1]
        # beyond the ends (RD#5: e.g. a >4.0 value clamps to the left/green anchor colour)
        loValue = min(first[0], last[0])
        hiValue = max(first[0], last[0])
        if value <= loValue:
            return self.rgbToHex(first[1] if first[0] == loValue else last[1])
        if value >= hiValue:
            return self.rgbToHex(first[1] if first[0] == hiValue else last[1])
        for (v0, c0), (v1, c1) in zip(rgbAnchors, rgbAnchors[1:]):
            if (v0 - value) * (v1 - value) <= 0 and v0 != v1:   # value lies within [v0, v1] (either order)
                t = (value - v0) / (v1 - v0)
                return self.rgbToHex(self.__lerpOklab(c0, c1, max(0.0, min(1.0, t))))
        return self.rgbToHex(last[1])

    def gradientStops(self, anchors, bandLeft, bandRight, steps=24):
        # n+1 (position, hex) stops sampled across the band, left(pos 0) -> right(pos 1), for the band fill.
        stops = []
        for i in range(steps + 1):
            pos = i / steps
            value = bandLeft + (bandRight - bandLeft) * pos
            stops.append((pos, self.gradientColorAt(value, anchors)))
        return stops

    def positionOf(self, value, bandLeft, bandRight):
        # marker position, linear in the metric, clamped to [0,1] (RD#5 — a value past an edge saturates here).
        if bandRight == bandLeft:
            return 0.0
        pos = (value - bandLeft) / (bandRight - bandLeft)
        return max(0.0, min(1.0, pos))

    def classify(self, value, thresholds, bandLeft, bandRight):
        # Which class a value falls in, orientation-aware (band may descend). classes are ordered left->right;
        # class index = number of threshold-boundaries the value has passed going left->right. A value sitting
        # exactly ON a boundary stays in the LEFT class (roast: 2.8 -> "good", spec §8.2).
        valuePos = self.positionOf(value, bandLeft, bandRight)
        thresholdPositions = sorted(self.positionOf(t, bandLeft, bandRight) for t in thresholds)
        index = 0
        for thresholdPos in thresholdPositions:
            if valuePos > thresholdPos:
                index += 1
            else:
                break
        return index
