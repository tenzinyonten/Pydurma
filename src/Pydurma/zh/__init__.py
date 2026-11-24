# collate_chinese and merge_chinese are loaded on first use, so that importing a
# module of this package (e.g. from a weigher) doesn't import collate.py, which
# imports the weighers itself (circular import)
__all__ = ["collate_chinese", "merge_chinese"]


def __getattr__(name):
    if name in __all__:
        from Pydurma.zh import collate
        return getattr(collate, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
