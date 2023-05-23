from test_funcs import *
from mixed_test_func import *
from bo.optimizer import Optimizer
from bo.optimizer_mixed import MixedOptimizer
import logging
import argparse
import os
import pickle
import pandas as pd
import time, datetime
from test_funcs.random_seed_config import *


# Set up the objective function
parser = argparse.ArgumentParser('Run Experiments')
parser.add_argument('-p', '--problem', type=str, default='xgboost-mnist')
parser.add_argument('--max_iters', type=int, default=150, help='Maximum number of BO iterations.')
parser.add_argument('--lamda', type=float, default=1e-6, help='the noise to inject for some problems')
parser.add_argument('--batch_size', type=int, default=1, help='batch size for BO.')
parser.add_argument('--n_trials', type=int, default=20, help='number of trials for the experiment')
parser.add_argument('--n_init', type=int, default=20, help='number of initialising random points')
parser.add_argument('--save_path', type=str, default='output/', help='save directory of the log files')
parser.add_argument('--ard', action='store_true', help='whether to enable automatic relevance determination')
parser.add_argument('-a', '--acq', type=str, default='ei', help='choice of the acquisition function.')
parser.add_argument('--random_seed_objective', type=int, default=20, help='The default value of 20 is provided also in COMBO')
parser.add_argument('-d', '--debug', action='store_true', help='Whether to turn on debugging mode (a lot of output will be generated).')
parser.add_argument('--no_save', action='store_true', help='If activated, do not save the current run into a log folder.')
parser.add_argument('--seed', type=int, default=None, help='**initial** seed setting')
parser.add_argument('-k', '--kernel_type', type=str, default=None, help='specifies the kernel type')
parser.add_argument('--infer_noise_var', action='store_true')

args = parser.parse_args()
options = vars(args)
print(options)

if args.debug:
    logging.basicConfig(level=logging.INFO)

# Sanity checks
assert args.acq in ['ucb', 'ei', 'thompson'], 'Unknown acquisition function choice ' + str(args.acq)





def main(nth_trial, mcv):
    # n_trials: number of trials for the experiment
    kwargs = {}
    # random_seed_objective? waht is 
    if args.random_seed_objective is not None:  
        assert 1 <= int(args.random_seed_objective) <= 25
        args.random_seed_objective -= 1


    # defining problem here
    if args.problem == 'pest':
        random_seed_ = sorted(generate_random_seed_pestcontrol())[args.random_seed_objective]
        f = PestControl(random_seed=random_seed_)
        kwargs = {
            'length_max_discrete': 25,
            'length_init_discrete': 20,
        }
    elif args.problem == 'func2C':
        f = Func2C(lamda=args.lamda,)
    elif args.problem == 'func3C':
        f = Func3C(lamda=args.lamda)
    elif args.problem == 'ackley53':
        f = Ackley53(lamda=args.lamda)
        kwargs = {
            'length_max_discrete': 50,
            'length_init_discrete': 30,
        }
    elif args.problem == 'MaxSAT60':
        f = MaxSAT60()
        kwargs = {
            'length_max_discrete': 60,
        }
    elif args.problem == 'xgboost-mnist':
        f = XGBoostOptTask(lamda=args.lamda, task='mnist', seed=args.seed)
    else:
        raise ValueError('Unrecognised problem type %s' % args.problem)

    n_categories = f.n_vertices
    problem_type = f.problem_type

    print('----- Starting trial %d / %d -----' % ((nth_trial + 1), args.n_trials))
    res = pd.DataFrame(np.nan, index=np.arange(int(args.max_iters*args.batch_size)),
                       columns=['Index', 'LastValue', 'BestValue', 'Time'])
    if args.infer_noise_var: noise_variance = None
    else: noise_variance = f.lamda if hasattr(f, 'lamda') else None

    if args.kernel_type is None:  kernel_type = 'mixed' if problem_type == 'mixed' else 'transformed_overlap'
    else: kernel_type = args.kernel_type

    if problem_type == 'mixed':
        optim = MixedOptimizer(f.config, f.lb, f.ub, f.continuous_dims, f.categorical_dims,
                               n_init=args.n_init, use_ard=args.ard, acq=args.acq,
                               kernel_type=kernel_type,
                               noise_variance=noise_variance,
                               **kwargs)
    else:
        optim = Optimizer(f.config, n_init=args.n_init, use_ard=args.ard, acq=args.acq,
                          kernel_type=kernel_type,
                          noise_variance=noise_variance, **kwargs)
        
    for i in range(args.max_iters):
        start = time.time()

        #
        x_next = optim.suggest(args.batch_size) 
        # x_next是？  x_next.shape = (1, 8)

        y_next = f.compute(x_next, normalize=f.normalize)
        # y_next是 ... y=f(x)？  y_next.shape = (1, )

        # Send an observation of a suggestion back to the optimizer
        optim.observe(x_next, y_next)

        # 时间    optim.suggest + f.compute + optim.observe
        end = time.time()


        # Save the full history: optim.casmopolitan.fX.shape = (iters, 1)
        if f.normalize:
            Y = np.array(optim.casmopolitan.fX) * f.std + f.mean
        else:
            Y = np.array(optim.casmopolitan.fX)


        if Y[:i].shape[0]:
            # res = pd.DataFrame
            mcv.rec(    i                   ,  'time'           )
            mcv.rec(    float(Y[-1])        ,  'this Y'          )
            mcv.rec(    float(np.min(Y[:i])),  'best Y'          )
            mcv.rec(    end-start           ,  'time cost'   )
            mcv.rec_show()
            # sequential
            if args.batch_size == 1:
                # iloc: index location，即对数据进行位置索引，从而在数据表中提取出相应的数据
                # [      iter,   本次Y,  最优Y,  本次时间花销         ]
                res.iloc[i, :] = [i, float(Y[-1]), float(np.min(Y[:i])), end-start]
            # batch
            else:
                for idx, j in enumerate(range(i*args.batch_size, (i+1)*args.batch_size)):
                    res.iloc[j, :] = [j, float(Y[-idx]), float(np.min(Y[:i*args.batch_size])), end-start]
            # x_next = x_next.astype(int)
            argmin = np.argmin(Y[:i*args.batch_size])

            print('Iter %d, Last X [%s] || fX:  %.4f || X_best: %s || fX_best: %.4f'
                  % (i, 
                     ''.join(['%.4f '%xx for xx in x_next.flatten()]),
                     float(Y[-1]),
                     ''.join([str(int(i)) for i in optim.casmopolitan.X[:i * args.batch_size][argmin].flatten()]),
                     Y[:i*args.batch_size][argmin]))

    if args.seed is not None:
        args.seed += 1


if __name__ == '__main__':
    from VISUALIZE.mcom import mcom
    mcv = mcom(
        path = './Temp',
        rapid_flush = True,
        draw_mode = 'Img',
        image_path = 'temp.jpg',
        tag = 'BO'
    )
    mcv.rec_init(color='g')

    for t in range(args.n_trials):
        main(t, mcv)