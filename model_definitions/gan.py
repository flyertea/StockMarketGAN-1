import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import os


# SEED = 42
tf.set_random_seed(0)
# np.random.seed(SEED)


class GAN():

    def sample_Z(self, batch_size, n):
        #return np.random.uniform(-1., 1., size=(batch_size, n))
        return np.random.normal(loc=0.0, scale=1.0, size=(batch_size, n))

    def __init__(self, num_features, num_historical_days, generator_input_size=200):

        self.X = tf.placeholder(tf.float32, shape=[None, num_historical_days, num_features])
        X = tf.reshape(self.X, [-1, num_historical_days, 1, num_features])
        self.Z = tf.placeholder(tf.float32, shape=[None, generator_input_size])
        self.keep_prob = tf.placeholder(tf.float32, shape=[])

        generator_output_size = num_features*num_historical_days
        with tf.variable_scope("generator"):
            W1 = tf.Variable(tf.truncated_normal([generator_input_size, generator_output_size*10]))
            b1 = tf.Variable(tf.truncated_normal([generator_output_size*10]))

            h1 = tf.nn.sigmoid(tf.matmul(self.Z, W1) + b1)

            W2 = tf.Variable(tf.truncated_normal([generator_output_size*10, generator_output_size*5]))
            b2 = tf.Variable(tf.truncated_normal([generator_output_size*5]))

            h2 = tf.nn.sigmoid(tf.matmul(h1, W2) + b2)


            W3 = tf.Variable(tf.truncated_normal([generator_output_size*5, generator_output_size]))
            b3 = tf.Variable(tf.truncated_normal([generator_output_size]))

            g_log_prob = tf.matmul(h2, W3) + b3
            g_log_prob = tf.reshape(g_log_prob, [-1, num_historical_days, 1, num_features])
            self.gen_data = tf.reshape(g_log_prob, [-1, num_historical_days, num_features])

            theta_G = [W1, b1, W2, b2, W3, b3]

        with tf.variable_scope("discriminator"):
            #[filter_height, filter_width, in_channels, out_channels]
            k1 = tf.Variable(tf.truncated_normal([3, 1, num_features, 32],
                stddev=0.1, dtype=tf.float32))
            b1 = tf.Variable(tf.zeros([32], dtype=tf.float32))

            k2 = tf.Variable(tf.truncated_normal([5, 1, 32, 64],
                stddev=0.1, dtype=tf.float32))
            b2 = tf.Variable(tf.zeros([64], dtype=tf.float32))


            k3 = tf.Variable(tf.truncated_normal([5, 1, 64, 128],
                stddev=0.1, dtype=tf.float32))
            b3 = tf.Variable(tf.zeros([128], dtype=tf.float32))


            W1 = tf.Variable(tf.truncated_normal([3*1*128, 128]))
            b4 = tf.Variable(tf.truncated_normal([128]))

            W2 = tf.Variable(tf.truncated_normal([128, 1]))

            theta_D = [k1, b1, k2, b2, k3, b3, W1, b4, W2]

        def discriminator(X):
            conv = tf.nn.conv2d(X,k1,strides=[1, 2, 1, 1],padding='SAME')
            relu = tf.nn.relu(tf.nn.bias_add(conv, b1))
            relu = tf.nn.dropout(relu, self.keep_prob)

            conv = tf.nn.conv2d(relu, k2,strides=[1, 2, 1, 1],padding='SAME')
            relu = tf.nn.relu(tf.nn.bias_add(conv, b2))
            relu = tf.nn.dropout(relu, self.keep_prob)


            conv = tf.nn.conv2d(relu, k3, strides=[1, 2, 1, 1], padding='SAME')
            relu = tf.nn.relu(tf.nn.bias_add(conv, b3))
            relu = tf.nn.dropout(relu, self.keep_prob)

            flattened_convolution_size = int(relu.shape[1]) * int(relu.shape[2]) * int(relu.shape[3])
            print(relu.shape[1]), int(relu.shape[2]), int(relu.shape[3])
            flattened_convolution = features = tf.reshape(relu, [-1, flattened_convolution_size])
            flattened_convolution = tf.nn.dropout(flattened_convolution, self.keep_prob)

            h1 = tf.nn.relu(tf.matmul(flattened_convolution, W1) + b4)

            D_logit = tf.matmul(h1, W2)
            D_prob = tf.nn.sigmoid(D_logit)
            return D_prob, D_logit, features

        D_real, D_logit_real, self.features = discriminator(X)
        D_fake, D_logit_fake, _ = discriminator(g_log_prob)


        # D_loss_real = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=D_logit_real, labels=tf.ones_like(D_logit_real)))
        # D_loss_fake = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=D_logit_fake, labels=tf.zeros_like(D_logit_fake)))
        # self.D_loss = D_loss_real + D_loss_fake
        # self.G_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=D_logit_fake, labels=tf.ones_like(D_logit_fake)))

        self.D_loss = -tf.reduce_mean(tf.log(D_real) + tf.log(1.0 - D_fake))
        self.G_loss = -tf.reduce_mean(tf.log(D_fake)) 


        self.D_solver = tf.train.AdamOptimizer(learning_rate=0.001).minimize(self.D_loss, var_list=theta_D)
        self.G_solver = tf.train.AdamOptimizer(learning_rate=0.001).minimize(self.G_loss, var_list=theta_G)
        self.clip_D = [p.assign(tf.clip_by_value(p, -0.01, 0.01)) for p in theta_D]