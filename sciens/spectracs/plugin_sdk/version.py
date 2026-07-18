"""
plugin_sdk version + compatibility gate (SPEC_plugin_distribution.md §4 / §8 A2).

The SDK ships INSIDE the app — exactly one per build, never distributed; only the *plugin* travels. So the
only question at load time is: the app has SDK N, this plugin targets M — safe? The rule is strict equality
(§4: no back-compat promise; Edwin controls both sides and rebuilds any plugin). Its whole job is a GOOD
ERROR MESSAGE — an honest "this plugin needs a newer app" instead of a mystery AttributeError three phases
deep.

Kept in its own tiny, dependency-free module (not in __init__.py) so SpectralPlugin can import SDK_VERSION
without a package-init import cycle.
"""

# Bump ONLY on a breaking change to the plugin_sdk surface. A plugin declares the SDK it was built against
# via SpectralPlugin.targetSdkVersion (default = this value).
SDK_VERSION = 1


class PluginSdkVersionError(Exception):
    """A plugin targets an SDK this app build does not provide."""


def checkSdkCompatibleVersion(targetSdkVersion, name: str = "plugin") -> None:
    """Raise PluginSdkVersionError unless `targetSdkVersion == SDK_VERSION`. Directional message: a newer
    target means "update the app"; an older one means "rebuild the plugin". The DB loader (B3) calls this with
    the sealed row's targetSdkVersion BEFORE exec'ing — so an incompatible plugin fails with a clear message
    instead of running and AttributeError-ing three phases deep."""
    if targetSdkVersion == SDK_VERSION:
        return
    if targetSdkVersion > SDK_VERSION:
        raise PluginSdkVersionError(
            "Plugin “%s” needs a newer app: it targets plugin-SDK %s, but this app ships SDK %s. "
            "Please update the app." % (name, targetSdkVersion, SDK_VERSION))
    raise PluginSdkVersionError(
        "Plugin “%s” is built for an older app: it targets plugin-SDK %s, but this app ships SDK "
        "%s. Rebuild the plugin against the current SDK." % (name, targetSdkVersion, SDK_VERSION))


def checkSdkCompatible(plugin) -> None:
    """As above, reading targetSdkVersion off a plugin instance. In-app plugins share the build's SDK by
    construction, so this is inert for them — it lights up for DB-delivered plugins (B3)."""
    checkSdkCompatibleVersion(
        getattr(plugin, "targetSdkVersion", SDK_VERSION),
        getattr(plugin, "title", None) or type(plugin).__name__)
