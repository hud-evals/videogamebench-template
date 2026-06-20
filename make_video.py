"""Assemble recorded gameplay frames into a video clip.

Frames are written by env.py when VGBENCH_RECORD=1 (to logs/rec/<game>/frame_*.png).

Usage:
    # record while running an eval:
    VGBENCH_RECORD=1 hud eval tasks.py claude --model claude-sonnet-4-6 \
        --task-ids play-zelda --max-steps 80 -y
    # then assemble:
    python make_video.py --dir logs/rec/zelda --out logs/zelda.mp4
    python make_video.py --dir logs/rec/zelda --out logs/zelda.gif --fps 8
"""

from __future__ import annotations

import argparse
import glob
import os

from PIL import Image


def load_frames(frame_dir: str, scale: int, stride: int = 1) -> list[Image.Image]:
    paths = sorted(glob.glob(os.path.join(frame_dir, "frame_*.png")))[:: max(1, stride)]
    frames = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        if scale != 1:
            im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        frames.append(im)
    return frames


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, help="frames dir (logs/rec/<game>)")
    ap.add_argument("--out", required=True, help="output .mp4 or .gif")
    ap.add_argument("--fps", type=int, default=6)
    ap.add_argument("--scale", type=int, default=3, help="integer upscale (nearest)")
    ap.add_argument("--stride", type=int, default=1, help="keep every Nth frame")
    args = ap.parse_args()

    frames = load_frames(args.dir, args.scale, args.stride)
    if not frames:
        raise SystemExit(f"No frames in {args.dir} (did you run with VGBENCH_RECORD=1?)")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    if args.out.lower().endswith(".gif"):
        frames[0].save(
            args.out,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000 / args.fps),
            loop=0,
            optimize=True,
        )
    else:
        import imageio.v2 as imageio
        import numpy as np

        writer = imageio.get_writer(
            args.out, fps=args.fps, codec="libx264", quality=8, macro_block_size=None
        )
        for im in frames:
            writer.append_data(np.asarray(im))
        writer.close()

    print(f"wrote {args.out}  ({len(frames)} frames @ {args.fps}fps, x{args.scale})")


if __name__ == "__main__":
    main()
