"""
The MIT License (MIT)

Copyright (c) 2026-Present @JustNixx and @IamGroot

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypedDict, TypeVar

from .types.filters import (
    ChannelMix as ChannelMixPayload,
)
from .types.filters import (
    Distortion as DistortionPayload,
)
from .types.filters import (
    Equalizer as EqualizerPayload,
)
from .types.filters import (
    FilterPayload,
)
from .types.filters import (
    Karaoke as KaraokePayload,
)
from .types.filters import (
    LowPass as LowPassPayload,
)
from .types.filters import (
    Rotation as RotationPayload,
)
from .types.filters import (
    Timescale as TimescalePayload,
)
from .types.filters import (
    Tremolo as TremoloPayload,
)
from .types.filters import (
    Vibrato as VibratoPayload,
)

if TYPE_CHECKING:
    from typing_extensions import Self, Unpack


FT = TypeVar("FT")


__all__ = (
    "ChannelMix",
    "Distortion",
    "Equalizer",
    "Filters",
    "FiltersOptions",
    "Karaoke",
    "LowPass",
    "PluginFilters",
    "Rotation",
    "Timescale",
    "Tremolo",
    "Vibrato",
)


class FiltersOptions(TypedDict, total=False):
    volume: float
    equalizer: Equalizer
    karaoke: Karaoke
    timescale: Timescale
    tremolo: Tremolo
    vibrato: Vibrato
    rotation: Rotation
    distortion: Distortion
    channel_mix: ChannelMix
    low_pass: LowPass
    plugin_filters: PluginFilters
    reset: bool


class EqualizerOptions(TypedDict):
    bands: list[EqualizerPayload] | None


class KaraokeOptions(TypedDict):
    level: float | None
    mono_level: float | None
    filter_band: float | None
    filter_width: float | None


class RotationOptions(TypedDict):
    rotation_hz: float | None


class DistortionOptions(TypedDict):
    sin_offset: float | None
    sin_scale: float | None
    cos_offset: float | None
    cos_scale: float | None
    tan_offset: float | None
    tan_scale: float | None
    offset: float | None
    scale: float | None


class ChannelMixOptions(TypedDict):
    left_to_left: float | None
    left_to_right: float | None
    right_to_left: float | None
    right_to_right: float | None


class _BaseFilter(Generic[FT]):
    _payload: FT

    def __init__(self, payload: FT) -> None:
        self._payload = payload
        self._remove_none()

    def _remove_none(self) -> None:
        # Lavalink doesn't allow nullable types in any filters, but they are still not required...
        # Passing None makes it easier for the user to remove a field...
        self._payload = {k: v for k, v in self._payload.items() if v is not None}  # type: ignore


class Equalizer:
    """Equalizer Filter Class.

    There are 15 bands ``0`` to ``14`` that can be changed.
    Each band has a ``gain`` which is the multiplier for the given band. ``gain`` defaults to ``0``.

    Valid ``gain`` values range from ``-0.25`` to ``1.0``, where ``-0.25`` means
    the given band is completely muted,
    and ``0.25`` means it will be doubled.

    Modifying the ``gain`` could also change the volume of the output.
    """

    def __init__(self, payload: list[EqualizerPayload] | None = None) -> None:
        """Initialize an Equalizer filter.

        Parameters
        ----------
        payload: list[:class:`~revvlink.types.filters.Equalizer`] | None
            An optional list of 15 bands to initialize the equalizer with.
            Each dictionary should contain the keys ``band`` and ``gain``.
            If not provided, all bands will be initialized with a gain of ``0.0``.
        """
        if payload and len(payload) == 15:
            self._payload = self._set(payload)

        else:
            payload_: dict[int, EqualizerPayload] = {n: {"band": n, "gain": 0.0} for n in range(15)}
            self._payload = payload_

    def _set(self, payload: list[EqualizerPayload]) -> dict[int, EqualizerPayload]:
        default: dict[int, EqualizerPayload] = {n: {"band": n, "gain": 0.0} for n in range(15)}

        for eq in payload:
            band: int = eq["band"]
            if band > 14 or band < 0:
                continue

            default[band] = eq

        return default

    def set(self, **options: Unpack[EqualizerOptions]) -> Self:
        """Set the bands of the Equalizer.

        This method changes **all** bands, resetting any bands not provided to ``0.0``.

        Parameters
        ----------
        bands: list[:class:`~revvlink.types.filters.Equalizer`] | None
            A list of dictionary objects containing ``band`` and ``gain``.
            ``band`` must be an integer between ``0`` and ``14``.
            ``gain`` must be a float between ``-0.25`` and ``1.0``.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        default: dict[int, EqualizerPayload] = {n: {"band": n, "gain": 0.0} for n in range(15)}
        payload: list[EqualizerPayload] | None = options.get("bands", None)

        if payload is None:
            self._payload = default
            return self

        self._payload = self._set(payload)
        return self

    def reset(self) -> Self:
        """Reset the Equalizer to its default state.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload: dict[int, EqualizerPayload] = {
            n: {"band": n, "gain": 0.0} for n in range(15)
        }
        return self

    @property
    def payload(self) -> dict[int, EqualizerPayload]:
        """The raw payload associated with this filter.

        Returns
        -------
        dict[int, :class:`~revvlink.types.filters.Equalizer`]
            A copy of the equalizer payload.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "Equalizer"

    def __repr__(self) -> str:
        return f"<Equalizer: {self._payload}>"


class Karaoke(_BaseFilter[KaraokePayload]):
    """Karaoke Filter class.

    Uses equalization to eliminate part of a band, usually targeting vocals.
    """

    def __init__(self, payload: KaraokePayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[KaraokeOptions]) -> Self:
        """Set the properties of the Karaoke filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        level: float | None
            The vocal elimination level, between ``0.0`` and ``1.0``.
        mono_level: float | None
            The mono level, between ``0.0`` and ``1.0``.
        filter_band: float | None
            The filter band in Hz.
        filter_width: float | None
            The filter width.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload: KaraokePayload = {
            "level": options.get("level", self._payload.get("level")),
            "monoLevel": options.get("mono_level", self._payload.get("monoLevel")),
            "filterBand": options.get("filter_band", self._payload.get("filterBand")),
            "filterWidth": options.get("filter_width", self._payload.get("filterWidth")),
        }
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: KaraokePayload = {}
        return self

    @property
    def payload(self) -> KaraokePayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "Karaoke"

    def __repr__(self) -> str:
        return f"<Karaoke: {self._payload}>"


class Timescale(_BaseFilter[TimescalePayload]):
    """Timescale Filter class.

    Changes the speed, pitch, and rate.
    """

    def __init__(self, payload: TimescalePayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[TimescalePayload]) -> Self:
        """Set the properties of the Timescale filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        speed: float | None
            The playback speed.
        pitch: float | None
            The pitch multiplier.
        rate: float | None
            The rate multiplier.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload.update(options)
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: TimescalePayload = {}
        return self

    @property
    def payload(self) -> TimescalePayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "Timescale"

    def __repr__(self) -> str:
        return f"<Timescale: {self._payload}>"


class Tremolo(_BaseFilter[TremoloPayload]):
    """The Tremolo Filter class.

    Uses amplification to create a shuddering effect, where the volume quickly oscillates.
    Demo: https://en.wikipedia.org/wiki/File:Fuse_Electronics_Tremolo_MK-III_Quick_Demo.ogv
    """

    def __init__(self, payload: TremoloPayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[TremoloPayload]) -> Self:
        """Set the properties of the Tremolo filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        frequency: float | None
            The frequency of the oscillations.
        depth: float | None
            The tremolo depth.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload.update(options)
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: TremoloPayload = {}
        return self

    @property
    def payload(self) -> TremoloPayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "Tremolo"

    def __repr__(self) -> str:
        return f"<Tremolo: {self._payload}>"


class Vibrato(_BaseFilter[VibratoPayload]):
    """The Vibrato Filter class.

    Similar to tremolo. While tremolo oscillates the volume, vibrato oscillates the pitch.
    """

    def __init__(self, payload: VibratoPayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[VibratoPayload]) -> Self:
        """Set the properties of the Vibrato filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        frequency: float | None
            The frequency of the oscillations.
        depth: float | None
            The vibrato depth.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload.update(options)
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: VibratoPayload = {}
        return self

    @property
    def payload(self) -> VibratoPayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "Vibrato"

    def __repr__(self) -> str:
        return f"<Vibrato: {self._payload}>"


class Rotation(_BaseFilter[RotationPayload]):
    """The Rotation Filter class.

    Rotates the sound around the stereo channels/user headphones (aka Audio Panning).
    It can produce an effect similar to https://youtu.be/QB9EB8mTKcc (without the reverb).
    """

    def __init__(self, payload: RotationPayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[RotationOptions]) -> Self:
        """Set the properties of the Rotation filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        rotation_hz: float | None
            The frequency of the audio rotating around the listener in Hz.
            ``0.2`` is a good starting point.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload: RotationPayload = {
            "rotationHz": options.get("rotation_hz", self._payload.get("rotationHz"))
        }
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: RotationPayload = {}
        return self

    @property
    def payload(self) -> RotationPayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "Rotation"

    def __repr__(self) -> str:
        return f"<Rotation: {self._payload}>"


class Distortion(_BaseFilter[DistortionPayload]):
    """The Distortion Filter class.

    According to Lavalink "It can generate some pretty unique audio effects."
    """

    def __init__(self, payload: DistortionPayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[DistortionOptions]) -> Self:
        """Set the properties of the Distortion filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        sin_offset: float | None
            The sin offset.
        sin_scale: float | None
            The sin scale.
        cos_offset: float | None
            The cos offset.
        cos_scale: float | None
            The cos scale.
        tan_offset: float | None
            The tan offset.
        tan_scale: float | None
            The tan scale.
        offset: float | None
            The offset.
        scale: float | None
            The scale.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload: DistortionPayload = {
            "sinOffset": options.get("sin_offset", self._payload.get("sinOffset")),
            "sinScale": options.get("sin_scale", self._payload.get("sinScale")),
            "cosOffset": options.get("cos_offset", self._payload.get("cosOffset")),
            "cosScale": options.get("cos_scale", self._payload.get("cosScale")),
            "tanOffset": options.get("tan_offset", self._payload.get("tanOffset")),
            "tanScale": options.get("tan_scale", self._payload.get("tanScale")),
            "offset": options.get("offset", self._payload.get("offset")),
            "scale": options.get("scale", self._payload.get("scale")),
        }
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: DistortionPayload = {}
        return self

    @property
    def payload(self) -> DistortionPayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "Distortion"

    def __repr__(self) -> str:
        return f"<Distortion: {self._payload}>"


class ChannelMix(_BaseFilter[ChannelMixPayload]):
    """The ChannelMix Filter class.

    Mixes both channels (left and right), with a configurable factor on how much
    each channel affects the other.
    With the defaults, both channels are kept independent of each other.

    Setting all factors to ``0.5`` means both channels get the same audio.
    """

    def __init__(self, payload: ChannelMixPayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[ChannelMixOptions]) -> Self:
        """Set the properties of the ChannelMix filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        left_to_left: float | None
            The left to left channel mix factor. Between ``0.0`` and ``1.0``.
        left_to_right: float | None
            The left to right channel mix factor. Between ``0.0`` and ``1.0``.
        right_to_left: float | None
            The right to left channel mix factor. Between ``0.0`` and ``1.0``.
        right_to_right: float | None
            The right to right channel mix factor. Between ``0.0`` and ``1.0``.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload: ChannelMixPayload = {
            "leftToLeft": options.get("left_to_left", self._payload.get("leftToLeft")),
            "leftToRight": options.get("left_to_right", self._payload.get("leftToRight")),
            "rightToLeft": options.get("right_to_left", self._payload.get("rightToLeft")),
            "rightToRight": options.get("right_to_right", self._payload.get("rightToRight")),
        }
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: ChannelMixPayload = {}
        return self

    @property
    def payload(self) -> ChannelMixPayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "ChannelMix"

    def __repr__(self) -> str:
        return f"<ChannelMix: {self._payload}>"


class LowPass(_BaseFilter[LowPassPayload]):
    """The LowPass Filter class.

    Higher frequencies get suppressed, while lower frequencies pass through this filter,
    thus the name low pass.
    Any smoothing values equal to or less than ``1.0`` will disable the filter.
    """

    def __init__(self, payload: LowPassPayload) -> None:
        super().__init__(payload=payload)

    def set(self, **options: Unpack[LowPassPayload]) -> Self:
        """Set the properties of the LowPass filter.

        This method accepts keyword argument pairs.
        This method does not override existing settings if they are not provided.

        Parameters
        ----------
        smoothing: float | None
            The smoothing factor. Higher values mean more smoothing.
            Values ``<= 1.0`` disable the filter.

        Returns
        -------
        Self
            The current instance for chaining.
        """
        self._payload.update(options)
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: LowPassPayload = {}
        return self

    @property
    def payload(self) -> LowPassPayload:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "LowPass"

    def __repr__(self) -> str:
        return f"<LowPass: {self._payload}>"


class PluginFilters(_BaseFilter[dict[str, Any]]):
    """The PluginFilters class.

    This class handles setting filters on plugins that support setting filter values.
    See the documentation of the Lavalink Plugin for more information on the values
        that can be set.

    This class takes in a ``dict[str, Any]`` usually in the form of:

    .. code:: python3

        {"pluginName": {"filterKey": "filterValue"}, ...}


    .. warning::

        Do NOT include the ``"pluginFilters"`` top level key when setting your values
        for this class.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload=payload)

    def set(self, **options: dict[str, Any]) -> Self:
        """Set the properties of this filter.

        This method accepts keyword argument pairs OR you can alternatively unpack a dictionary.
        See the documentation of the Lavalink Plugin for more information on the values
        that can be set.

        Examples
        --------

        .. code:: python3

            plugin_filters: PluginFilters = PluginFilters()
            plugin_filters.set(pluginName={"filterKey": "filterValue", ...})

            # OR...

            plugin_filters.set(**{"pluginName": {"filterKey": "filterValue", ...}})
        """
        self._payload.update(options)
        self._remove_none()
        return self

    def reset(self) -> Self:
        """Reset this filter to its defaults."""
        self._payload: dict[str, Any] = {}
        return self

    @property
    def payload(self) -> dict[str, Any]:
        """The raw payload associated with this filter.

        This property returns a copy.
        """
        return self._payload.copy()

    def __str__(self) -> str:
        return "PluginFilters"

    def __repr__(self) -> str:
        return f"<PluginFilters: {self._payload}"


class Filters:
    """The revvlink Filters class.

    This class contains the information associated with each of Lavalinks filter objects,
    as Python classes.
    Each filter can be ``set`` or ``reset`` individually.

    Using ``set`` on an individual filter only updates any ``new`` values you pass.
    Using ``reset`` on an individual filter, resets its payload, and can be
    used before ``set`` when you want a clean state for that filter.

    See: :meth:`~revvlink.Filters.reset` to reset **every** individual filter.

    This class is already applied an instantiated on all new :class:`~revvlink.Player`.

    See: :meth:`~revvlink.Player.set_filters` for information on applying this class to
    your :class:`~revvlink.Player`.
    See: :attr:`~revvlink.Player.filters` for retrieving the applied filters.

    To retrieve the ``payload`` for this Filters class, you can call an instance of this class.

    Examples
    --------

    .. code:: python3

        import revvlink

        # Create a brand new Filters and apply it...
        # You can use player.set_filters() for an easier way to reset.
        filters: revvlink.Filters = revvlink.Filters()
        await player.set_filters(filters)


        # Retrieve the payload of any Filters instance...
        filters: revvlink.Filters = player.filters
        print(filters())


        # Set some filters...
        # You can set and reset individual filters at the same time...
        filters: revvlink.Filters = player.filters
        filters.timescale.set(pitch=1.2, speed=1.1, rate=1)
        filters.rotation.set(rotation_hz=0.2)
        filters.equalizer.reset()

        await player.set_filters(filters)


        # Reset a filter...
        filters: revvlink.Filters = player.filters
        filters.timescale.reset()

        await player.set_filters(filters)


        # Reset all filters...
        filters: revvlink.Filters = player.filters
        filters.reset()

        await player.set_filters(filters)


        # Reset and apply filters easier method...
        await player.set_filters()
    """

    def __init__(self, *, data: FilterPayload | None = None) -> None:
        self._volume: float | None = None
        self._equalizer: Equalizer = Equalizer(None)
        self._karaoke: Karaoke = Karaoke({})
        self._timescale: Timescale = Timescale({})
        self._tremolo: Tremolo = Tremolo({})
        self._vibrato: Vibrato = Vibrato({})
        self._rotation: Rotation = Rotation({})
        self._distortion: Distortion = Distortion({})
        self._channel_mix: ChannelMix = ChannelMix({})
        self._low_pass: LowPass = LowPass({})
        self._plugin_filters: PluginFilters = PluginFilters({})

        if data:
            self._create_from(data)

    def _create_from(self, data: FilterPayload) -> None:
        self._volume = data.get("volume")
        self._equalizer = Equalizer(data.get("equalizer", None))
        self._karaoke = Karaoke(data.get("karaoke", {}))
        self._timescale = Timescale(data.get("timescale", {}))
        self._tremolo = Tremolo(data.get("tremolo", {}))
        self._vibrato = Vibrato(data.get("vibrato", {}))
        self._rotation = Rotation(data.get("rotation", {}))
        self._distortion = Distortion(data.get("distortion", {}))
        self._channel_mix = ChannelMix(data.get("channelMix", {}))
        self._low_pass = LowPass(data.get("lowPass", {}))
        self._plugin_filters = PluginFilters(data.get("pluginFilters", {}))

    def _set_with_reset(self, filters: FiltersOptions) -> None:
        self._volume = filters.get("volume")
        self._equalizer = filters.get("equalizer", Equalizer(None))
        self._karaoke = filters.get("karaoke", Karaoke({}))
        self._timescale = filters.get("timescale", Timescale({}))
        self._tremolo = filters.get("tremolo", Tremolo({}))
        self._vibrato = filters.get("vibrato", Vibrato({}))
        self._rotation = filters.get("rotation", Rotation({}))
        self._distortion = filters.get("distortion", Distortion({}))
        self._channel_mix = filters.get("channel_mix", ChannelMix({}))
        self._low_pass = filters.get("low_pass", LowPass({}))
        self._plugin_filters = filters.get("plugin_filters", PluginFilters({}))

    def set_filters(self, **filters: Unpack[FiltersOptions]) -> None:
        """Set multiple filters at once to a standalone Filter object.
        To set the filters to the player directly see :meth:`revvlink.Player.set_filters`

        Parameters
        ----------
        volume: float
            The Volume filter to apply to the player.
        equalizer: :class:`revvlink.Equalizer`
            The Equalizer filter to apply to the player.
        karaoke: :class:`revvlink.Karaoke`
            The Karaoke filter to apply to the player.
        timescale: :class:`revvlink.Timescale`
            The Timescale filter to apply to the player.
        tremolo: :class:`revvlink.Tremolo`
            The Tremolo filter to apply to the player.
        vibrato: :class:`revvlink.Vibrato`
            The Vibrato filter to apply to the player.
        rotation: :class:`revvlink.Rotation`
            The Rotation filter to apply to the player.
        distortion: :class:`revvlink.Distortion`
            The Distortion filter to apply to the player.
        channel_mix: :class:`revvlink.ChannelMix`
            The ChannelMix filter to apply to the player.
        low_pass: :class:`revvlink.LowPass`
            The LowPass filter to apply to the player.
        plugin_filters: :class:`revvlink.PluginFilters`
            The extra Plugin Filters to apply to the player. See
            :class:`~revvlink.PluginFilters` for more details.
        reset: bool
            Whether to reset all filters that were not specified.
        """

        reset: bool = filters.get("reset", False)
        if reset:
            self._set_with_reset(filters)
            return

        self._volume = filters.get("volume", self._volume)
        self._equalizer = filters.get("equalizer", self._equalizer)
        self._karaoke = filters.get("karaoke", self._karaoke)
        self._timescale = filters.get("timescale", self._timescale)
        self._tremolo = filters.get("tremolo", self._tremolo)
        self._vibrato = filters.get("vibrato", self._vibrato)
        self._rotation = filters.get("rotation", self._rotation)
        self._distortion = filters.get("distortion", self._distortion)
        self._channel_mix = filters.get("channel_mix", self._channel_mix)
        self._low_pass = filters.get("low_pass", self._low_pass)
        self._plugin_filters = filters.get("plugin_filters", self._plugin_filters)

    def _reset(self) -> None:
        self._volume = None
        self._equalizer = Equalizer(None)
        self._karaoke = Karaoke({})
        self._timescale = Timescale({})
        self._tremolo = Tremolo({})
        self._vibrato = Vibrato({})
        self._rotation = Rotation({})
        self._distortion = Distortion({})
        self._channel_mix = ChannelMix({})
        self._low_pass = LowPass({})
        self._plugin_filters = PluginFilters({})

    def reset(self) -> None:
        """Method which resets this object to an original state.

        This method will clear all individual filters, and assign the revvlink default classes.
        """
        self._reset()

    @classmethod
    def from_filters(cls, **filters: Unpack[FiltersOptions]) -> Self:
        """Creates a Filters object with specified filters.

        Parameters
        ----------
        volume: float
            The Volume filter to apply to the player.
        equalizer: :class:`revvlink.Equalizer`
            The Equalizer filter to apply to the player.
        karaoke: :class:`revvlink.Karaoke`
            The Karaoke filter to apply to the player.
        timescale: :class:`revvlink.Timescale`
            The Timescale filter to apply to the player.
        tremolo: :class:`revvlink.Tremolo`
            The Tremolo filter to apply to the player.
        vibrato: :class:`revvlink.Vibrato`
            The Vibrato filter to apply to the player.
        rotation: :class:`revvlink.Rotation`
            The Rotation filter to apply to the player.
        distortion: :class:`revvlink.Distortion`
            The Distortion filter to apply to the player.
        channel_mix: :class:`revvlink.ChannelMix`
            The ChannelMix filter to apply to the player.
        low_pass: :class:`revvlink.LowPass`
            The LowPass filter to apply to the player.
        plugin_filters: :class:`revvlink.PluginFilters`
            The extra Plugin Filters to apply to the player. See
            :class:`~revvlink.PluginFilters` for more details.
        reset: bool
            Whether to reset all filters that were not specified.
        """

        self = cls()
        self._set_with_reset(filters)

        return self

    @property
    def volume(self) -> float | None:
        """The volume multiplier for the player.

        Adjusts the volume multiplier for the player from ``0.0`` to ``5.0``,
        where ``1.0`` is 100%. Values ``> 1.0`` may cause clipping.

        Returns
        -------
        float | None
            The current volume multiplier, or ``None`` if not set.
        """
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        self._volume = value

    @property
    def equalizer(self) -> Equalizer:
        """Property which returns the :class:`~revvlink.Equalizer` filter associated with
        this Filters payload."""
        return self._equalizer

    @property
    def karaoke(self) -> Karaoke:
        """Property which returns the :class:`~revvlink.Karaoke` filter associated with
        this Filters payload."""
        return self._karaoke

    @property
    def timescale(self) -> Timescale:
        """The :class:`~revvlink.Timescale` filter associated with this payload.

        Returns
        -------
        :class:`~revvlink.Timescale`
            The timescale filter.
        """
        return self._timescale

    @property
    def tremolo(self) -> Tremolo:
        """Property which returns the :class:`~revvlink.Tremolo` filter associated with
        this Filters payload."""
        return self._tremolo

    @property
    def vibrato(self) -> Vibrato:
        """Property which returns the :class:`~revvlink.Vibrato` filter associated with
        this Filters payload."""
        return self._vibrato

    @property
    def rotation(self) -> Rotation:
        """Property which returns the :class:`~revvlink.Rotation` filter associated with
        this Filters payload."""
        return self._rotation

    @property
    def distortion(self) -> Distortion:
        """Property which returns the :class:`~revvlink.Distortion` filter associated with
        this Filters payload."""
        return self._distortion

    @property
    def channel_mix(self) -> ChannelMix:
        """Property which returns the :class:`~revvlink.ChannelMix` filter associated with
        this Filters payload."""
        return self._channel_mix

    @property
    def low_pass(self) -> LowPass:
        """Property which returns the :class:`~revvlink.LowPass` filter associated with
        this Filters payload."""
        return self._low_pass

    @property
    def plugin_filters(self) -> PluginFilters:
        """The :class:`~revvlink.PluginFilters` associated with this payload.

        Returns
        -------
        :class:`~revvlink.PluginFilters`
            The plugin filters.
        """
        return self._plugin_filters

    def __call__(self) -> FilterPayload:
        """Retrieve the raw payload for this :class:`Filters` class.

        Returns
        -------
        :class:`~revvlink.types.filters.FilterPayload`
            The raw filter payload for Lavalink.
        """
        payload: FilterPayload = {
            "volume": self._volume,
            "equalizer": list(self._equalizer._payload.values()),
            "karaoke": self._karaoke._payload,
            "timescale": self._timescale._payload,
            "tremolo": self._tremolo._payload,
            "vibrato": self._vibrato._payload,
            "rotation": self._rotation._payload,
            "distortion": self._distortion._payload,
            "channelMix": self._channel_mix._payload,
            "lowPass": self._low_pass._payload,
            "pluginFilters": self._plugin_filters._payload,
        }

        for key, value in payload.copy().items():
            if not value:
                del payload[key]

        return payload

    def __repr__(self) -> str:
        return (
            f"<Filters: volume={self._volume}, equalizer={self._equalizer!r}, "
            f"karaoke={self._karaoke!r},"
            f" timescale={self._timescale!r}, tremolo={self._tremolo!r}, vibrato={self._vibrato!r},"
            f" rotation={self._rotation!r}, distortion={self._distortion!r}, "
            f"channel_mix={self._channel_mix!r},"
            f" low_pass={self._low_pass!r}, plugin_filters={self._plugin_filters!r}>"
        )
