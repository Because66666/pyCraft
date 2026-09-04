"""
A simple JSON file cache, ported from ``prismarine-auth``
(``src/common/cache/FileCache.js``).

Note that cached data includes access and refresh tokens; cache files
must be kept private and never committed or logged.
"""
import json
import os


class FileCache(object):
    """
    Persists a dictionary as JSON in a single file. The data is loaded
    lazily on first access and kept in memory afterwards.
    """

    def __init__(self, cache_location):
        """
        Parameters:
            cache_location - Path of the JSON cache file.
        """
        self.cache_location = cache_location
        self._cache = None

    def reset(self):
        """
        Clears the cache, overwriting the cache file with ``{}``.
        """
        self._cache = {}
        self._write()
        return self._cache

    def load_initial_value(self):
        """
        Reads the cache file, resetting it if it is missing or corrupt.
        """
        try:
            with open(self.cache_location, "r") as cache_file:
                return json.load(cache_file)
        except (IOError, OSError, ValueError):
            return self.reset()

    def get_cached(self):
        """
        Returns the whole cached dictionary.
        """
        if self._cache is None:
            self._cache = self.load_initial_value()
        return self._cache

    def set_cached(self, cached):
        """
        Replaces the cached dictionary and writes it to disk.
        """
        self._cache = cached
        self._write()

    def set_cached_partial(self, cached):
        """
        Merges ``cached`` into the cached dictionary (shallow update)
        and writes the result to disk.
        """
        new_cache = self.get_cached().copy()
        new_cache.update(cached)
        self.set_cached(new_cache)

    def _write(self):
        directory = os.path.dirname(os.path.abspath(self.cache_location))
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(self.cache_location, "w") as cache_file:
            json.dump(self._cache, cache_file)
