# COVAS-NEXT-PLUGINS

> **Platform support:** This software is developed and tested on Windows. It has not been tested on Linux, and compatibility or correct operation on Linux is not guaranteed.

> **Status:** Chromas Next 1.0.0 and Covasify 4.2.0 are published. Archived Covinance and Songbird source packages are also retained publicly for reference.

This project contains plugin packages for [COVAS:NEXT](https://ratherrude.github.io/Elite-Dangerous-AI-Integration/).

The repository currently centers on **Covasify**, the maintained Spotify integration, and **Chromas Next**, the dedicated COVAS:NEXT integration for the separate **Elite Dangerous Lighting** application. Older plugins are retained only for historical/reference purposes.

## Development Transparency and AI use

The projects in this repository are developed with substantial generative-AI assistance under human direction.

Project goals, requirements, architecture, design decisions, testing, physical validation where applicable, acceptance criteria, maintenance direction, and publication are directed by **DocTrintignant**. AI-generated code is reviewed and tested before being accepted, but users should understand that these are non-commercial passion projects maintained by a non-professional and may still contain defects or inefficiencies. Download and use at your own discretion.

## Plugins

### Covasify — Maintained

**Covasify 4.2.0** is the actively maintained COVAS:NEXT Spotify integration. It lets COVAS search for and play music, control Spotify playback, manage track bindings, and expose now-playing information.

Covasify can also participate in **Elite Dangerous Lighting** Modes as an optional music/media listener. EDL itself remains standalone; COVAS:NEXT control of EDL belongs to the separate **Chromas Next** plugin.

For EDL Mode music, **Covasify 4.2.0 or newer is required**. In the Chromas Next settings page, enable **Enable Covasify bridge for Mode audio**. When enabled, Chromas Next passes a media cue to Covasify only after EDL has accepted and started the Mode. Covasify handles Spotify playback only; it does not own EDL lighting state and does not register a competing EDL Mode action.

Detailed Covasify installation, Spotify setup, commands, troubleshooting, version history, lineage, and licensing documentation are published in [`Covasify/`](Covasify/).

### Chromas Next — Elite Dangerous Lighting integration

**Chromas Next 1.0.0** is the dedicated COVAS:NEXT plugin for **Elite Dangerous Lighting**. It must be installed and enabled in the COVAS:NEXT Plugins menu before COVAS can control the standalone EDL application.

Once enabled, Chromas Next lets COVAS issue lighting commands to EDL by voice or operator request: changing colours and effects, using Stand Down to relinquish temporary lighting authority, and starting saved **Modes** by name. Modes are user-created multi-phase lighting sequences in EDL that can combine different devices, colours, effects, and timings into a reusable sequence.

Chromas Next always owns the COVAS-facing EDL command path, including the single public `edl_run_mode` action. It works without Covasify. The optional Covasify bridge adds only Mode-associated music:

```text
COVAS:NEXT -> Chromas Next -> EDL

optional Mode music:
Chromas Next -> Covasify -> Spotify
```

EDL remains the lighting engine and continues to own Elite state, rules, effects, scripted scenes, Modes, timing, arbitration, rendering, hardware control, and restoration. Chromas Next provides the COVAS-facing command layer; Covasify contributes only optional Spotify playback.

The Chromas Next 1.0.0 plugin source package is published in [`ChromasNext/`](ChromasNext/).

## Related Project

### Elite Dangerous Lighting

[Elite Dangerous Lighting](https://github.com/DocTrintignant/elite-dangerous-lighting) is a separate standalone application and repository.

EDL translates live Elite Dangerous state, hardware input, user rules, scripted sequences, and operator commands into deterministic RGB lighting across supported devices. It can operate without COVAS:NEXT.

When COVAS:NEXT integration is used, **Chromas Next is the EDL command plugin**. Covasify is optional and only participates in Mode-associated music when its bridge is enabled in Chromas Next.

## Archived / Obsolete Plugins

The development history also contains the following archived, obsolete plugins. They are no longer maintained, are not part of the current supported public release, and may no longer be compatible with current COVAS:NEXT releases.

- [`Songbird_ARCHIVED_OBSOLETE/`](Songbird_ARCHIVED_OBSOLETE/) — former voice-controlled sound-effects plugin using Freesound and a local soundboard.
- [`Covinance_ARCHIVED_OBSOLETE/`](Covinance_ARCHIVED_OBSOLETE/) — former Elite Dangerous commodity trading and market-analysis plugin using the Ardent API.

Do not treat the archived folders as current supported plugins.

## Installation

Install each published plugin according to the instructions in its own folder.

COVAS:NEXT plugins are installed under:

```text
%appdata%\com.covas-next.ui\plugins\
```

For Covasify, copy the `Covasify` folder there, restart COVAS:NEXT, and complete the Spotify setup described in [`Covasify/README.md`](Covasify/README.md).

For EDL voice control, copy the `ChromasNext` folder there and restart COVAS:NEXT. The optional **Covasify bridge for Mode audio** is configured from **COVAS:NEXT -> Plugins -> Chromas Next**, not from EDL or Covasify.

## License

New original contributions in this repository are made available under the [PolyForm Noncommercial License 1.0.0](LICENSE).

Non-commercial use, modification and redistribution are permitted under that licence. Commercial use of those contributions requires a separate licence from the copyright holder.

Forks and derivative projects are welcome for non-commercial use. If you plan to publish or maintain a derivative project, please contact the maintainer first. This is a courtesy request, not an additional condition of the licence.

**Covasify includes portions derived from the Lag0matic development line that were published under the MIT License. Those existing MIT-licensed portions remain under their original MIT terms and are not relicensed or restricted by the repository-level PolyForm licence.** Bundled third-party dependencies and notices likewise retain their own applicable licences.
