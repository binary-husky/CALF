import numpy as np
import commentjson as json
import logging, os
from functools import lru_cache
from THIRDPARTY.casmopolitan.bo_interface import BayesianOptimizationInterface
from UTIL.file_lock import FileLock
MasterAutoRLKey = 'auto_rl_3'
os.makedirs(f'AUTORL/{MasterAutoRLKey}', exist_ok=True)


class HmpBayesianOptimizationInterface(BayesianOptimizationInterface):

    def obtain_base_experiment(self):
        return """
{
    "config.py->GlobalConfig": {
        "note": "parallel-0",
        "env_name": "dca_multiteam",
        "env_path": "MISSION.dca_multiteam",
        "draw_mode": "Img",
        "num_threads": 32,
        "report_reward_interval": 32,
        "test_interval": 65536,
        "test_epoch": 256,
        "mt_parallel": true,
        "device": "cpu",
        "fold": 1,
        "n_parallel_frame": 50000000.0,
        "max_n_episode": 4096.0,
        "seed": 0,
        "mt_act_order": "new_method",
        "backup_files": [
            "ALGORITHM/experimental_conc_mt_fuzzy_agent_wise_3",
            "MISSION/dca_multiteam"
        ]
    },

    "MISSION.dca_multiteam.collective_assult_parallel_run.py->ScenarioConfig": {
        "N_TEAM": 2,
        "N_AGENT_EACH_TEAM": [20,20],
        "introduce_terrain": true,
        "terrain_parameters": [0.15,0.2],
        "size": "5",
        "random_jam_prob": 0.05,
        "MaxEpisodeStep": 150,
        "render": false,
        "RewardAsUnity": true,
        "half_death_reward": true,
        "TEAM_NAMES": [
            // "ALGORITHM.random.foundation->RandomController"
            "ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation->ReinforceAlgorithmFoundation",
            "TEMP.TEAM2.ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation->ReinforceAlgorithmFoundation",
        ]
    },

    "ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig": {
        "train_traj_needed": 32,
        "n_focus_on": 3,
        "lr": 0.0003,
        "ppo_epoch": 16,
        "lr_descent": false,
        "use_policy_resonance": false,
        "gamma": 0.99,
        "device_override": "cuda:6",
        "fuzzy_controller": true,
        "fuzzy_controller_param": [ 1,2,3,4,5,6,7,8,9 ],
        "fuzzy_controller_scale_param": [-99],
        "gpu_party_override": "cuda6_party0"
    },

    "TEMP.TEAM2.ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig": {
        "train_traj_needed": 32,
        "n_focus_on": 3,
        "lr": 0.0003,
        "ppo_epoch": 16,
        "lr_descent": false,
        "use_policy_resonance": false,
        "gamma": 0.99,
        "device_override": "cuda:0",
        "gpu_party_override": "cuda5_party0",
    },
}
"""




    def compute_(self, X, normalize=False):
        def get_score(conclusion_list):
            score_list = []
            for c in conclusion_list:
                conclusion_parsed = {}
                # parse
                for name, line, time in zip(c['name_list'],c['line_list'],c['time_list']):
                    conclusion_parsed[name] = line
                s = conclusion_parsed['acc win ratio of=team-0']
                score_list.append(s[-1])
            return score_list

        X = np.array(X)
        batch = X.shape[0]
        async_struct = {
            'X': X,
            'future': [None]*batch,
            'y_result_array': np.zeros(shape=(batch, 1))
        }
        
        self.clean_profile_folder()

        for b in range(batch):
            _, async_struct['future'][b] = self.prev_part(async_struct['X'][b], batch=b)

        for b in range(batch):
            async_struct['y_result_array'][b] = self.post_part(async_struct['X'][b], get_score, async_struct['future'][b], batch=b)

        return async_struct['y_result_array']

    def post_part(self, X, get_score, future_list, batch):
        from UTIL.batch_exp import fetch_experiment_conclusion
        conclusion_list = fetch_experiment_conclusion(
                step=self.internal_step_cnt,
                future_list=future_list,
                n_run_mode=self.n_run_mode_withbatch[batch])

        y_array = get_score(conclusion_list)
        y = np.array(y_array).mean()
        self.logger.info(f'input X={X} | output {y_array}, average {y}')
        res = (y - self.y_offset)
        if self.optimize_direction == 'maximize':
            res = -res
        else:
            assert self.optimize_direction == 'minimize'
        return res

    def prev_part(self, X, batch):
        conf_override = {"config.py->GlobalConfig-->seed": self.seed_list,"config.py->GlobalConfig-->note": self.note_list,}
        conf_override.update(self.get_device_conf(batch))

            # AutoRL::learn hyper parameter ---> fuzzy
        p0 = self.convert_categorical(from_x = X[0],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=0)
        p1 = self.convert_categorical(from_x = X[1],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=1)
        p2 = self.convert_categorical(from_x = X[2],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=2)
        p3 = self.convert_categorical(from_x = X[3],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=3)
        p4 = self.convert_categorical(from_x = X[4],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=4)
        p5 = self.convert_categorical(from_x = X[5],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=5)
        p6 = self.convert_categorical(from_x = X[6],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=6)
        p7 = self.convert_categorical(from_x = X[7],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=7)
        p8 = self.convert_categorical(from_x = X[8],  to_list=[0, 1, 2, 3, 4, 5, 6], p_index=8)

        self.logger.info(f'input X={X} | parsed {[p0,p1,p2,p3,p4,p5,p6,p7,p8]}')

        conf_override.update({
                "ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->fuzzy_controller_param": \
                    [[p0,p1,p2,p3,p4,p5,p6,p7,p8]] * self.n_run
            })

        self.internal_step_cnt += 1
        future_list = self.push_experiments_and_execute(conf_override, batch)
        return X, future_list


    def get_device_conf(self, batch):
        if batch==0:
            return {
                ########################################
                "ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->device_override":
                    [
                        "cuda:0",
                        "cuda:0",
                        "cuda:1",
                        "cuda:1",
                        "cuda:0",
                        "cuda:0",
                        "cuda:1",
                        "cuda:1",
                    ],
                "ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->gpu_party_override":
                    [
                        "#0",
                        "#0",
                        "#0",
                        "#0",
                        "#1",
                        "#1",
                        "#1",
                        "#1",
                    ],

                ########################################
                "TEMP.TEAM2.ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->device_override":
                    [
                        "cuda:0",
                        "cuda:0",
                        "cuda:1",
                        "cuda:1",
                        "cuda:0",
                        "cuda:0",
                        "cuda:1",
                        "cuda:1",
                    ],
                "TEMP.TEAM2.ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->gpu_party_override":
                    [
                        "#2",
                        "#2",
                        "#2",
                        "#2",
                        "#3",
                        "#3",
                        "#3",
                        "#3",
                    ],

            }
        elif batch==1:
            return {
                ########################################
                "ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->device_override":
                    [
                        "cuda:2",
                        "cuda:2",
                        "cuda:3",
                        "cuda:3",
                        "cuda:4",
                        "cuda:4",
                        "cuda:0",
                        "cuda:0",
                    ],
                "ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->gpu_party_override":
                    [
                        "#2", 
                        "#2",
                        "#2", 
                        "#2",
                        "#2", 
                        "#2",
                        "#2",
                        "#2",
                    ],

                ########################################
                "TEMP.TEAM2.ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->device_override":
                    [
                        "cuda:2",
                        "cuda:2",
                        "cuda:3",
                        "cuda:3",
                        "cuda:4",
                        "cuda:4",
                        "cuda:0",
                        "cuda:0",
                    ],
                "TEMP.TEAM2.ALGORITHM.experimental_conc_mt_fuzzy_agent_wise_3.foundation.py->AlgorithmConfig-->gpu_party_override":
                    [
                        "#3", 
                        "#3",
                        "#3", 
                        "#3",
                        "#3", 
                        "#3",
                        "#3",
                        "#3",
                    ],

            }
      

    def __init__(self, MasterAutoRLKey, normalize=False, seed=None):
        super().__init__(MasterAutoRLKey)
        self.problem_type = 'categorical' # 'categorical' # 'mixed'
        self.seed = seed if seed is not None else 0
        self.n_run = 8
        self.seed_list = [self.seed + i for i in range(self.n_run)]
        self.note_list = [f'parallel-{i}' for i in range(self.n_run)]
        self.n_run_mode_withbatch = [
            [
                {   
                    "addr": "210.75.240.143:2236",
                    "usr": "hmp",
                    "pwd": "hmp"
                },
            ]*self.n_run,
            [
                {   
                    "addr": "localhost:2266",
                    "usr": "hmp",
                    "pwd": "hmp"
                },
            ]*self.n_run,

        ]
        self.sum_note = "Bo_AutoRL"
        self.base_conf = json.loads(self.obtain_base_experiment())
        if self.base_conf["config.py->GlobalConfig"]["max_n_episode"] < 1000:
            input('conf_override["config.py->GlobalConfig-->max_n_episode"] < 1000, confirm?')
        self.internal_step_cnt = 0

        self.P_CategoricalDims = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8])
        self.P_NumCategoryList = np.array([7, 7, 7, 7, 7, 7, 7, 7, 7])

        # self.P_ContinuousDims       = np.array([10])
        # self.P_ContinuousLowerBound = np.array([-1] * len(self.P_ContinuousDims))
        # self.P_ContinuousUpperBound = np.array([+1] * len(self.P_ContinuousDims))

        self.normalize = False
        self.y_offset = 0
        self.optimize_direction = 'maximize' # 'minimize'

    def convert_categorical(self, from_x, to_list, p_index):
        assert p_index in self.P_CategoricalDims
        assert len(to_list) == self.P_NumCategoryList[p_index]
        from_x_ = int(from_x)
        assert from_x_-from_x == 0
        return to_list[from_x_]

    def convert_continuous(self, from_x, to_range, p_index):
        assert p_index in self.P_ContinuousDims
        where = np.where(self.P_ContinuousDims==p_index)[0]

        new_range = to_range[1] - to_range[0]
        xx = ((from_x - self.P_ContinuousLowerBound[where]) * new_range / (self.P_ContinuousUpperBound[where] - self.P_ContinuousLowerBound[where])) + to_range[0]

        return float(xx)

    def clean_profile_folder(self):
        import shutil, os
        if os.path.exists('PROFILE'):
            time_mark_only = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
            shutil.copytree('PROFILE', f'TEMP/PROFILE-{time_mark_only}')
            shutil.rmtree('PROFILE')


    def push_experiments_and_execute(self, conf_override, batch):
        # copy the experiments
        import shutil, os
        shutil.copyfile(__file__, os.path.join(os.path.dirname(__file__), 'batch_experiment_backup.py'))
        # run experiments remotely
        from UTIL.batch_exp import run_batch_exp, fetch_experiment_conclusion
        print('Execute in server:', self.n_run_mode_withbatch[batch][0])
        future = run_batch_exp(self.sum_note, self.n_run, self.n_run_mode_withbatch[batch], self.base_conf, conf_override, __file__, skip_confirm=True, master_folder='AutoRL', logger=self.logger)
        return future






















#####################################################################################################################

if __name__ == '__main__':

    # from THIRDPARTY.casmopolitan.mixed_test_func import *
    import logging, torch
    import argparse
    import time
    from THIRDPARTY.casmopolitan.test_funcs.random_seed_config import *
    from VISUALIZE.mcom import mcom
    from THIRDPARTY.casmopolitan.bo_interface import BayesianOptimisation

    # Set up the objective function
    parser = argparse.ArgumentParser('Run Experiments')
    parser.add_argument('--max_iters', type=int, default=300, help='Maximum number of BO iterations.')
    parser.add_argument('--lamda', type=float, default=1e-6, help='the noise to inject for some problems')
    parser.add_argument('--batch_size', type=int, default=1, help='batch size for BO.')
    parser.add_argument('--n_trials', type=int, default=20, help='number of trials for the experiment')
    parser.add_argument('--n_init', type=int, default=20, help='number of initialising random points')
    parser.add_argument('--save_path', type=str, default=f'AUTORL/{MasterAutoRLKey}/', help='save directory of the log files')
    # parser.add_argument('--ard', action='store_true', help='whether to enable automatic relevance determination')
    parser.add_argument('--ard', action='store_false', help='whether to enable automatic relevance determination')
    parser.add_argument('-a', '--acq', type=str, default='ei', help='choice of the acquisition function.')
    parser.add_argument('--random_seed_objective', type=int, default=20, help='The default value of 20 is provided also in COMBO')
    parser.add_argument('-d', '--debug', action='store_true', help='Whether to turn on debugging mode (a lot of output will be generated).')
    parser.add_argument('--no_save', action='store_true', help='If activated, do not save the current run into a log folder.')
    parser.add_argument('--seed', type=int, default=2023, help='**initial** seed setting')
    parser.add_argument('-k', '--kernel_type', type=str, default=None, help='specifies the kernel type')
    parser.add_argument('--infer_noise_var', action='store_true')
    parser.add_argument('--global_bo', action='store_true', help='whether to use global BO modelling only (disabling the local BO modelling)')

    args = parser.parse_args()
    options = vars(args)
    print(options)
    # Set numpy seed
    np.random.seed(args.seed)
    np.set_printoptions(3, suppress=True)
    torch.cuda.manual_seed(args.seed)


    if args.debug: logging.basicConfig(level=logging.INFO)
    # Sanity checks
    assert args.acq in ['ucb', 'ei', 'thompson'], 'Unknown acquisition function choice ' + str(args.acq)
    mcv = mcom(path = f'AUTORL/{MasterAutoRLKey}/', rapid_flush = True, draw_mode = 'Img', image_path = f'AUTORL/{MasterAutoRLKey}/decend.jpg', tag = 'BayesianOptimisation')
    mcv.rec_init(color='g')
    BayesianOptimisation(0, mcv, args, MasterAutoRLKey=MasterAutoRLKey, HmpBayesianOptimizationInterface=HmpBayesianOptimizationInterface)

