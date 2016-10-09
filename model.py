from gcode import GCode
import random

import numpy as np
from keras.models import Model
from keras.layers import Dense, Embedding
from keras.layers import GRU, Input


def build_model_gru():
    main_input = Input(shape=(None, 4), dtyle='float32', name='input')
    embedding = Embedding(4, 128, dropout=0.2, name='embed')(main_input)
    gru1 = GRU(128, dropout_W=0.2, dropout_U=0.2, name='gru1')(embedding)
    gru2 = GRU(128, dropout_W=0.2, dropout_U=0.2, name='gru2')(gru1)

    x_out = Dense(1, activation='linear', name='x_out')(gru2)
    y_out = Dense(1, activation='linear', name='y_out')(gru2)
    z_out = Dense(1, activation='linear', name='z_out')(gru2)
    e_out = Dense(1, activation='softmax', name='e_out')(gru2)

    model = Model(input=[main_input], output=[x_out, y_out, z_out, e_out])
    model.compile(
        optimizer='rmsprop',
        loss=[
            'mean_squared_error',
            'mean_squared_error',
            'mean_squared_error',
            'binary_crossentropy',
        ]
    )
    return model


def training_batches(min_sequence=64, max_sequence=2048):
    filenames = ['./data/Killer_Queen_Jojo_Skull_Redo.stl']
    gcodes = [g.normalize_moves().relative_moves()
              for f in filenames for g in GCode.stl_to_gcode(f)]
    datas = list(map(gcode_to_numpy, gcodes))
    del gcodes

    def _():
        for data in datas:
            nlines = data.shape[0]
            i = 0
            while nlines > min_sequence:
                upper = min(max_sequence or nlines, nlines) - 1
                seqlen = random.randint(min_sequence, upper)
                yield (data[i:i+seqlen], data[i+seqlen])
                nlines -= seqlen + 1
                i += seqlen + 1
    return _


def gcode_to_numpy(gcode):
    data = np.zeros((len(gcode.lines), 4), np.float32)
    for i, line in enumerate(gcode.lines):
        data[i, 0] = gcode.lines[i].get('X', 0)
        data[i, 1] = gcode.lines[i].get('Y', 0)
        data[i, 2] = gcode.lines[i].get('Z', 0)
        data[i, 3] = 'E' not in gcode.lines[i]
    return data


if __name__ == "__main__":
    # model = build_model_gru()
    pass
