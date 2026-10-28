import colorsys


CRYPTO_COLORS = {
    "BTC-USD": "#F7931A",
    "ETH-USD": "#627EEA",
    "SOL-USD": "#14F195",
    "ADA-USD": "#0033FF",
}


def get_crypto_colors(assets: list[str]) -> dict[str, str]:
    """Return a stable color map for selected assets."""
    colors: dict[str, str] = {}

    for index, asset in enumerate(assets):
        if asset in CRYPTO_COLORS:
            colors[asset] = CRYPTO_COLORS[asset]
            continue

        hue = (index / max(len(assets), 1)) % 1.0
        saturation = 0.7 + (index % 3) * 0.1
        value = 0.8 + (index % 2) * 0.15
        rgb = colorsys.hsv_to_rgb(hue, saturation, value)
        colors[asset] = "#{:02x}{:02x}{:02x}".format(
            int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
        )

    return colors
