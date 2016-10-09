import re
import math
import tempfile
import itertools as it
from functools import wraps
import os
import copy

re_comments = re.compile(r";.*$")


def inplace(fxn):
    @wraps(fxn)
    def _(self, *args, **kwargs):
        result = fxn(self, *args, **kwargs)
        new_gcode = copy.deepcopy(self)
        new_gcode.lines = list(result)
        return new_gcode
    return _


class GCode(object):

    def __init__(self, lines):
        self.raw_lines = lines
        self.lines = list(self.process_lines(lines))

    def reset(self):
        self.lines = list(self.process_lines(self.raw_lines))

    @staticmethod
    def process_lines(lines):
        for line in lines:
            line_nocomments = re_comments.subn("", line)[0].strip()
            if line_nocomments:
                command, *params_raw = line_nocomments.split()
                params = {p[0]: float(p[1:]) for p in params_raw}
                yield {"command": command, **params}

    def shape_bounds(self):
        minx, miny, minz = 1e8, 1e8, 1e8
        maxx, maxy, maxz = -1e8, -1e8, -1e8
        for line in self.lines:
            if line['command'] == 'G1':
                if 'X' in line:
                    minx = min(minx, line['X'])
                    maxx = max(maxx, line['X'])
                if 'Y' in line:
                    miny = min(miny, line['Y'])
                    maxy = max(maxy, line['Y'])
                if 'Z' in line:
                    minz = min(minz, line['Z'])
                    maxz = max(maxz, line['Z'])
        return (minx, maxx), (miny, maxy), (minz, maxz)

    @inplace
    def normalize_moves(self, lines=None, keep_aspect=True):
        lines = lines or self.lines
        ranges = self.shape_bounds()
        if not keep_aspect:
            norm = {
                "X": lambda x: (x + ranges[0][0]) / (ranges[0][1] - ranges[0][0]),
                "Y": lambda y: (y + ranges[1][0]) / (ranges[1][1] - ranges[1][0]),
                "Z": lambda z: (z + ranges[2][0]) / (ranges[2][1] - ranges[2][0])
            }
        else:
            aspect = min(1.0 / (r[1] - r[0]) for r in ranges)
            norm = {
                "X": lambda x: aspect * (x + ranges[0][0]),
                "Y": lambda y: aspect * (y + ranges[1][0]),
                "Z": lambda z: aspect * (z + ranges[2][0])
            }
        identity = lambda x: x
        for line in lines:
            yield {k: norm.get(k, identity)(v)
                   for k, v in line.items()}

    @inplace
    def relative_moves(self, lines=None):
        lines = lines or self.lines
        pos = {f: None for f in 'XYZ'}
        started = False
        for line in lines:
            if line['command'] == 'G1':
                if not started and all(pos.values()):
                    yield {"command": "G1", "X": 0, "Y": 0, "Z": 0}
                    started = True
                elif started:
                    rel_move = {k: line.get(k, p) - p for k, p in pos.items()}
                    params = {k: v for k, v in line.items() if k not in 'XYZ'}
                    yield {**params, **rel_move}
                for k in pos:
                    pos[k] = line.get(k, pos[k])

    def to_turtle(self, lines=None, filter_fxn=None, scale=1):
        lines = lines or self.lines
        import turtle
        from tqdm import tqdm
        turtle.speed(0)
        turtle.radians()
        turtle.home()
        turtle.clear()
        if filter_fxn is not None:
            lines = it.takewhile(filter_fxn, lines)
        for move in tqdm(list(lines)):
            if 'E' in move:
                turtle.pencolor('black')
            else:
                turtle.pencolor('yellow')
            turtle.setheading(math.atan2(move['Y'], move['X']))
            turtle.forward(scale * (move['Y']**2 + move['X']**2)**0.5)
        input()

    @staticmethod
    def stl_to_gcode(filename):
        gcodes = []
        filename = os.path.abspath(filename)
        with tempfile.TemporaryDirectory() as tmpdirname:
            os.symlink(filename, os.path.join(tmpdirname, 'input.stl'))
            retcode = os.system("slic3r --split {}/input.stl"
                                .format(tmpdirname))
            if retcode != 0:
                raise Exception("Error creating gcode")
            gfilename = os.path.join(tmpdirname, 'temp.gcode')
            for stlfile in os.listdir(tmpdirname):
                if stlfile == "input.stl":
                    continue
                stlfile = os.path.join(tmpdirname, stlfile)
                print("Processing: ", stlfile)
                retcode = os.system(("slic3r --bottom-solid-layers=0 "
                                     "--top-solid-layers=0 --perimeters=1 "
                                     "--fill-density=0 --skirts=0 {infile} "
                                     "-o {outfile}").format(infile=stlfile,
                                                            outfile=gfilename))
                if retcode != 0:
                    raise Exception("Error creating gcode")
                with open(gfilename) as fd:
                    gcodes.append(GCode(list(fd)))
                    print("Num lines: ", len(gcodes[-1].lines))
        return gcodes


if __name__ == "__main__":
    # g = GCode(list(open("./data/hook_simple.gcode")))
    g = GCode.stl_to_gcode("./data/Killer_Queen_Jojo_Skull_Redo.stl")[0]
    g.normalize_moves().relative_moves().to_turtle(scale=250)
