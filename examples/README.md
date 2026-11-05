# Reproducible organic examples

`organic-portrait.json` is the validated scene specification produced by the local Qwen3
4B planning run recorded in VALIDATION.md. Its geometry and animation are built by the
procedural organic tools. Rebuilding this file does not call the AI or train anything.

From the project root:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe' -m scene_forge build --plan examples/organic-portrait.json --preview stills
```

Use `--preview video` for a shaded 12 FPS Eevee MP4 alongside three Cycles stills. Rendering
can take many minutes on this laptop. Each build creates a separate editable project.
This example has not been approved for a training corpus or as a production-quality asset.

`organic-greeting.json` is the three-second full-body wave recipe from the 0.3 run.
The local model initially added three unwanted primitive trees. An explicit AI revision
removed them and corrected the limitations, preserving all character and camera settings.
The actual requests, model output and revision diff are retained in the output jobs listed
in `VALIDATION.md`. This file is that revised plan, not a separately authored demo.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe' -m scene_forge build --plan examples/organic-greeting.json --preview video
```

The 0.3 builder supplies denser procedural anatomy, articulated arms and animated foliage.
It does not train weights. The greeting is stationary; arbitrary motion and organic
walking remain unsupported. No training-corpus approval is implied by this example.
