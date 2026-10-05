# RoomTidy: small quick-start guide

## Set up once

1. Open `Start-RoomTidy.cmd`. The app starts paused.
2. Tidy one visible area as you want it to stay. Keep the camera fixed.
3. Choose **Camera setup**, then **Open preview**. Camera0 is the existing C920.
4. Drag a rectangle around the desk or floor area. Add preferences, for example: `Books are allowed; dishes should be removed.`
5. Press **Save tidy reference**, then give the area a name. This saves the selected crop as your comparison picture. Repeat for other areas if needed.
6. Go to **Overview** and press **Resume monitoring**. Keep the app open and the computer awake.

## Everyday use

- **Check now:** take a snapshot after a two-second notice and assess locally. Live clutter counts still advance at most hourly.
- **Clutter observed:** one valid clutter check is added. At30 valid checks, the app attempts one desktop reminder. Thirty observations do not prove30 continuous hours of clutter.
- **Matches reference:** the counter clears.
- **Unable to assess:** no evidence is counted; progress is preserved.
- **Cleaned:** reset progress while keeping the reference.
- **Snooze1 hour:** hide the active reminder for an hour. The same unresolved episode does not produce repeated toasts.
- **Pause monitoring:** stop automatic checks. Closing RoomTidy stops all monitoring.

**Update tidy reference** changes what the app compares against. Use a fresh preview and explicitly confirm it. Saving an existing area's preferences or reference resets both Live and Demo tracking for that area.

## Quick demo

In **Settings**, choose **Demo: every minute** and set the threshold to3. For real-camera testing, return to Overview and resume; the counter needs three valid clutter scans.

For a synthetic demonstration, load `demo/tidy.png` with **Load demo reference picture**, drag nearly the whole image and save it. Preferences: `Red square is allowed; blue circular objects should be removed.` In Settings, import `demo/clutter.png` three times. `dark.png` and `blocked.png` preserve progress; `tidy.png` resets it. This demonstrates the workflow, not real-room accuracy.

Demo and Live counters are separate. Switching profiles pauses monitoring. The threshold is shared: set it back to30 when returning to Live. Staged references cannot be used for Live analysis; select or save a real-camera area for Live.

## If something goes wrong

Use a well-lit, unobstructed view. If you move the camera, update its reference explicitly. If local analysis times out, pause and try again when GPU load is lower. Windows may suppress notifications; the app keeps the reminder visible. **How to use** inside the app has the same guidance; **Settings** has Reduce motion and Delete local app data.

## Guided photo walkthrough

1. Double-click `Start-Photo-Demo.cmd` for the **SYNTHETIC PHOTO WALKTHROUGH**.
2. Click **Use staged reference / Start**. This explicitly saves the generated desk reference and resets only the dedicated photo-demo profile.
3. Click **Next step** seven times, waiting for each local analysis to finish: tidy reference, clutter, blocked view, clutter, clutter at the reminder threshold, extra clutter without a repeated reminder, and tidy reset.

The reference and current-picture thumbnails show the staged inputs. Each step displays its target and the actual model result; a mismatch is kept and reported. **Reset demo** resets this demo's tracking; Start begins a fresh walkthrough.

These are manual staged observations with a threshold of **3**, not thirty elapsed minutes or hourly observations. Data is separate at `%LOCALAPPDATA%\RoomTidyPhotoDemo\RoomTidy`; normal RoomTidy references/history are not opened. The camera is unused. Generated scene provenance is in `demo/photos/README.md`. The reminder uses the genuine Windows notification path, but Windows can suppress visual delivery.
