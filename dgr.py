import abc
import utils
import random
import torch
from torch import nn
from torch.autograd import Variable


# ============
# Base Classes
# ============

class GenerativeMixin(object):
    """Mixin which defines a sampling iterface for a generative model."""
    def sample(self, size):
        raise NotImplementedError


class BatchTrainable(nn.Module, metaclass=abc.ABCMeta):
    """
    Abstract base class which defines a generative-replay based training
    interface for a model.

    """
    @abc.abstractmethod
    def train_a_batch(self, x, y):
        raise NotImplementedError


# ==============================
# Deep Generative Replay Modules
# ==============================

class Generator(GenerativeMixin, BatchTrainable):
    """Abstract generator module of a scholar module"""


class Solver(BatchTrainable):
    """Abstract solver module of a scholar module"""
    def __init__(self):
        super().__init__()
        self.optimizer = None
        self.criterion = None

    @abc.abstractmethod
    def forward(self, x):
        raise NotImplementedError

    def solve(self, x):
        scores = self(x)
        _, predictions = torch.max(scores, 1)
        return predictions

    def train_a_batch(self, x, y):
        self.optimizer.zero_grad()
        loss = self.criterion(self.forward(x), y)
        loss.backward()
        self.optimizer.step()
        return {'loss': loss}

    def set_optimizer(self, optimizer):
        self.optimizer = optimizer

    def set_criterion(self, criterion):
        self.criterion = criterion


class Scholar(GenerativeMixin, nn.Module):
    """Scholar for Deep Generative Replay"""
    def __init__(self, label, generator, solver):
        super().__init__()
        self.label = label
        self.generator = generator
        self.solver = solver

    def train_with_replay(self, dataset, scholar=None,
                          importance_of_new_task=.5, batch_size=32,
                          generator_iteration=2000,
                          generator_training_callbacks=None,
                          solver_iteration=1000,
                          solver_training_callbacks=None):

        # train the generator of the scholar.
        self._train_batch_trainable_with_replay(
            self.generator, dataset, scholar,
            importance_of_new_task=importance_of_new_task,
            batch_size=batch_size,
            iteration=generator_iteration,
            training_callbacks=generator_training_callbacks,
        )

        # train the solver of the scholar.
        self._train_batch_trainable_with_replay(
            self.solver, dataset, scholar,
            importance_of_new_task=importance_of_new_task,
            batch_size=batch_size,
            iteration=solver_iteration,
            training_callbacks=solver_training_callbacks,
        )

    def sample(self, size):
        x = self.generator.sample(size)
        y = self.solver.solve(x)
        return x, y

    def _train_batch_trainable_with_replay(
            self, trainable, dataset, scholar=None,
            importance_of_new_task=.5, batch_size=32, iteration=1000,
            training_callbacks=None):

        # create a data loader for the dataset.
        data_loader = iter(utils.get_data_loader(
            dataset, batch_size, cuda=self._is_on_cuda()
        ))

        for i in range(iteration):
            # decide from where to sample the training data.
            sample_from_scholar = (
                random.random() > importance_of_new_task and
                scholar is not None
            )

            # sample the training data.
            x, y = (
                scholar.sample(batch_size) if sample_from_scholar else
                next(data_loader)
            )

            # wrap the data with variables.
            x = Variable(x).cuda() if self._is_on_cuda() else Variable(x)
            y = Variable(y).cuda() if self._is_on_cuda() else Variable(y)

            # train the model with a batch.
            result = trainable.train_a_batch(x, y)

            # fire the callbacks on each iteration.
            for callback in (training_callbacks or []):
                callback(trainable, result, i)

    def _is_on_cuda(self):
        return iter(self.parameters()).next().is_cuda