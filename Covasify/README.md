# Covasify v4.2.0

**Covasify lets you control Spotify by talking to COVAS:NEXT.**

You can ask for songs, albums, artists or playlists, control playback, manage Liked Songs, create your own voice bindings, and show the current track on the COVAS:NEXT HUD.

Covasify works on its own. **Elite Dangerous Lighting and Chromas Next are optional** and are only needed if you want Spotify music attached to EDL Modes.

**Spotify Premium is required** for playback control.

## What it does

Covasify can:

- play tracks, albums, artists and playlists
- play your Liked Songs
- pause, resume, stop, skip and restart playback
- seek within a track
- control volume, shuffle and repeat
- save or remove the current track from Liked Songs
- bind a track to a custom phrase
- tell COVAS:NEXT what is currently playing
- show a live now-playing card on the COVAS:NEXT HUD
- optionally play music attached to an Elite Dangerous Lighting Mode

## How it fits together

There are four separate pieces:

- **COVAS:NEXT** is the voice/AI environment.
- **Covasify** gives COVAS:NEXT access to Spotify.
- **Chromas Next** gives COVAS:NEXT access to Elite Dangerous Lighting.
- **Elite Dangerous Lighting (EDL)** is the separate application that actually controls the RGB lighting.

For normal Spotify use:

```text
COVAS:NEXT -> Covasify -> Spotify
```

For lighting:

```text
COVAS:NEXT -> Chromas Next -> EDL -> your lights
```

For an EDL Mode that also has music:

```text
COVAS:NEXT -> Chromas Next -> EDL
                 |
                 -> Covasify -> Spotify
```

Covasify never takes control of the lighting. It only handles Spotify.

## What you need

For normal Covasify use:

- COVAS:NEXT
- Spotify Premium
- a Spotify Developer application
- your Spotify Client ID and Client Secret
- an available Spotify playback device

Optional, only for EDL Mode music:

- Elite Dangerous Lighting
- Chromas Next 0.6.12 or newer

## Installation

1. Download the current `Covasify` folder.
2. Make sure the folder is named exactly:

   ```text
   Covasify
   ```

3. Copy it to:

   ```text
   %APPDATA%\com.covas-next.ui\plugins\
   ```

4. Restart COVAS:NEXT.

The required Python dependencies are already bundled in `deps`. You do not need to install them separately.

Replacing the Covasify plugin folder does not normally remove your saved COVAS:NEXT settings, Spotify login token or track bindings because those are stored separately by COVAS:NEXT.

## Setup

### 1. Create a Spotify application

Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create an application.

Add this exact Redirect URI:

```text
http://127.0.0.1:8888/callback
```

If Spotify Development Mode requires it, add the Spotify account you intend to use under **User Management**.

Copy the application's:

- **Client ID**
- **Client Secret**

### 2. Enter the Spotify details in COVAS:NEXT

Open:

**COVAS:NEXT -> Plugins -> Covasify Spotify Integration**

Enter:

| Setting | What to enter |
|---|---|
| Client ID | Your Spotify application Client ID |
| Client Secret | Your Spotify application Client Secret |
| Redirect URI | `http://127.0.0.1:8888/callback` |

Start a COVAS chat session. On the first authorization, your browser will open so you can approve Spotify access.

Keep Spotify open on at least one device. Covasify needs an available Spotify playback device before it can start music.

## What you can do

You can speak naturally. Examples:

```text
"Play Bohemian Rhapsody"
"Play Abbey Road album"
"Play Queen"
"Play Queen's top tracks"
"Play workout playlist"
"Play Liked Songs"

"Pause"
"Resume"
"Next"
"Previous"
"Restart"
"Seek to 2:30"
"Set volume to 50"
"Shuffle on"
"Repeat track"

"What's playing?"
"Save this track"
"Remove this track"

"Bind this to workout intro"
"Workout intro"
"List bindings"
"Unbind workout intro"
"Unbind all"
```

You can also ask COVAS to show the current track on the HUD, for example:

```text
"Show what's playing on the HUD"
"Add a now-playing widget to the display"
```

## Available COVAS actions

These are the actions Covasify registers with COVAS:NEXT. You do not need to say the action names yourself; they are included here so you can see exactly what the plugin exposes.

| Action | What it does |
|---|---|
| `covasify_play` | Plays a track, artist, artist top tracks, album or playlist |
| `covasify_control` | Pause/resume, next/previous, restart, seek, volume, shuffle and repeat |
| `covasify_library` | Saves or removes the current track from Liked Songs |
| `covasify_bindings` | Creates, plays, lists or removes custom phrase bindings |
| `covasify_status` | Returns the current Spotify track and playback status |

## Using it with the other plugin

Covasify can optionally provide music for EDL Modes started through **Chromas Next**.

To start a saved EDL Mode through COVAS:NEXT, ask for the Mode using the name you gave it in EDL. For example, if the Mode is named `RED ALERT`, say **“Start RED ALERT.”**

Covasify does not choose or start the Mode. Chromas Next sends the saved Mode name to EDL; Covasify only receives the optional music cue after EDL has accepted the Mode.

Open:

**COVAS:NEXT -> Plugins -> Chromas Next**

and enable:

**Enable Covasify bridge for Mode audio**

With the bridge **OFF**, EDL Modes run normally with lighting only.

With the bridge **ON**, Chromas Next starts the Mode in EDL first. If that Mode includes a music cue, Chromas Next then passes the cue to Covasify, which uses the normal Spotify playback system.

Three rules are intentionally kept simple:

1. **Chromas Next controls EDL.** Covasify does not control lighting or start EDL Modes itself.
2. **Covasify handles only the optional music.** If Covasify or Spotify fails after the Mode has started, the lighting keeps running normally.
3. **EDL is optional for Covasify.** Normal Spotify control continues to work even when EDL is not running.

A Mode cue such as `Danger Zone by Kenny Loggins` uses the same artist-aware track search as a normal Covasify request.

## Troubleshooting

**No active Spotify devices found**  
Open Spotify on the desktop app, mobile app or web player and start playback once, then try again.

**Covasify is not connected to Spotify**  
Check the Client ID, Client Secret and Redirect URI in the Covasify settings. If necessary, re-authorize Spotify.

**EDL Mode lighting works but the music does not start**  
Make sure Covasify is installed and connected to Spotify, then check that **Enable Covasify bridge for Mode audio** is enabled in the Chromas Next settings.

**A voice binding does not play on the first attempt**  
Try the phrase once more. First-attempt retries can occasionally be required.

**Some Spotify features are unavailable**  
Current Spotify Development Mode applications do not expose some older API features such as radio/recommendations, related-artists suggestions and an endless smart queue.

## Package contents

```text
Covasify/
  Covasify.py
  manifest.json
  deps/
  README.md
```

- `Covasify.py` — the plugin itself
- `manifest.json` — tells COVAS:NEXT what the plugin is and which file to load
- `deps/` — bundled Python libraries required by Covasify
- `README.md` — this guide

## Version history

**4.2.0** — Canonical EDL-compatible release. Adds optional Chromas Next -> Covasify Mode music and automatic EDL connection reporting while leaving Chromas Next as the sole owner of EDL Mode invocation.

**4.1.2** — Maintenance resumed under DocTrintignant: corrected playback startup, moved OAuth/bindings to persistent plugin data, and removed raw settings logging.

**4.1.1** — Lag0matic development line: GenUI now-playing projection.

**4.1.0** — Improved artist-aware track matching and search scoring.

**4.0.0** — Consolidated tool model, ambient now-playing state and reduced per-turn token cost.

**3.0.0** — Restored/reworked by Lag0matic and AI.

**2.0.0** — COVAS:NEXT settings integration.

**1.0.0** — Initial release.

## Credits and licensing

Covasify was originally created by **DocTrintignant**. Versions **3.0.0 through 4.1.1** were restored and substantially developed by **Lag0matic**. Maintenance and new development resumed under **DocTrintignant** from **4.1.2** onward.

Lag0matic development line:  
https://github.com/lag0matic/TRINTIGNANT-COVAS-NEXT-PLUGINS/tree/main/Covasify

The Lag0matic development line is published under the [MIT License](https://github.com/lag0matic/TRINTIGNANT-COVAS-NEXT-PLUGINS/blob/main/LICENSE). New original contributions in this repository are subject to the repository-level **PolyForm Noncommercial License 1.0.0** to the extent applicable; existing MIT-licensed upstream portions remain under their original MIT terms and are not relicensed or restricted by the repository-level licence.

Canonical maintained repository:  
https://github.com/DocTrintignant/covas-next-plugins
