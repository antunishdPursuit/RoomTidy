# RoomTidy

A local Windows desktop app built for my roommate. Select camera areas, save an explicit tidy reference, and receive a gentle reminder when visible clutter persists. Image analysis runs locally with **Gemma 4 E4B Instruct**, OpenCV and llama.cpp. No accounts, paid AI APIs or cloud image uploads.

[Watch the 60-second demo](https://youtu.be/_4c8RANLBD4). The video uses generated desk photos and manually staged checks, not a timed real-room trial.

## Install on Windows

Tested with Python 3.11, Windows, and an NVIDIA RTX 3080. Other hardware has not been verified. You need Git, [Python 3.11](https://www.python.org/downloads/), a webcam for live monitoring, and the local runtime/model downloads below (about 5.6 GB of model files).

The MVP currently expects this folder layout:

```text
Coding/
  Projects/RoomTidy/          # this repository
  Utilities/RoomTidySetup/
    .venv/
    runtime/                 # llama-server.exe and bundled DLLs
    models/
      gemma-4-E4B-it-Q4_0.gguf
      mmproj-gemma-4-E4B-it-BF16.gguf
```

From a folder where you want to create `Coding`, run in PowerShell:

```powershell
New-Item -ItemType Directory -Force Coding/Projects, Coding/Utilities/RoomTidySetup
git clone https://github.com/antunishdPursuit/RoomTidy.git Coding/Projects/RoomTidy
cd Coding/Projects/RoomTidy
py -3.11 -m venv ../../Utilities/RoomTidySetup/.venv
& ../../Utilities/RoomTidySetup/.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
```

1. Download the Windows CUDA 12 build and CUDA 12.4 DLL archive from [llama.cpp release b11146](https://github.com/ggml-org/llama.cpp/releases/tag/b11146): `llama-b11146-bin-win-cuda-12.4-x64.zip` and `cudart-llama-bin-win-cuda-12.4-x64.zip`. Extract their contents into `Coding/Utilities/RoomTidySetup/runtime`; `llama-server.exe` must be directly in that folder. Keep the accompanying DLLs together. A CPU build is available upstream, but has not been tested here.
2. Download the two model files named above from the [pinned official GGUF conversion](https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF/tree/b8093469224f83f5c38f691eb906c380e9e63114), and place them in `Coding/Utilities/RoomTidySetup/models`.
3. Double-click `Start-RoomTidy.cmd`, or run:

```powershell
& ../../Utilities/RoomTidySetup/.venv/Scripts/python.exe app.py
```

The app starts and stops its own authenticated loopback inference process. You do not need to start a separate model server. Missing runtime/model files appear as an analysis error.

## Use it

1. Tidy an area and keep the camera fixed. In **Camera setup**, open preview, drag a rectangle, add preferences (for example, books allowed; dishes removed), then save and name the tidy reference.
2. **Resume monitoring** and keep the app open and computer awake. Hourly checks show a brief capture notice and release the camera afterward.
3. After 30 valid clutter observations, one desktop reminder is attempted. Darkness, blocked views and missed checks do not add evidence. A tidy result clears progress.
4. Use **Pause**, **Snooze**, or **Cleaned** as needed. Updating the reference requires explicit action; persistent clutter never becomes a new baseline automatically.

See [QUICK_START.md](QUICK_START.md) for controls and troubleshooting. Closing the app stops monitoring.

## Try the generated-photo demo

Open `Start-Photo-Demo.cmd`, click **Use staged reference / Start**, then advance through seven steps, waiting for each result. It uses the real local analysis and persistence pipeline, with a threshold of three and synthetic photos. Changed pictures use Gemma; unreadable views and exact readable reference matches use deterministic checks. Targets do not override actual results.

The demo has a separate local profile and does not use the webcam. [Image provenance](demo/photos/README.md).

## Privacy and limits

Settings, references and observation metadata stay under `%LOCALAPPDATA%/RoomTidy`. Routine captured images stay in memory; history is capped at 500 metadata rows. **Delete local app data** removes app-owned data (ordinary deletion, not secure erasure). The photo demo uses a separate `%LOCALAPPDATA%/RoomTidyPhotoDemo` profile. Notifications may show area names on the lock screen.

The app describes visible items; it does not detect dust or prove somebody has not cleaned. Thirty checks do not establish thirty continuous hours of clutter. Windows may suppress desktop toasts, so reminders also remain visible in the app. Keep camera position and lighting consistent; arbitrary camera movement and real-room classification accuracy are not established.

## Tests

```powershell
& ../../Utilities/RoomTidySetup/.venv/Scripts/python.exe -m pytest tests --basetemp .pytest-new-run -q
```

71 regression tests passed on the development computer. The controlled seven-step local-model demo produced counts `0, 1, 1, 2, 3, 4, 0`. Camera capture/release was checked separately. A full timed room trial, changed real-camera classification accuracy, recipient feedback and independently observed Windows toast delivery remain unverified.

`verify_local.py` captures and releases the camera without saving its image, then checks synthetic inputs. `verify_photo_flow.py` checks the generated-photo sequence with local inference.

## Licenses and project history

App source: [MIT](LICENSE). [Gemma model weights and official conversion](https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF): Apache-2.0. llama.cpp: MIT; OpenCV: Apache-2.0; PySide6: LGPL-3.0/GPL alternatives; bundled Nunito Sans: [SIL OFL](assets/fonts/OFL.txt). Check dependency obligations before distributing a packaged installer. Model weights and runtime binaries are downloaded separately.

Built with AI coding assistance and Opus/Astra source reviews. Generated demo photos came from OpenAI image generation; runtime analysis uses local Gemma. This repository begins with an initial import of the already-developed MVP; earlier development did not have a Git commit history. It is a Windows hackathon MVP, with **Best Use of Gemma** as its intended partner category.
