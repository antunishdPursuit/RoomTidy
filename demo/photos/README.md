# Synthetic photo demo provenance

These are generated images of a fictional desk, created for the RoomTidy walkthrough with the built-in OpenAI `image_gen` tool on 2026-10-04:

- `reference.png`: approved tidy-scene example.
- `clutter.png`: an edit of the same view with visible clutter added.
- `blocked.png`: an edit of the same view made dark/obscured for an unable-to-assess example.

The images are synthetic demonstration assets, not photographs of Dennis's room or roommate. They were generated with OpenAI image generation, **not by local Gemma**. Changed-image comparison and image understanding use the application's local Gemma 4 E4B Instruct model (Q4_0 with its matching BF16 vision projector). Deterministic quality checks run first; exactly matching readable decoded pixels return tidy without invoking the model. These demonstration inputs are not uploaded by the app.

The seven-step walkthrough reuses these three images. Repeated manually staged inputs are not elapsed hourly/minute observations, and results from these examples do not establish real-room classification accuracy. Step targets are presented separately from the actual model output; mismatches remain visible.

Gemma compares changed selected-area inputs with the explicit tidy reference; application logic, not the model, tracks valid observations and reminders. Its model weights and upstream revisions are recorded in the shared installation’s `gemma-e4b-manifest.json`. There is no cloud image-analysis fallback. The original Qwen setup remains preserved as prior evaluation evidence, not the active runtime.
