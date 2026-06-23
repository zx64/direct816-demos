from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ty_extensions import JustFloat

else:
    JustFloat = float

RGB_F32 = tuple[JustFloat, JustFloat, JustFloat]
RGB_U8 = tuple[int, int, int]


if TYPE_CHECKING:
    from colorsys import hsv_to_rgb

    # Trivial wrapper that is easier for the type checker to reason about
    def hsv(h: float, s: float, v: float) -> RGB_F32:
        r, g, b = hsv_to_rgb(h, s, v)
        assert isinstance(r, float)
        assert isinstance(g, float)
        assert isinstance(b, float)
        return r, g, b
else:
    from colorsys import hsv_to_rgb as hsv  # noqa: F401
