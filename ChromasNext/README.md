# Chromas Next v1.0.0

**Chromas Next lets you control Elite Dangerous Lighting by talking to COVAS:NEXT.**

You can ask COVAS to change colours and effects, check which lighting devices are currently available, start your saved EDL Modes by name, and tell the lighting to Stand Down.

Chromas Next does not control RGB hardware itself. It sends your requests to the separate **Elite Dangerous Lighting (EDL)** application, and EDL remains responsible for the actual lights.

## What it does

Chromas Next can:

- check whether EDL is connected and ready
- read the lighting devices, zones and effects currently available in EDL
- set a device or zone to a static colour
- use the effects currently exposed by EDL
- start a saved EDL Mode using the name you gave it in EDL
- Stand Down and return lighting control to the current underlying EDL state
- optionally pass a Mode's music cue to Covasify

## How it fits together

There are four separate pieces:

- **COVAS:NEXT** is the voice/AI environment.
- **Covasify** gives COVAS:NEXT access to Spotify.
- **Chromas Next** gives COVAS:NEXT access to Elite Dangerous Lighting.
- **Elite Dangerous Lighting (EDL)** is the separate application that actually controls the RGB lighting.

For lighting:

```text
COVAS:NEXT -> Chromas Next -> EDL -> your lights
```

For normal Spotify use:

```text
COVAS:NEXT -> Covasify -> Spotify
```

For an EDL Mode that also has music:

```text
COVAS:NEXT -> Chromas Next -> EDL
                 |
                 -> Covasify -> Spotify
```

Chromas Next is the messenger between COVAS:NEXT and EDL. EDL still owns your lighting rules, Modes, effects, connected devices and hardware control.

## What you need

For Chromas Next:

- COVAS:NEXT
- Elite Dangerous Lighting
- the `ChromasNext` plugin folder installed in COVAS:NEXT

Optional, only for EDL Mode music:

- Covasify 4.2.0 or newer
- Spotify Premium

EDL remains fully usable without COVAS:NEXT. Chromas Next is only needed when you want COVAS:NEXT to control EDL.

## Installation

1. Download the current `ChromasNext` folder.
2. Make sure the folder is named exactly:

   ```text
   ChromasNext
   ```

3. Copy it to:

   ```text
   %APPDATA%\com.covas-next.ui\plugins\
   ```

4. Restart COVAS:NEXT.
5. Start Elite Dangerous Lighting.
6. If you also use Covasify for Mode music, open **COVAS:NEXT -> Plugins -> Chromas Next** and turn on **Enable Covasify bridge for Mode audio**.
7. Start or restart the COVAS chat assistant.

If you are upgrading from an old build that used the folder name `chromas_next_plugin`, remove that old folder first. Do not leave both versions installed.

The Covasify bridge is optional. You only need to enable it if you want an EDL Mode to start Spotify music through Covasify. For lighting-only use, leave it off.

## Setup

For the complete set of lighting effects, **start EDL before starting the COVAS chat session**.

Chromas Next reads EDL's current effect list when the chat starts. If EDL was not running at that point, the basic Chromas Next actions still load, but the effect-specific actions cannot be created until you restart the chat.

If you start EDL later:

1. make sure EDL is running
2. restart the COVAS chat assistant

Chromas Next will then rebuild its effect actions from the current EDL catalog.

For optional Mode music, this is the point where you enable the bridge:

1. install both **Chromas Next** and **Covasify**
2. restart COVAS:NEXT
3. open **COVAS:NEXT -> Plugins -> Chromas Next**
4. turn on **Enable Covasify bridge for Mode audio**
5. start or restart the COVAS chat assistant

You do **not** enable this bridge in EDL or in the Covasify settings. It belongs to the **Chromas Next** plugin settings.

Leave the switch off if you only want lighting.

## What you can do

You can speak naturally. Examples:

```text
"Is Elite Dangerous Lighting connected?"
"What lighting devices are available?"
"Make the keyboard red."
"Set the mouse to blue."
"Put the Govee strip on a rainbow effect."
"Start RED ALERT."
"Stand Down."
```

The exact devices, zones and effects you can ask for come from your current EDL setup. Chromas Next does not keep a separate hard-coded copy of them.

To start a saved EDL Mode through COVAS:NEXT, ask for the Mode using the name you gave it in EDL. For example, if the Mode is named `RED ALERT`, say **“Start RED ALERT.”**

The Mode name is the saved name shown in EDL; it is not a description that Chromas Next invents. Saved Modes remain owned by EDL, and Chromas Next simply sends that saved Mode name to EDL.

## Available COVAS actions

These are the actions Chromas Next registers with COVAS:NEXT. You do not need to say the action names yourself; they are included here so you can see exactly what the plugin exposes.

| Action | What it does |
|---|---|
| `edl_status` | Checks the current EDL connection and live lighting status |
| `edl_catalog` | Reads the current devices, zones, effects and capabilities exposed by EDL |
| `edl_set_color` | Applies a static colour to an EDL target |
| `edl_<effect>` | One action per non-static effect exposed by EDL when the COVAS chat starts |
| `edl_run_mode` | Starts a saved EDL Mode using the name saved in EDL |
| `edl_stand_down` | Releases temporary COVAS/Mode lighting control and returns to the current underlying EDL state |

There is no fixed hard-coded list of effect actions. Chromas Next builds them from the EDL catalog so that COVAS sees the effects that EDL can actually use at that moment.

## Using it with the other plugin

Chromas Next works without Covasify.

Covasify is only needed if you want a saved EDL Mode to start Spotify music as well as lighting.

After both plugins are installed, enable the bridge from **COVAS:NEXT -> Plugins -> Chromas Next -> Enable Covasify bridge for Mode audio**. This is the setting that connects Mode music to Covasify.

With **Enable Covasify bridge for Mode audio** turned **OFF**:

```text
COVAS:NEXT -> Chromas Next -> EDL
```

The Mode runs as lighting only.

With the bridge turned **ON**, Chromas Next first asks EDL to start the Mode. If EDL accepts it and the Mode contains a music cue, Chromas Next then passes that cue to Covasify:

```text
COVAS:NEXT -> Chromas Next -> EDL
                 |
                 -> Covasify -> Spotify
```

Three rules are intentionally kept simple:

1. **Chromas Next controls the COVAS-to-EDL path.** Covasify does not send lighting commands to EDL.
2. **Covasify handles only the optional music.** Spotify failure must not cancel or roll back lighting that EDL has already started.
3. **EDL remains the lighting authority.** Chromas Next sends requests; EDL decides how those requests are rendered on the actual hardware.

## Troubleshooting

**COVAS says EDL is not connected**  
Start Elite Dangerous Lighting, then open **Setup → COVAS:NEXT connection** in EDL and check the reported Chromas Next status.

**Basic controls work but some effect actions are missing**  
EDL was probably not available when the COVAS chat started. Start EDL, then restart the COVAS chat assistant so Chromas Next can read the current effect catalog again.

**A saved Mode will not start**  
Make sure live lighting is running in EDL, that the Mode exists in the currently applied EDL profile, and that you asked for it using the name shown in EDL.

**The Mode lighting starts but Spotify music does not**  
Make sure Covasify 4.2.0 or newer is installed and connected to Spotify, then check that **Enable Covasify bridge for Mode audio** is enabled in the Chromas Next settings.

**You want to stop a temporary lighting request or active Mode**  
Tell COVAS to **Stand Down**. EDL will return to the current underlying lighting state.

## Package contents

The current repository folder contains:

```text
ChromasNext/
  ChromasNext.py
  manifest.json
  README.md
  __init__.py
  tests/
```

- `ChromasNext.py` — the plugin itself and the file COVAS:NEXT loads
- `manifest.json` — tells COVAS:NEXT what the plugin is and which file to load
- `README.md` — this guide
- `__init__.py` — Python package marker
- `tests/` — maintenance tests; normal users do not need to run them

The current plugin entrypoint is `ChromasNext.py`.

## Version history

**1.0.0** — First stable v1 release. Promotes the physically accepted single-file Chromas Next runtime without changing its control model: live EDL status/catalog, static colour control, EDL-provided effect actions, saved Modes, Stand Down, and the optional Covasify Mode-audio bridge.

**0.6.12** — Final pre-1.0 accepted build of the current single-file runtime and integration model.

Earlier development history is available in the repository history.

## Credits and licensing

Chromas Next is created and maintained by **DocTrintignant** as the COVAS:NEXT integration for the separate [Elite Dangerous Lighting](https://github.com/DocTrintignant/elite-dangerous-lighting) project.

Chromas Next original contributions are covered by the repository-level [PolyForm Noncommercial License 1.0.0](../LICENSE). Commercial use requires separate permission from the copyright holder.

Canonical maintained repository:  
https://github.com/DocTrintignant/covas-next-plugins
