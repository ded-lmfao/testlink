from revvlink.utils import ExtrasNamespace, Namespace


def test_namespace():
    ns = Namespace(a=1, b="two")
    assert ns.a == 1
    assert ns.b == "two"
    items = list(iter(ns))
    assert ("a", 1) in items
    assert ("b", "two") in items


def test_extras_namespace():
    ns = ExtrasNamespace({"hello": "world"}, stuff=1)
    assert ns.hello == "world"
    assert ns.stuff == 1

    # testing dict() conversion
    d = dict(ns)
    assert d == {"hello": "world", "stuff": 1}
