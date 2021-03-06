'''Train a simple deep NN on the MNIST dataset.
Get to 98.40% test accuracy after 20 epochs
(there is *a lot* of margin for parameter tuning).
2 seconds per epoch on a K520 GPU.
'''

from __future__ import print_function
import numpy as np
import plac
from itertools import izip
from cytoolz import partition_all
from thinc.extra.eg import Example
import random

random.seed(1337)  # for reproducibility
np.random.seed(1337)

from keras.datasets import mnist
from keras.utils import np_utils


from keras.datasets import mnist
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.optimizers import SGD, Adam, RMSprop
from keras.utils import np_utils


from thinc.neural.nn import NeuralNet


def score_model(x_y, model):
    correct = 0
    total = 0
    scores = model.predict_batch([x for x, y in x_y])
    for i, (_, gold) in enumerate(x_y):
        correct += scores[i].argmax() == gold
        total += 1
    return float(correct) / total


def best_first_sgd(model, train_data, check_data):
    print(model.widths)
    print("Itn:\tParent\tScore\tNew\tTrain\tCheck\tEta")
    train_acc = 0
    queue = [[score_model(check_data, model), 0, model]]
    limit = 8
    i = 0
    best_model = model
    best_acc = 0.0
    best_i = 0
    try:
        while best_i > (i - 100) and train_acc < 0.999:
            queue.sort(reverse=True)
            queue = queue[:limit]
            prev_score, parent, model = queue[0]
            queue[0][0] -= 0.0005
            train_acc, new_model = get_new_model(train_data, model)
            check_acc = score_model(check_data, new_model)
            ratio = min(check_acc / train_acc, 1.0)
            
            i += 1
            queue.append([check_acc * ratio, i, new_model])
            
            print('%d:\t%d\t%.5f\t%.5f\t%.5f\t%.5f\t%.4f' % (i, parent, prev_score,
                queue[-1][0], train_acc, check_acc, new_model.eta))
            if check_acc >= best_acc:
                best_acc = check_acc
                best_i = i
                best_model = new_model
    except KeyboardInterrupt:
        pass
    return best_model


def get_new_model(train_data, model):
    learn_rate = np.random.normal(loc=model.eta, scale=0.001)
    if learn_rate < 0.0001:
        learn_rate = 0.0001

    new_model = NeuralNet(model.widths, update_step='sgd', eta=learn_rate, rho=model.rho)
    new_model.weights = model.weights
    new_model.tau = model.tau
    train_data = train_data + train_data
    random.shuffle(train_data)
    acc = new_model.train(train_data, batch_size=100)
    return acc, new_model


def sequential_sgd(model, train_data, check_data, n_iter=5):
    print(model.widths)
    print(model.nr_class)
    train_acc = 0.0
    check_acc = 0.0
    batch_size = 100
    for itn in range(n_iter):
        random.shuffle(train_data)
        train_acc = model.train(train_data, batch_size=batch_size)
        check_acc = score_model(check_data, model)
        print('%d:\t%.3f\t%.3f' % (itn, train_acc, check_acc))
        #batch_size = max(1, int(batch_size * 0.9))
    return check_acc, model


def stepdown_fixed_increment(input_width, output_width, n_hidden=5, scale=2):
    step_size = int((input_width - output_width) / n_hidden * scale)
    widths = [input_width]
    for i in range(n_hidden):
        if widths[-1] <= step_size:
            break
        widths.append(widths[-1] - step_size)
    widths.append(output_width)
    print(widths)
    return widths

def stepup_fixed_increment(input_width, output_width, n_hidden=5):
    step_size = int((input_width - output_width) / n_hidden)
    widths = [input_width]
    last_width = input_width
    for i in range(n_hidden):
        widths.insert(1, last_width - step_size)
        last_width -= step_size
    widths.append(output_width)
    return widths

def fixed_layer_width(input_width, output_width, n_hidden=5):
    halfway = int(abs(input_width - output_width) / 2)
    return [input_width] + [halfway] * n_hidden + [output_width]


def linear(input_width, output_width, n_hidden=5):
    return []


def multiple_of_smaller(input_width, output_width, n_hidden=5, multiple=3):
    smaller = min(input_width, output_width)
    return [input_width] + [smaller * multiple] * n_hidden + [output_width]


def power_of_two(input_width, output_width, n_hidden=5, scale=6):
    return [input_width] + [2**scale] * n_hidden + [output_width]

def main(batch_size=128, nb_epoch=10, nb_classes=10):
    # the data, shuffled and split between tran and test sets
    (X_train, y_train), (X_test, y_test) = mnist.load_data()

    X_train = X_train.reshape(60000, 784)
    X_test = X_test.reshape(10000, 784)
    X_train = X_train.astype('float64')
    X_test = X_test.astype('float64')
    X_train /= 255
    X_test /= 255
    print(X_train.shape[0], 'train samples')
    print(X_test.shape[0], 'test samples')


    train_data = zip(X_train, y_train)
    nr_train = len(train_data)
    random.shuffle(train_data)
    heldout_data = train_data[:int(nr_train * 0.1)] 
    train_data = train_data[len(heldout_data):]

    model = NeuralNet(power_of_two(784, 10, n_hidden=20, scale=6),
                      update_step='sgd', eta=0.01, rho=0.0)
    #acc, model = sequential_sgd(model, train_data, heldout_data, n_iter=50)
  
    model = best_first_sgd(model, train_data, heldout_data)
    print('Test score:', score_model(zip(X_test, y_test), model))


if __name__ == '__main__':
    plac.call(main)
    #import cProfile
    #import pstats
    #cProfile.runctx("main()", globals(), locals(), "Profile.prof")
    #s = pstats.Stats("Profile.prof")
    #s.strip_dirs().sort_stats("time").print_stats()
