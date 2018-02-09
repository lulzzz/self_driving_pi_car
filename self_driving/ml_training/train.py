import tensorflow as tf
import os
import numpy as np
import shutil
import argparse
import sys
import inspect

from DataHolder import DataHolder
from Config import Config
from Trainer import Trainer
from DFN import DFN
from util import reconstruct_from_record
from util import int2command


almost_current = os.path.abspath(inspect.getfile(inspect.currentframe()))
currentdir = os.path.dirname(almost_current)
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from plot.util import plotconfusion # noqa


def train(mode,
          records,
          height,
          width,
          channels,
          architecture,
          activations,
          batch_size,
          epochs,
          num_steps,
          save_step,
          learning_rate,
          optimizer,
          verbose,
          name,
          move):
    """
    Trains a model

    :param height: image height
    :type heights: int
    :param width: image width
    :type width: int
    :param channels: image channels
    :type channels: int
    :param architecture: network architecture
    :type architecture: list of int
    :param activations: list of different tf functions
    :type activations: list of tf.nn.sigmoid, tf.nn.relu, tf.nn.tanh
    :param batch_size: batch size for training
    :type batch_size: int
    :param epochs: number of epochs
    :type epochs: int
    :param num_steps: number of iterations for each epoch
    :type num_steps: int
    :param save_step: when step % save_step == 0, the model
                      parameters are saved.
    :type save_step: int
    :param learning_rate: learning rate for the optimizer
    :type learning_rate: float
    :param optimizer: a optimizer from tensorflow.
    :type optimizer: tf.train.GradientDescentOptimizer,
                     tf.train.AdadeltaOptimizer,
                     tf.train.AdagradOptimizer,
                     tf.train.AdagradDAOptimizer,
                     tf.train.AdamOptimizer,
                     tf.train.FtrlOptimizer,
                     tf.train.ProximalGradientDescentOptimizer,
                     tf.train.ProximalAdagradOptimizer,
                     tf.train.RMSPropOptimizer
    :param verbose: param to control if the trainig will be printed
                    and if the confusion matrix will be calculated.
    :type verbose: bool
    :param name: name to save the confusion matrix plot.
    :type name: str
    :param move: param to control if the checkpoints path
                 will be moved to the parent folder.
    :type move: bool
    """

    if os.path.exists("checkpoints"):
        shutil.rmtree("checkpoints")

    config = Config(height=height,
                    width=width,
                    channels=channels,
                    architecture=architecture,
                    activations=activations,
                    batch_size=batch_size,
                    epochs=epochs,
                    num_steps=num_steps,
                    save_step=save_step,
                    learning_rate=learning_rate,
                    optimizer=optimizer)

    data = DataHolder(config,
                      records=records)

    graph = tf.Graph()
    network = DFN(graph, config)
    trainer = Trainer(graph, config, network, data)
    print("\nTraining in the {} data\n".format(mode))
    print("params:\n{}\n".format(config.get_status()))
    trainer.fit(verbose=verbose)
    if verbose:
        valid_images, valid_labels, _ = reconstruct_from_record(data.get_valid_tfrecord()) # noqa
        valid_images = valid_images.astype(np.float32) / 255
        valid_pred = trainer.predict(valid_images)
        valid_labels = valid_labels.reshape((valid_labels.shape[0],))
        plotconfusion(valid_labels, valid_pred, name + ".png", int2command, classes=["left", "right", "up"]) # noqa
    if move:
        dst = os.path.join(parentdir, "checkpoints")
        shutil.move("checkpoints", dst)


def main():
    """
    Main script to train one model using one kind of data.

    "mode" is the argument to choose which kind of data will be used:
        "pure": rgb image with no manipulation.
        "flip": flippped rgb image (a image with label "left" is
                flipped and transform in an image with label
                "right", and vice versa; to have a balanced data).
        "aug": flippped rgb image with new shadowed and blurred images.
        "bin": binary image, only one channel.
        "gray": grayscale image, only one channel.
        "green": image with only the green channel.
    """
    parser = argparse.ArgumentParser(description='Train a model')
    parser.add_argument("-m",
                        "--mode",
                        type=str,
                        default="bin",
                        help="mode for data: pure, flip, aug, bin, gray, green (default=pure)")  # noqa
    parser.add_argument("-he",
                        "--height",
                        type=int,
                        default=90,
                        help="image height (default=90)")
    parser.add_argument("-w",
                        "--width",
                        type=int,
                        default=160,
                        help="image width (default=160)")
    parser.add_argument('-a',
                        '--architecture',
                        type=int,
                        nargs='+',
                        help='sizes for hidden layers and output layer, should end with "4" !, (default=[4])',  # noqa
                        default=[4])
    parser.add_argument('-ac',
                        '--activations',
                        type=str,
                        nargs='+',
                        help='activations: relu, sigmoid, tanh (defaul=None)',
                        default=None)
    parser.add_argument("-b",
                        "--batch_size",
                        type=int,
                        default=32,
                        help="batch size (default=32)")
    parser.add_argument("-e",
                        "--epochs",
                        type=int,
                        default=5,
                        help="epochs for training (default=5)")
    parser.add_argument("-ns",
                        "--num_steps",
                        type=int,
                        default=1000,
                        help="number of steps for each epoch (default=1000)")
    parser.add_argument("-ss",
                        "--save_step",
                        type=int,
                        default=100,
                        help="number of steps to save variables (default=100)")
    parser.add_argument("-lr",
                        "--learning_rate",
                        type=float,
                        default=0.02,
                        help="learning rate (default=0.02)")
    opt_list = """optimizers: GradientDescent,
                              Adadelta,
                              Adagrad,
                              Adam,
                              Ftrl,
                              ProximalGradientDescent,
                              ProximalAdagrad,
                              RMSProp"""
    parser.add_argument("-o",
                        "--optimizer",
                        type=str,
                        default="GradientDescent",
                        help=opt_list + "(default=GradientDescent)")
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="print training results and calculate confusion matrix (default=False)")  # noqa
    parser.add_argument("-n",
                        "--name",
                        type=str,
                        default="Confusion_Matrix",
                        help="name to save confusion matrix plot (default=Confusion_Matrix)")  # noqa
    parser.add_argument("-mv",
                        "--move",
                        action="store_true",
                        default=False,
                        help="move checpoits to parent folder (default=False)")  # noqa
    args = parser.parse_args()
    if args.mode == "bin" or args.mode == "gray" or args.mode == "green":
        channels = 1
    else:
        channels = 3
    records = ["_train.tfrecords", "_valid.tfrecords", "_test.tfrecords"]
    new_records = []
    for record in records:
        record = args.mode + record
        new_records.append(record)

    optimizer_dict = {"GradientDescent": tf.train.GradientDescentOptimizer, # noqa
                      "Adadelta": tf.train.AdadeltaOptimizer,
                      "Adagrad": tf.train.AdagradOptimizer,
                      "Adam": tf.train.AdamOptimizer,
                      "Ftrl": tf.train.FtrlOptimizer,
                      "ProximalGradientDescent": tf.train.ProximalGradientDescentOptimizer, # noqa
                      "ProximalAdagrad": tf.train.ProximalAdagradOptimizer, # noqa
                      "RMSProp":tf.train.RMSPropOptimizer} # noqa

    activations_dict = {"relu": tf.nn.relu,
                        "sigmoid": tf.nn.sigmoid,
                        "tanh": tf.nn.tanh}
    if args.activations is not None:
        activations = [activations_dict[act] for act in args.activations]
    else:
        activations = args.activations
    optimizer = optimizer_dict[args.optimizer]

    train(mode=args.mode,
          records=new_records,
          height=args.height,
          width=args.width,
          channels=channels,
          architecture=args.architecture,
          activations=activations,
          batch_size=args.batch_size,
          epochs=args.epochs,
          num_steps=args.num_steps,
          save_step=args.save_step,
          learning_rate=args.learning_rate,
          optimizer=optimizer,
          verbose=args.verbose,
          name=args.name,
          move=args.move)


if __name__ == '__main__':
    main()