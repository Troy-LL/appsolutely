# Urgent chime

Owner: Donita. This is MVP item M6 in [features.md](features.md). `/lola` never turns red ([architecture.md](architecture.md#viewports)).

**Off by default since Sat ~8:05 AM (Donita).** The urgent alarm now rings on the caregiver iPhone: `/caregiver` is armed with one "Turn on alerts" tap, and on `alert` a full-screen red alert rings and repeats until the caregiver taps "Papunta na ako / On my way" (or an `urgent_reply` arrives), for at most 2 minutes. The page must stay open and awake ([architecture.md](architecture.md#offline-guarantees)). `CHIME=1` turns this laptop chime back on as a backup: `hub/start.sh` passes it to the hub server, so restart the server with it (`hub/start.sh stop`, then `CHIME=1 hub/start.sh`). The health light prints `Laptop chime: ON` or `OFF`. The hub still goes deaf for `CHIME_DEAF_SECONDS` (9 s) after every urgent decision, chime or not, because the iPad mic may hear the phone's alarm. The iPhone alarm is not tested yet: to verify on the iPhone.

Everything below describes the laptop chime when it is on.

## When it plays

With `CHIME=1`, the hub plays it when the decision `action` is `urgent`. That is the same moment `/caregiver` receives the `alert` event. No other action plays it. There is no push notification with the internet off ([architecture.md](architecture.md#offline-guarantees)).

## How

From `hub/`, use macOS built-in `afplay`. No downloaded sound and no extra audio file in the repo.

```
afplay -v 1 /System/Library/Sounds/Glass.aiff
```

One alarm plays Glass 5 times back to back, with no gap: each play starts right after the previous one ends. Glass is 1.65 s long (measured with `afinfo`), so one alarm lasts about 8.25 s. `play_chime()` in `hub/chime.py` starts it in the background and returns at once. If a second urgent line comes while an alarm is still playing, no second alarm starts, so the sounds never pile up.

Changed Sat ~4:10 AM at Donita's request after testing: a single Glass was too easy to miss. The gap between plays was removed at Donita's request (~4:20 AM) so the dings are closer.

`-v 1` is `afplay`'s full scale. Louder than that is the Mac's output volume. Turn the hub volume up before the demo ([demo.md](demo.md)).

`/lola` does not play this file and does not turn red.

## When it stops

A caregiver `urgent_reply` (docs/sino/architecture.md) calls `stop_chime()`, which ends the `afplay` process if it is still running. The next urgent line can start a new alarm. `/lola` still never plays this sound.

Whether the chime is audible across a room is to verify at smoke test ([architecture.md](architecture.md#to-verify-at-smoke-test)).

## Pre-freeze test (was the 1:00 AM test)

Planned for 1:00 AM, before Donita slept. The hub was not up by then, so run it as soon as the hub is up and before the 3:30 AM MVP freeze ([mvp-plan.md](mvp-plan.md)). Not run yet as of Sat 2:00 AM.

1. The hub is up from `start.sh` with `CHIME=1` (needed since Sat ~8:05 AM). The health light is up. The hub volume is up.
2. On `/backstage`, type `Masakit dibdib ko` into the typed-question box (or speak that line).
3. Pass: the hub speaker plays `Glass.aiff` through `afplay`, and `/caregiver` shows a red card with those words.
4. Pass: `/lola` stays calm and does not turn red.
5. Fail: no sound, sound from the iPad, or any red on `/lola`. Fix it before the freeze.
