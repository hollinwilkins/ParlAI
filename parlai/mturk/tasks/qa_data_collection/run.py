# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
from parlai.core.params import ParlaiParser
from parlai.mturk.tasks.qa_data_collection.worlds import QADataCollectionWorld
from parlai.mturk.core.agents import MTurkAgent, MTurkManager
from task_config import task_config
import time
import os
import importlib
import copy
from itertools import product
try:
    from joblib import Parallel, delayed
except ModuleNotFoundError:
    raise SystemExit("Please install joblib by running: pip install joblib")

def main():
    argparser = ParlaiParser(False, False)
    argparser.add_parlai_data_path()
    argparser.add_mturk_args()
    opt = argparser.parse_args()
    opt['task'] = os.path.basename(os.getcwd())
    opt.update(task_config)

    # Initialize a SQuAD teacher agent, which we will get context from
    module_name = 'parlai.tasks.squad.agents'
    class_name = 'DefaultTeacher'
    my_module = importlib.import_module(module_name)
    task_class = getattr(my_module, class_name)
    task_opt = {}
    task_opt['datatype'] = 'train'
    task_opt['datapath'] = opt['datapath']

    mturk_manager = MTurkManager()
    mturk_manager.init_aws(opt=opt)

    mturk_agent_id = 'Worker'
    mturk_manager.mturk_agent_ids = [mturk_agent_id]
    mturk_manager.all_agent_ids = [QADataCollectionWorld.collector_agent_id, mturk_agent_id] # In speaking order

    global run_hit
    def run_hit(hit_index, assignment_index, task_class, task_opt, opt, mturk_manager):
        conversation_id = str(hit_index) + '_' + str(assignment_index)

        task = task_class(task_opt)
        # Create the MTurk agent which provides a chat interface to the Turker
        mturk_agent = MTurkAgent(id=mturk_agent_id, manager=mturk_manager, conversation_id=conversation_id, opt=opt)
        world = QADataCollectionWorld(opt=opt, task=task, mturk_agent=mturk_agent)
        while not world.episode_done():
            world.parley()
        world.shutdown()

    mturk_manager.create_hits(opt=opt)
    results = Parallel(n_jobs=opt['num_hits'] * opt['num_assignments'], backend='threading') \
                (delayed(run_hit)(hit_index, assignment_index, task_class, task_opt, opt, mturk_manager) \
                    for hit_index, assignment_index in product(range(1, opt['num_hits']+1), range(1, opt['num_assignments']+1)))    
    mturk_manager.review_hits()
    mturk_manager.shutdown()

if __name__ == '__main__':
    main()
