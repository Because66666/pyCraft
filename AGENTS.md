# AGENTS.md

Guidance for AI coding agents working in this repository. Assumes no prior
knowledge of the project.

## Project overview

**pyCraft** (version `0.7.0`, defined in `minecraft/__init__.py`) is a Python
library for communicating with a Minecraft server as a client. It implements
the Minecraft networking protocol (handshake, status, login, configuration,
and play states — the configuration state exists in protocols 764+,
i.e. Minecraft 1.20.2 and later), encryption, and Mojang/Yggdrasil
authentication. It supports Minecraft
releases 1.8 through 26.1.2 (plus many snapshots and some 1.7.x releases);
the authoritative list of supported versions and protocol numbers is
`KNOWN_MINECRAFT_VERSION_RECORDS` in `minecraft/__init__.py`.

Only a subset of packets is implemented: those needed to stay connected,
chat, and a few others. New packet support is added by writing packet classes
under `minecraft/networking/packets/`.

`start.py` is a runnable example headless client (`python start.py --help`).

## Technology stack and packaging

- Pure Python; targets Python 3.5–3.9 and PyPy (see `tox.ini` envlist and
  `README.rst`). `setup.py` classifiers also mention Python 2.7, but the
  README and CI treat Python 3 as the supported line.
- Packaging is **setuptools via `setup.py`** — there is no `pyproject.toml`
  or `setup.cfg`. Runtime dependencies (also in `setup.py`): `cryptography>=1.5`,
  `requests`, `pynbt`. `requirements.txt` contains only `-e .` (install the
  package itself in editable mode to get its dependencies).
- Version is read from `minecraft.__version__` by `setup.py`.
- `MANIFEST.in` controls the sdist contents and is checked by the
  `verify-manifest` tox env (`check-manifest`).

## Build and test commands

Setup:

```bash
pip install -r requirements.txt   # installs pyCraft editable + dependencies
```

Running tests (nose is the test runner):

```bash
pip install nose nose-timer
nosetests                          # run the whole suite
nosetests tests/test_connection.py # a single module
```

The full matrix is driven by tox (this is what CI runs):

```bash
pip install tox
tox                 # all envs: py35..py39, pypy, flake8, pylint, verify-manifest
tox -e py39         # tests + coverage (branch coverage, min 60%)
tox -e flake8       # style check
tox -e pylint-errors  # pylint, errors only (must pass)
tox -e pylint-full    # pylint without errors (advisory; failure tolerated)
tox -e verify-manifest
```

Documentation (Sphinx, hosted on Read the Docs):

```bash
bin/build_docs      # or: cd docs && make html  (needs sphinx, sphinx-rtd-theme)
```

CI is Travis CI (`.travis.yml`): one job per tox env, coverage uploaded to
Coveralls from the `py39` job. `bin/generate_travis_yml.py` regenerates
`.travis.yml`; `bin/clean` removes build/test artifacts.

## Repository layout

- `minecraft/` — the installable package.
  - `__init__.py` — version registry: `KNOWN_MINECRAFT_VERSION_RECORDS` and
    the derived globals (`SUPPORTED_MINECRAFT_VERSIONS`,
    `SUPPORTED_PROTOCOL_VERSIONS`, `PROTOCOL_VERSION_INDICES`, ...).
    `initglobals()` re-derives them; users may mutate the records at runtime
    and call it again to add dynamic version support.
  - `authentication.py` — Mojang/Yggdrasil authentication (`AuthenticationToken`,
    profile joining/refreshing) built on `requests`, plus
    `MicrosoftAuthenticationToken` (Microsoft device-code login, mimicking
    node-minecraft-protocol's `src/client/microsoftAuth.js`).
  - `microsoft/` — Microsoft (MSA) authentication component ported from
    `prismarine-auth`. Only the OAuth 2.0 **device-code** flow is implemented
    (no passwords). Chain: `live_token_manager.py` (login.live.com device
    code) → `xbox_token_manager.py` (XBL user/device/title + XSTS, with
    proof-of-possession ES256 request signing on `cryptography`) →
    `java_token_manager.py` (api.minecraftservices.com token/profile/
    certificates), orchestrated by `auth_flow.py` (`MicrosoftAuthFlow`).
    Tokens are cached as JSON files via `cache.py` (`FileCache`), named
    `<sha1(username)[:6]>_{live,xbl,mca}-cache.json` (same scheme as
    prismarine-auth); default cache dir is `~/.minecraft/nmp-cache`.
  - `exceptions.py` — custom exception hierarchy (e.g. `YggdrasilError`,
    `VersionMismatch`, `LoginDisconnect`, `IgnorePacket`, `InvalidState`).
  - `utility.py` — version-comparison helpers (protocol versions are compared
    by chronological release order, not numeric order).
  - `networking/connection.py` (~880 lines) — the core `Connection` class
    (socket handling, threads for read/write/react, compression, encryption
    setup) and `ConnectionContext` (carries `protocol_version` and offers
    `protocol_earlier`/`protocol_later`/... comparisons).
  - `networking/encryption.py` — AES/CFB8 socket wrappers and RSA helpers on
    top of `cryptography`.
  - `networking/types/` — protocol data types. `basic.py` (VarInt, String,
    Position, NBT, etc.), `enum.py` (`Enum`, `BitFieldEnum`), `utility.py`
    (e.g. `overridable_property`).
  - `networking/packets/` — packet classes, organized by **direction**
    (`clientbound/`, `serverbound/`) and then by **protocol state**
    (`handshake/`, `status/`, `login/`, `configuration/` (protocols 764+),
    `play/`). Shared machinery lives at
    the top level: `packet.py` (base `Packet`), `packet_buffer.py`,
    `packet_listener.py`, `keep_alive_packet.py`, `plugin_message_packet.py`.
- `tests/` — nose/unittest test suite plus `fake_server.py`, an in-process
  fake Minecraft server used to test `Connection` end-to-end.
  `tests/encryption/` holds RSA key fixtures (`.bin` files, shipped via
  `MANIFEST.in`).
- `docs/` — Sphinx documentation sources (`index.rst`, `authentication.rst`,
  `connecting.rst`).
- `start.py` — example headless client.
- `examples/` — standalone runnable example scripts referenced by
  `TUTORIAL.md` (`connect_offline.py`, `connect_microsoft.py`,
  `chat_bot.py` — Microsoft device-code login with listeners for every
  implemented clientbound packet type — and `custom_packet.py`). Each
  inserts the repo root into `sys.path` so it can run from a checkout.
- `bin/` — maintenance scripts (shell + Python).
- `node-minecraft-protocol-master/` — **untracked** vendored copy of the
  Node.js `node-minecraft-protocol` project, kept locally for reference only.
  It is not part of the package, tests, or build; do not modify or rely on it.
- `prismarine-auth-master/` — **untracked** vendored copy of the Node.js
  `prismarine-auth` project, kept locally as the reference for the port in
  `minecraft/microsoft/`; do not modify or rely on it.

## How packets are defined (key convention)

A packet is a subclass of `minecraft.networking.packets.Packet`. To define
one:

- Set the class attribute `id` (int), **or** override `get_id(context)` when
  the ID varies across protocol versions.
- Set the class attribute `definition` — a list of single-key dicts mapping
  field name to a type from `minecraft.networking.types`, e.g.
  `[{'keep_alive_id': VarInt}]` — **or** override `get_definition(context)`
  when the layout varies, **or** override `read`/`write_fields` for layouts
  that don't fit a simple field list.
- Version-dependent behavior keys off the `ConnectionContext` (its
  `protocol_version` and `protocol_earlier(...)` helpers).
- Enum-valued fields get a nested `Enum` subclass named after the field in
  CamelCase (see `Packet.field_enum`).
- New code should use the classes under `packets.clientbound.*` /
  `packets.serverbound.*`. `packets/__init__.py` re-exports a legacy,
  oddly-named subset purely for backward compatibility — do not extend it.

## Protocol upgrades

When adding support for a new Minecraft protocol version:

1. Add the version record(s) to `KNOWN_MINECRAFT_VERSION_RECORDS` in
   `minecraft/__init__.py` (chronological order, correct protocol number).
2. Diff the new protocol against the previous one (the vendored
   `minecraft-data-master/data/pc/<version>/protocol.json` and
   `node-minecraft-protocol-master` are the local references) and update
   every affected packet's `get_id(context)` cascade and, where the layout
   changed, its `get_definition(context)` / `read` / `write_fields`.
3. Run the full test suite (`tests/test_packets.py` round-trips every
   packet class for every supported protocol version, so ID or definition
   mistakes at the new protocol surface there).
4. **Sync the documentation**: update the supported-version lists in
   `README.rst` and `README.md`, and review `TUTORIAL.md` and the scripts
   under `examples/` — whenever the protocol change affects what they
   describe or demonstrate (changed packet structures or fields they use,
   new login/connection flow, new version lists), update them to match;
   if the change does not affect them, no edit is needed.
5. Update this `AGENTS.md` if any documented facts changed (e.g. the
   supported-version range in "Project overview").

## Testing instructions and strategy

- Test runner is **nose** on top of `unittest` classes; tests live in
  `tests/test_*.py`.
- `tests/fake_server.py` provides `_FakeServerTest`: it spins up a real
  local socket server that speaks the protocol, runs a `Connection` against
  it, and drives the scenario via an inner `client_handler_type` class
  (see `tests/test_connection.py` for the pattern). Raise
  `FakeServerTestSuccess` / `FakeServerDisconnect` from handlers to end a
  scenario.
- `tests/test_packets.py` performs generic serialization round-trip tests
  over **all** packet classes for **all** supported protocol versions — so a
  new or changed packet class is exercised automatically; its fields must be
  readable/writable for every supported version (with and without context).
- Some tests in `tests/test_authentication.py` hit Mojang's real servers and
  run only when the environment variable `PYCRAFT_RUN_INTERNET_TESTS` is set
  (tox sets it in the `py39` env).
- Coverage: branch coverage is measured on the `py39` tox env with a 60%
  minimum.

## Code style guidelines

- Code, comments, and docs are in **English**; documentation files use
  reStructuredText (`.rst`).
- Enforced style: `flake8` over `minecraft tests setup.py start.py
  bin/generate_travis_yml.py` (no custom flake8 config — defaults apply,
  i.e. 79-char lines — with per-file ignores declared in `tox.ini`), plus
  `pylint -E` (errors only) using `pylintrc` (`max-line-length=100`).
  Full pylint is advisory and its tox env may fail.
- Style follows PEP 8: 4-space indentation, `snake_case` for
  functions/variables, `CamelCase` for classes. Docstrings use single or
  triple quotes with the existing reST-ish phrasing.
- The codebase retains Python-2-era idioms in places (e.g.
  `class X(object):`, `super(ClassName, self)`); match the surrounding code
  rather than modernizing wholesale.
- Keep backward compatibility: public names re-exported in
  `minecraft/networking/packets/__init__.py` must not be broken (there is a
  dedicated `tests/test_backward_compatible.py`).

## Security considerations

- `minecraft/authentication.py` and `start.py` handle Mojang account
  credentials and access tokens. Never log, print, or commit credentials or
  tokens; `.gitignore` already excludes a `credentials` file.
- The Microsoft token caches written by `minecraft/microsoft/cache.py`
  (default `~/.minecraft/nmp-cache/*.json`) contain live access and refresh
  tokens. Never log, print, or commit them either.
- `minecraft/networking/encryption.py` implements Minecraft's encryption
  handshake (RSA key exchange + AES/CFB8 stream cipher with the shared secret
  as both key and IV — this mirrors the protocol, don't "fix" it). Use the
  `cryptography` library for any crypto changes, never hand-rolled crypto.
- `tests/encryption/*.bin` are test-only RSA key fixtures, not real secrets.
- Internet-dependent auth tests are opt-in via `PYCRAFT_RUN_INTERNET_TESTS`;
  don't enable network calls in tests by default.
