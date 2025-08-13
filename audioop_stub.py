import sys
import types


def ensure_audioop_stub() -> None:
    """audioopモジュールがインポートできない場合、スタブを提供します。
    """
    try:
        import audioop as _  # noqa: F401
    except Exception:
        mod = types.ModuleType("audioop")

        class AudioopError(Exception):
            pass

        mod.error = AudioopError

        def _passthrough(fragment, *args, **kwargs):
            return fragment

        def _ratecv(fragment, *args, **kwargs):
            return fragment, None

        def _adpcm_passthrough(fragment, *args, **kwargs):
            return fragment, None

        mod.mul = _passthrough
        mod.add = _passthrough
        mod.lin2lin = _passthrough
        mod.ratecv = _ratecv
        mod.tomono = _passthrough
        mod.tostereo = _passthrough
        mod.ulaw2lin = _passthrough
        mod.lin2ulaw = _passthrough
        mod.adpcm2lin = _adpcm_passthrough
        mod.lin2adpcm = _adpcm_passthrough
        sys.modules["audioop"] = mod
