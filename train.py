import copy
from torch import optim
from torch import nn


def _generator_training_callback(
        loss_log_interval,
        image_log_interval,
        current_task,
        total_tasks,
        total_iterations):

    def cb(generator, progress, batch_index, result):
        # TODO: NOT IMPLEMENTED YET
        pass

    return cb


def _solver_training_callback(
        loss_log_interval,
        eval_log_interval,
        current_task,
        total_tasks,
        total_iterations):

    def cb(solver, progress, batch_index, result):
        # TODO: NOT IMPLEMENTED YET
        pass

    return cb


def train(scholar, train_datasets, test_datasets, replay_mode,
          generator_c_updates_per_g_update=5,
          generator_iterations=2000,
          solver_iterations=1000,
          importance_of_new_task=.5,
          batch_size=32,
          test_size=1024,
          sample_size=36,
          lr=1e-03, weight_decay=1e-05,
          loss_log_interval=30,
          eval_log_interval=50,
          image_log_interval=100,
          cuda=False):
    # define solver criterion and generators for the scholar model.
    solver_criterion = nn.CrossEntropyLoss()
    solver_optimizer = optim.Adam(
        scholar.solver.parameters(),
        lr=lr, weight_decay=weight_decay,
    )
    generator_g_optimizer = optim.Adam(
        scholar.generator.generator.parameters(),
        lr=lr, weight_decay=weight_decay
    )
    generator_c_optimizer = optim.Adam(
        scholar.generator.critic.parameters(),
        lr=lr, weight_decay=weight_decay,
    )

    # set the criterion, optimizers, and training configurations for the
    # scholar model.
    scholar.solver.set_criterion(solver_criterion)
    scholar.solver.set_optimizer(solver_optimizer)
    scholar.generator.set_generator_optimizer(generator_g_optimizer)
    scholar.generator.set_critic_optimizer(generator_c_optimizer)
    scholar.generator.set_critic_updates_per_generator_update(
        generator_c_updates_per_g_update
    )
    scholar.train()

    # define the previous scholar who will generate samples of previous tasks.
    previous_scholar = None
    previous_datasets = None

    for task, train_dataset in enumerate(train_datasets, 1):
        # define callbacks for visualizing the training process.
        generator_training_callbacks = [_generator_training_callback(
            loss_log_interval=loss_log_interval,
            image_log_interval=image_log_interval,
            current_task=task,
            total_tasks=len(train_datasets),
            total_iterations=generator_iterations,
        )]
        solver_training_callbacks = [_solver_training_callback(
            loss_log_interval=loss_log_interval,
            eval_log_interval=eval_log_interval,
            current_task=task,
            total_tasks=len(train_datasets),
            total_iterations=generator_iterations,
        )]

        # train the scholar with generative replay.
        scholar.train_with_replay(
            train_dataset,
            scholar=previous_scholar,
            previous_datasets=previous_datasets,
            importance_of_new_task=importance_of_new_task,
            batch_size=batch_size,
            generator_iterations=generator_iterations,
            generator_training_callbacks=generator_training_callbacks,
            solver_iterations=solver_iterations,
            solver_training_callbacks=solver_training_callbacks,
        )

        previous_scholar = (
            copy.deepcopy(scholar) if replay_mode == 'generative-replay' else
            None
        )
        previous_datasets = (
            train_datasets[:task-1] if replay_mode == 'exect-replay' else
            None
        )
