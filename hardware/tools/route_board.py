#!/usr/bin/env python3
"""Autoroute a KiCad PCB with Freerouting and import the tracks back.

The script exports the board as a Specctra DSN file, runs the Freerouting
autorouter on it, imports the routed session (SES) file back into the
board, and saves the result. It works on any .kicad_pcb file. Tracks come
out at 45/90 degrees.

It needs:
  - KiCad's Python (for the pcbnew module), e.g. with the KiCad 10 AppImage:
      ~/bin/kicad-10.0.5-x86_64.AppImage python3.11 route_board.py ...
  - Java 17 or newer.
  - The Freerouting 1.9.0 jar. Get it once with --download. Newer
    Freerouting releases (2.x) ignore the pass limit on the command line and
    2.2+ need Java 25, so 1.9.0 is the default.

Freerouting 1.9.0 opens a progress window, so it needs a display. Without
one (SSH, CI), the script runs it through xvfb-run if that is installed.

Examples:

    K="$HOME/bin/kicad-10.0.5-x86_64.AppImage python3.11"
    $K route_board.py --download
    $K route_board.py board.kicad_pcb -o /tmp/routed.kicad_pcb --render /tmp/routed.png
    $K route_board.py board.kicad_pcb --clear --in-place

Close the board in KiCad before you write it in place, or KiCad overwrites
the result on its next save.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

try:
    import pcbnew
except ImportError:
    sys.exit(
        "error: cannot import pcbnew. Run this script with KiCad's Python, e.g.\n"
        "  ~/bin/kicad-10.0.5-x86_64.AppImage python3.11 " + sys.argv[0] + " --help"
    )

FREEROUTING_VERSION = "1.9.0"
FREEROUTING_URL = (
    f"https://github.com/freerouting/freerouting/releases/download/v{FREEROUTING_VERSION}/"
    f"freerouting-{FREEROUTING_VERSION}.jar"
)
DEFAULT_JAR = os.path.expanduser(f"~/.local/share/freerouting/freerouting-{FREEROUTING_VERSION}.jar")


def download_jar(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"downloading {FREEROUTING_URL}")
    tmp = path + ".part"
    urllib.request.urlretrieve(FREEROUTING_URL, tmp)
    os.replace(tmp, path)
    print(f"saved: {path}")


def find_tool(name, explicit=None):
    """Find a program: the explicit path, next to this Python (AppImage), or on PATH."""
    if explicit:
        return explicit
    beside = os.path.join(os.path.dirname(sys.executable), name)
    if os.path.exists(beside):
        return beside
    return shutil.which(name)


def board_stats(board):
    tracks = board.GetTracks()
    vias = sum(1 for t in tracks if t.GetClass() == "PCB_VIA")
    length = sum(t.GetLength() for t in tracks if t.GetClass() != "PCB_VIA")
    board.BuildConnectivity()
    unrouted = board.GetConnectivity().GetUnconnectedCount(False)
    return len(tracks) - vias, vias, pcbnew.ToMM(length), unrouted


def clear_tracks(board):
    tracks = list(board.GetTracks())
    for t in tracks:
        board.Remove(t)
    print(f"cleared: {len(tracks)} existing track and via items")


def run_freerouting(args, dsn, ses, workdir):
    cmd = [args.java, "-jar", args.jar, "-de", dsn, "-do", ses, "-mp", str(args.passes)]
    if args.threads:
        cmd += ["-mt", str(args.threads)]
    cmd.append("-da")  # disable Freerouting's usage analytics
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        xvfb = shutil.which("xvfb-run")
        if not xvfb:
            sys.exit("error: Freerouting needs a display. Run in a desktop session or install xvfb-run.")
        cmd = [xvfb, "-a"] + cmd
    log_path = os.path.join(workdir, "freerouting.log")
    print(f"routing: up to {args.passes} passes, timeout {args.timeout} s (log: {log_path})")
    with open(log_path, "w") as log:
        try:
            result = subprocess.run(cmd, cwd=workdir, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            sys.exit(f"error: Freerouting did not finish in {args.timeout} s. Raise --timeout or lower --passes.")
    if result.returncode != 0 or not os.path.exists(ses):
        with open(log_path) as log:
            tail = log.read().splitlines()[-10:]
        sys.exit("error: Freerouting failed:\n  " + "\n  ".join(tail))


def render(board_path, out_path, kicad_cli):
    """Render copper, silkscreen and outline to SVG, or PNG through ImageMagick."""
    cli = find_tool("kicad-cli", kicad_cli)
    if not cli:
        print("warning: kicad-cli not found, no render (use --kicad-cli)")
        return
    svg = out_path if out_path.lower().endswith(".svg") else os.path.splitext(out_path)[0] + ".svg"
    layers = "F.Cu,B.Cu,F.Silkscreen,Edge.Cuts"
    subprocess.run(
        [cli, "pcb", "export", "svg", board_path, "-l", layers, "--mode-single", "--fit-page-to-board", "-o", svg],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if svg == out_path:
        print(f"render: {svg}")
        return
    magick = shutil.which("magick") or shutil.which("convert")
    if not magick:
        print(f"warning: ImageMagick not found, render left as {svg}")
        return
    subprocess.run([magick, "-density", "200", "-background", "white", svg, "-flatten", out_path], check=True)
    os.remove(svg)
    print(f"render: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("board", nargs="?", help="input .kicad_pcb file")
    parser.add_argument("-o", "--output", help="write the routed board to this .kicad_pcb file")
    parser.add_argument("-i", "--in-place", action="store_true", help="overwrite the input board (a .bak copy is kept)")
    parser.add_argument("--clear", action="store_true", help="delete existing tracks and vias before routing")
    parser.add_argument("--passes", type=int, default=30, help="maximum autorouter passes (default: 30)")
    parser.add_argument("--threads", type=int, help="optimizer threads (default: Freerouting's choice)")
    parser.add_argument("--timeout", type=int, default=600, help="stop Freerouting after this many seconds (default: 600)")
    parser.add_argument("--render", metavar="FILE", help="also render the result to FILE (.png needs ImageMagick, or .svg)")
    parser.add_argument("--keep", metavar="DIR", help="keep the DSN, SES and log files in this directory")
    parser.add_argument("--jar", default=os.environ.get("FREEROUTING_JAR", DEFAULT_JAR),
                        help="Freerouting jar (default: $FREEROUTING_JAR or %(default)s)")
    parser.add_argument("--java", default=shutil.which("java") or "java", help="Java program (default: java on PATH)")
    parser.add_argument("--kicad-cli", help="kicad-cli program for --render (default: next to this Python, or on PATH)")
    parser.add_argument("--download", action="store_true",
                        help=f"download Freerouting {FREEROUTING_VERSION} to --jar, then continue (or exit if no board)")
    args = parser.parse_args()

    if args.download:
        download_jar(args.jar)
        if not args.board:
            return
    if not args.board:
        parser.error("give a board file (or only --download)")
    if not args.output and not args.in_place:
        parser.error("give -o OUTPUT or --in-place")
    if args.output and args.in_place:
        parser.error("-o and --in-place cannot be used together")
    if not os.path.exists(args.jar):
        parser.error(f"Freerouting jar not found: {args.jar} (run with --download, or give --jar)")

    board = pcbnew.LoadBoard(args.board)
    if args.clear:
        clear_tracks(board)

    workdir = args.keep or tempfile.mkdtemp(prefix="route_board_")
    os.makedirs(workdir, exist_ok=True)
    dsn = os.path.abspath(os.path.join(workdir, "board.dsn"))
    ses = os.path.abspath(os.path.join(workdir, "board.ses"))
    if os.path.exists(ses):
        os.remove(ses)

    if not pcbnew.ExportSpecctraDSN(board, dsn):
        sys.exit("error: KiCad could not export the DSN file")
    run_freerouting(args, dsn, ses, workdir)
    if not pcbnew.ImportSpecctraSES(board, ses):
        sys.exit("error: KiCad could not import the SES file")

    tracks, vias, length, unrouted = board_stats(board)
    print(f"result: {tracks} track segments, {vias} vias, {length:.0f} mm of track, {unrouted} unrouted connections")

    target = args.board if args.in_place else args.output
    if args.in_place:
        shutil.copy2(args.board, args.board + ".bak")
        print(f"backup: {args.board}.bak")
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    board.Save(target)
    if not os.path.exists(target):
        sys.exit(f"error: KiCad could not write {target}")
    print(f"written: {target}")

    if args.render:
        render(target, args.render, args.kicad_cli)
    if not args.keep:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
