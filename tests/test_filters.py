import pytest

from revvlink.filters import (
    ChannelMix,
    Distortion,
    Equalizer,
    Filters,
    Karaoke,
    LowPass,
    PluginFilters,
    Rotation,
    Timescale,
    Tremolo,
    Vibrato,
)


def test_equalizer():
    eq = Equalizer()
    assert len(eq.payload) == 15
    assert eq.payload[0]["gain"] == pytest.approx(0.0)

    # set with full 15 bands payload
    bands = [{"band": i, "gain": 0.1} for i in range(15)]
    eq.set(bands=bands)
    assert eq.payload[0]["gain"] == pytest.approx(0.1)

    # set with out-of-range band (should be ignored)
    eq.set(bands=[{"band": 99, "gain": 0.5}, {"band": 0, "gain": 0.9}])
    assert eq.payload[0]["gain"] == pytest.approx(0.9)

    # set with None bands (reset behaviour)
    eq.set(bands=None)
    assert eq.payload[0]["gain"] == pytest.approx(0.0)

    eq.reset()
    assert eq.payload[0]["gain"] == pytest.approx(0.0)

    assert str(eq) == "Equalizer"
    assert "Equalizer" in repr(eq)

    # Initialise with partial payload (not 15 bands)
    eq2 = Equalizer([{"band": 0, "gain": 0.5}])
    assert eq2.payload[0]["gain"] == pytest.approx(
        0.0
    )  # Should fall back to default (not 15 bands)


def test_karaoke():
    kar = Karaoke({"level": 1.0})
    assert kar.payload["level"] == pytest.approx(1.0)

    kar.set(mono_level=0.5, filter_band=220.0, filter_width=100.0)
    assert kar.payload["monoLevel"] == pytest.approx(0.5)
    assert kar.payload["filterBand"] == pytest.approx(220.0)

    kar.reset()
    assert kar.payload == {}

    assert str(kar) == "Karaoke"
    assert "Karaoke" in repr(kar)


def test_timescale():
    ts = Timescale({})
    ts.set(speed=1.5, pitch=1.2, rate=1.0)
    assert ts.payload["speed"] == pytest.approx(1.5)
    assert ts.payload["pitch"] == pytest.approx(1.2)

    ts.reset()
    assert ts.payload == {}

    assert str(ts) == "Timescale"
    assert "Timescale" in repr(ts)


def test_tremolo():
    tr = Tremolo({})
    tr.set(frequency=2.0, depth=0.5)
    assert tr.payload["frequency"] == pytest.approx(2.0)

    tr.reset()
    assert tr.payload == {}

    assert str(tr) == "Tremolo"
    assert "Tremolo" in repr(tr)


def test_vibrato():
    vb = Vibrato({})
    vb.set(frequency=2.0, depth=0.5)
    assert vb.payload["frequency"] == pytest.approx(2.0)

    vb.reset()
    assert vb.payload == {}

    assert str(vb) == "Vibrato"
    assert "Vibrato" in repr(vb)


def test_rotation():
    rot = Rotation({})
    rot.set(rotation_hz=0.2)
    assert rot.payload["rotationHz"] == pytest.approx(0.2)

    rot.reset()
    assert rot.payload == {}

    assert str(rot) == "Rotation"
    assert "Rotation" in repr(rot)


def test_distortion():
    dis = Distortion({})
    dis.set(sin_offset=0.1, sin_scale=1.0)
    assert dis.payload["sinOffset"] == pytest.approx(0.1)

    dis.reset()
    assert dis.payload == {}

    assert str(dis) == "Distortion"
    assert "Distortion" in repr(dis)


def test_channel_mix():
    cm = ChannelMix({})
    cm.set(left_to_left=1.0, right_to_left=0.5)
    assert cm.payload["leftToLeft"] == pytest.approx(1.0)
    assert cm.payload["rightToLeft"] == pytest.approx(0.5)

    cm.reset()
    assert cm.payload == {}

    assert str(cm) == "ChannelMix"
    assert "ChannelMix" in repr(cm)


def test_low_pass():
    lp = LowPass({})
    lp.set(smoothing=20.0)
    assert lp.payload["smoothing"] == pytest.approx(20.0)

    lp.reset()
    assert lp.payload == {}

    assert str(lp) == "LowPass"


def test_plugin_filters():
    pf = PluginFilters({})
    pf.set(**{"echo": {"delay": 1.0}})
    assert pf.payload["echo"]["delay"] == pytest.approx(1.0)

    pf.reset()
    assert pf.payload == {}

    assert str(pf) == "PluginFilters"
    assert "PluginFilters" in repr(pf)


def test_filters_properties():
    filters = Filters()

    assert filters.equalizer is not None
    assert filters.karaoke is not None
    assert filters.timescale is not None
    assert filters.tremolo is not None
    assert filters.vibrato is not None
    assert filters.rotation is not None
    assert filters.distortion is not None
    assert filters.channel_mix is not None
    assert filters.low_pass is not None
    assert filters.plugin_filters is not None
    assert filters.volume is None

    filters.volume = 1.5
    assert filters.volume == pytest.approx(1.5)

    assert "Filters" in repr(filters)


def test_filters_call():
    filters = Filters()
    filters.timescale.set(speed=2.0)
    filters.volume = 0.8

    payload = filters()
    assert payload["timescale"]["speed"] == pytest.approx(2.0)
    assert payload["volume"] == pytest.approx(0.8)


def test_filters_set_filters():
    filters = Filters()
    eq = Equalizer()
    ts = Timescale({})
    ts.set(speed=1.5)

    filters.set_filters(equalizer=eq, timescale=ts, volume=0.5)
    assert filters.volume == pytest.approx(0.5)
    assert filters.timescale.payload["speed"] == pytest.approx(1.5)

    # With reset=True
    filters.set_filters(reset=True, volume=2.0)
    assert filters.volume == pytest.approx(2.0)
    assert filters.timescale.payload == {}


def test_filters_from_filters():
    ts = Timescale({})
    ts.set(speed=1.5)

    filters = Filters.from_filters(timescale=ts, volume=1.0)
    assert filters.volume == pytest.approx(1.0)
    assert filters.timescale.payload["speed"] == pytest.approx(1.5)


def test_filters_collection():
    filters = Filters()
    filters.timescale.set(speed=2.0)
    filters.karaoke.set(level=1.0)

    filters.reset()
    assert filters.timescale.payload == {}
    assert filters.karaoke.payload == {}


def test_filters_from_data():
    data = {
        "volume": 1.0,
        "equalizer": [{"band": i, "gain": 0.0} for i in range(15)],
        "karaoke": {"level": 0.5},
        "timescale": {"speed": 1.1},
        "tremolo": {},
        "vibrato": {},
        "rotation": {"rotationHz": 0.2},
        "distortion": {},
        "channelMix": {"leftToLeft": 1.0},
        "lowPass": {"smoothing": 20.0},
        "pluginFilters": {},
    }

    filters = Filters(data=data)
    assert filters.volume == pytest.approx(1.0)
    assert filters.rotation.payload.get("rotationHz") == pytest.approx(0.2)
    assert filters.karaoke.payload.get("level") == pytest.approx(0.5)
