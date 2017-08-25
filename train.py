# Brief:     Train a densenet for image classification
# Data:      24/Aug./2017
# E-mail:    huyixuanhyx@gmail.com
# License:   Apache 2.0
# By:        Yeephycho @ Hong Kong

# Code still under construction


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import numpy as np
import os


DATA_DIR = "./tfrecord"
TRAINING_SET_SIZE = 2512
global_step = TRAINING_SET_SIZE * 100
TEST_SET_SIZE = 908
BATCH_SIZE = 16
IMAGE_SIZE = 224


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=value))

def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

# image object from tfrecord
class _image_object:
    def __init__(self):
        self.image = tf.Variable([], dtype = tf.string)
        self.height = tf.Variable([], dtype = tf.int64)
        self.width = tf.Variable([], dtype = tf.int64)
        self.filename = tf.Variable([], dtype = tf.string)
        self.label = tf.Variable([], dtype = tf.int32)

def read_and_decode(filename_queue):
    with tf.name_scope('data_provider'):
        reader = tf.TFRecordReader()
        _, serialized_example = reader.read(filename_queue)
        features = tf.parse_single_example(serialized_example, features = {
            "image/encoded": tf.FixedLenFeature([], tf.string),
            "image/height": tf.FixedLenFeature([], tf.int64),
            "image/width": tf.FixedLenFeature([], tf.int64),
            "image/filename": tf.FixedLenFeature([], tf.string),
            "image/class/label": tf.FixedLenFeature([], tf.int64),})
        image_encoded = features["image/encoded"]
        image_raw = tf.image.decode_jpeg(image_encoded, channels=3)
        image_object = _image_object()
        image_object.image = tf.image.resize_image_with_crop_or_pad(image_raw, IMAGE_SIZE, IMAGE_SIZE)
        image_object.height = features["image/height"]
        image_object.width = features["image/width"]
        image_object.filename = features["image/filename"]
        image_object.label = tf.cast(features["image/class/label"], tf.int64)
    return image_object


def flower_input(if_random = True, if_training = True):
    with tf.name_scope('image_reader_and_preprocessor'):
        if(if_training):
            filenames = [os.path.join(DATA_DIR, "train.tfrecord")]
        else:
            filenames = [os.path.join(DATA_DIR, "test.tfrecord")]

        for f in filenames:
            if not tf.gfile.Exists(f):
                raise ValueError("Failed to find file: " + f)
        filename_queue = tf.train.string_input_producer(filenames)
        image_object = read_and_decode(filename_queue)
        distorted_image = tf.image.random_flip_left_right(image_object.image)
        image = tf.image.per_image_standardization(distorted_image)
    #    image = tf.image.adjust_gamma(tf.cast(image_object.image, tf.float32), gamma=1, gain=1) # Scale image to (0, 1)
        label = image_object.label
        filename = image_object.filename

        if(if_random):
            min_fraction_of_examples_in_queue = 0.4
            min_queue_examples = int(TRAINING_SET_SIZE * min_fraction_of_examples_in_queue)
            print("Filling queue with %d images before starting to train. " "This will take a few minutes." % min_queue_examples)
            num_preprocess_threads = 1
            image_batch, label_batch, filename_batch = tf.train.shuffle_batch(
                [image, label, filename],
                batch_size = BATCH_SIZE,
                num_threads = num_preprocess_threads,
                capacity = min_queue_examples + 3 * BATCH_SIZE,
                min_after_dequeue = min_queue_examples)
            image_batch = tf.reshape(image_batch, (BATCH_SIZE, IMAGE_SIZE, IMAGE_SIZE, 3))
            label_offset = -tf.ones([BATCH_SIZE], dtype=tf.int64, name="label_batch_offset")
            label_batch = tf.one_hot(tf.add(label_batch, label_offset), depth=5, on_value=1.0, off_value=0.0)
        else:
            image_batch, label_batch, filename_batch = tf.train.batch(
                [image, label, filename],
                batch_size = BATCH_SIZE,
                num_threads = 1)
            image_batch = tf.reshape(image_batch, (BATCH_SIZE, IMAGE_SIZE, IMAGE_SIZE, 3))
            label_offset = -tf.ones([BATCH_SIZE], dtype=tf.int64, name="label_batch_offset")
            label_batch = tf.one_hot(tf.add(label_batch, label_offset), depth=5, on_value=1.0, off_value=0.0)
    return image_batch, label_batch, filename_batch


def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.05)
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.constant(0.02, shape=shape)
    return tf.Variable(initial)

def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')

def max_pool_2x2(x):
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')

def flower_inference(image_batch):
    with tf.name_scope('conv1'):
        W_conv1 = weight_variable([5, 5, 3, 32])
        b_conv1 = bias_variable([32])

        x_image = tf.reshape(image_batch, [-1, IMAGE_SIZE, IMAGE_SIZE, 3])

        h_conv1 = tf.nn.relu(conv2d(x_image, W_conv1) + b_conv1)
        h_pool1 = max_pool_2x2(h_conv1) # 112

    with tf.name_scope('conv2'):
        W_conv2 = weight_variable([5, 5, 32, 64])
        b_conv2 = bias_variable([64])

        h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2) + b_conv2)
        h_pool2 = max_pool_2x2(h_conv2) # 56

    with tf.name_scope('conv3'):
        W_conv3 = weight_variable([5, 5, 64, 128])
        b_conv3 = bias_variable([128])

        h_conv3 = tf.nn.relu(conv2d(h_pool2, W_conv3) + b_conv3)
        h_pool3 = max_pool_2x2(h_conv3) # 28

    with tf.name_scope('conv4'):
        W_conv4 = weight_variable([5, 5, 128, 256])
        b_conv4 = bias_variable([256])

        h_conv4 = tf.nn.relu(conv2d(h_pool3, W_conv4) + b_conv4)
        h_pool4 = max_pool_2x2(h_conv4) # 14

    with tf.name_scope('conv5'):
        W_conv5 = weight_variable([5, 5, 256, 256])
        b_conv5 = bias_variable([256])

        h_conv5 = tf.nn.relu(conv2d(h_pool4, W_conv5) + b_conv5)
        h_pool5 = max_pool_2x2(h_conv5) # 7

    with tf.name_scope('fc'):
        W_fc1 = weight_variable([7*7*256, 2048])
        b_fc1 = bias_variable([2048])

        h_pool5_flat = tf.reshape(h_pool5, [-1, 7*7*256])
        h_fc1 = tf.nn.relu(tf.matmul(h_pool5_flat, W_fc1) + b_fc1)

        h_fc1_drop = tf.nn.dropout(h_fc1, 0.6)

        W_fc2 = weight_variable([2048, 256])
        b_fc2 = bias_variable([256])

        h_fc2 = tf.nn.relu(tf.matmul(h_fc1_drop, W_fc2) + b_fc2)

        W_fc3 = weight_variable([256, 64])
        b_fc3 = bias_variable([64])

        h_fc3 = tf.nn.relu(tf.matmul(h_fc2, W_fc3) + b_fc3)

        W_fc4 = weight_variable([64, 5])
        b_fc4 = bias_variable([5])

        y_conv = tf.nn.softmax(tf.matmul(h_fc3, W_fc4) + b_fc4)

    return y_conv



def flower_train():
    with tf.name_scope("training"):
        image_batch_placeholder = tf.placeholder(tf.float32, shape=[None, 224, 224, 3])
        label_batch_placeholder = tf.placeholder(tf.float32, shape=[None, 5])

        image_batch, label_batch, filename_batch = flower_input(if_random = False, if_training = True)

        logits = flower_inference(image_batch_placeholder)

        #loss = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits(labels=label_batch_placeholder, logits=logits))
        loss = tf.losses.mean_squared_error(labels=label_batch_placeholder, predictions=logits)

        train_step = tf.train.GradientDescentOptimizer(0.004).minimize(loss)

        # create a summary for training loss
        tf.summary.scalar('loss', loss)

    # with tf.name_scope("evalutation"):
    #     image_batch_placeholder_eval = tf.placeholder(tf.float32, shape=[None, 224, 224, 3])
    #     label_batch_placeholder_eval = tf.placeholder(tf.int64, shape=[BATCH_SIZE])
    #
    #     image_batch_eval, label_batch_eval, filename_batch_eval = flower_input(if_random = False, if_training = False)
    #     label_batch_dense_eval = tf.arg_max(label_batch, dimension = 1)
    #
    #     logits_eval = flower_inference(image_batch_placeholder_eval)
    #     logits_dense = tf.to_int64(tf.arg_max(logits_eval, dimension = 1))
    #     correct_prediction = tf.equal(logits_dense, label_batch_placeholder_eval)
    #     accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))


    # merge all summaries into a single "operation" which we can execute in a session
    summary_op = tf.summary.merge_all()

    saver = tf.train.Saver()

    config = tf.ConfigProto()
    config.gpu_options.allow_growth=True
    with tf.Session(config=config) as sess:
    # with tf.Session() as sess:
        summary_writer = tf.summary.FileWriter("./training_log", sess.graph)

        sess.run(tf.global_variables_initializer())
        saver.restore(sess, "./models/flower.ckpt")

        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(coord=coord, sess = sess)

        check_points = int(TRAINING_SET_SIZE/BATCH_SIZE) * 4
        for epoch in range(30):
            for check_point in range(check_points):
                image_batch_train, label_batch_train, filename_train = sess.run([image_batch, label_batch, filename_batch])

                _, training_loss, summary = sess.run([train_step, loss, summary_op],
                                                       feed_dict={image_batch_placeholder: image_batch_train,
                                                                  label_batch_placeholder: label_batch_train})

                if(bool(check_point%100 == 0) & bool(check_point != 0)):
                    print("batch: ", check_point + epoch * check_points)
                    print("training loss: ", training_loss)
                    summary_writer.add_summary(summary, check_point + epoch * check_points)
                    saver.save(sess, "./models/flower.ckpt")


            # print("Evaluating")
            # accuracy_accu = 0.0
            # for i in range(int(TEST_SET_SIZE/BATCH_SIZE)):
            #     _image_batch_eval, _label_batch_eval, _filename_eval = sess.run([image_batch_eval, label_batch_dense_eval, filename_batch_eval])
            #     batch_accuracy = sess.run([accuracy], feed_dict={image_batch_placeholder_eval: _image_batch_eval,
            #                                                      label_batch_placeholder_eval: _label_batch_eval})
            #     accuracy_accu += np.asarray(batch_accuracy)
            #
            # print("Evaluation accuracy: ", accuracy_accu[0]/int(TEST_SET_SIZE/BATCH_SIZE))

        coord.request_stop()
        coord.join(threads)
        sess.close()
    return 0


def main():
    tf.reset_default_graph()
    flower_train()


if __name__ == '__main__':
    main()
