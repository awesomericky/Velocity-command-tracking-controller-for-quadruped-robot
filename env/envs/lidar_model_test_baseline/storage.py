import pdb

import numpy as np
import torch
from torch.utils.data.sampler import BatchSampler, SubsetRandomSampler, SequentialSampler

class DataStorage:
    def __init__(self, max_storage_size, state_dim, command_shape, P_col_shape, coordinate_shape, device):
        self.device = device

        # Core
        self.states = torch.zeros(max_storage_size, state_dim).to(self.device)
        self.commands = torch.zeros(command_shape[0], max_storage_size, command_shape[1]).to(self.device)
        self.P_cols = torch.zeros(P_col_shape[0], max_storage_size, P_col_shape[1]).to(self.device)
        self.coordinates = torch.zeros(coordinate_shape[0], max_storage_size, coordinate_shape[1]).to(self.device)

        self.max_storage_size = max_storage_size
        self.step = 0
        self.full = False

    def add_data(self, state, command, P_col, coordinate):
        """
        Add(Update) n_env number of data to the storage

        :param state: (n_env, state_dim)
        :param command: (prediction_len, n_env, command_dim)
        :param P_col: (prediction_len, n_env, P_col_dim)
        :param coordinate: (prediction_len, n_env, coordinate_dim)
        :return: None
        """
        n_env = state.shape[0]
        second_step = None
        if self.step + n_env > self.max_storage_size:
            self.full = True
            # first_step = n_env - self.step if second_step is None else n_env - second_step
            second_step = self.step + n_env - self.max_storage_size
            first_step = n_env - second_step

        if second_step == None:
            self.states[self.step:self.step + n_env, :].copy_(torch.from_numpy(state).to(self.device))
            self.commands[:, self.step:self.step + n_env, :].copy_(torch.from_numpy(command).to(self.device))
            self.P_cols[:, self.step:self.step + n_env, :].copy_(torch.from_numpy(P_col).to(self.device))
            self.coordinates[:, self.step:self.step + n_env, :].copy_(torch.from_numpy(coordinate).to(self.device))
            self.step += n_env
        else:
            self.states[self.step:, :].copy_(torch.from_numpy(state[:first_step, :]).to(self.device))
            self.states[:second_step, :].copy_(torch.from_numpy(state[first_step:, :]).to(self.device))
            self.commands[:, self.step:, :].copy_(torch.from_numpy(command[:, :first_step, :]).to(self.device))
            self.commands[:, :second_step, :].copy_(torch.from_numpy(command[:, first_step:, :]).to(self.device))
            self.P_cols[:, self.step:, :].copy_(torch.from_numpy(P_col[:, :first_step, :]).to(self.device))
            self.P_cols[:, :second_step, :].copy_(torch.from_numpy(P_col[:, first_step:, :]).to(self.device))
            self.coordinates[:, self.step:, :].copy_(torch.from_numpy(coordinate[:, :first_step, :]).to(self.device))
            self.coordinates[:, :second_step, :].copy_(torch.from_numpy(coordinate[:, first_step:, :]).to(self.device))
            self.step = second_step

    def clear(self):
        self.step = 0

    def is_full(self):
        return self.full

    def mini_batch_generator_shuffle(self, mini_batch_size):
        for indices in BatchSampler(SubsetRandomSampler(range(self.max_storage_size)), mini_batch_size, drop_last=True):
            states_batch = self.states[indices]
            commands_batch = self.commands[:, indices, :]
            P_cols_batch = self.P_cols[:, indices, :]
            coordinates_batch = self.coordinates[:, indices, :]
            yield states_batch, commands_batch, P_cols_batch, coordinates_batch

    def mini_batch_generator_inorder(self, mini_batch_size):
        for indices in BatchSampler(SequentialSampler(range(self.max_storage_size)), mini_batch_size, drop_last=True):
            states_batch = self.states[indices]
            commands_batch = self.commands[:, indices, :]
            P_cols_batch = self.P_cols[:, indices, :]
            coordinates_batch = self.coordinates[:, indices, :]
            yield states_batch, commands_batch, P_cols_batch, coordinates_batch

class Buffer:
    def __init__(self, n_env, buffer_size, feature_dim):
        """

        Implementation of FIFO (First-In-First-Out) buffer.

        For each environment, (feature_dim, buffer_size) data are being stored.

        For terminated environment, the data are initialized to zero vectors.
        """
        self.n_env = n_env
        self.feature_dim = feature_dim
        self.buffer_size = buffer_size
        self.data = np.zeros((self.n_env, self.feature_dim, self.buffer_size))

    def reset(self):
        self.data = np.zeros((self.n_env, self.feature_dim, self.buffer_size))

    def partial_reset(self, idx):
        """

        :param idx: list of environment index to be cleared (list)
        :return:
        """
        self.data[idx, :, :] = np.zeros((len(idx), self.feature_dim, self.buffer_size))

    def update(self, new_data):
        """

        :param new_data: (self.n_env, self.feature_dim)
        :return:
        """
        self.data[:, :, :-1] = self.data[:, :, 1:]
        self.data[:, :, -1] = new_data

    def return_data(self, flatten=False):
        if flatten:
            return np.swapaxes(self.data, 1, 2).reshape((self.n_env, -1))
        else:
            return self.data
