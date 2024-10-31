import importlib
import pkgutil

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins = {}

    def load_plugins(self):
        self.plugins = {}
        for loader, name, is_pkg in pkgutil.iter_modules(['plugins']):
            try:
                module = importlib.import_module(f'plugins.{name}')
                plugin_class = getattr(module, 'Plugin', None)
                if plugin_class:
                    self.plugins[name] = plugin_class(self.app)
            except Exception as e:
                print(f"Ошибка при загрузке плагина {name}: {e}")

    def apply_plugins(self, text):
        for plugin in self.plugins.values():
            try:
                text = plugin.process(text)
            except Exception as e:
                print(f"Ошибка в плагине {plugin}: {e}")
        return text
