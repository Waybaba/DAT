import pyrootutils
root = pyrootutils.setup_root(__file__, dotenv=True, pythonpath=True, indicator=[".env"])
import argparse
import os

import mmcv
import torch
from mmcv.parallel import MMDataParallel, MMDistributedDataParallel
from mmcv.runner import get_dist_info, init_dist, load_checkpoint
from mmcv.utils import DictAction
from copy import deepcopy

from mmseg.apis import multi_gpu_test, single_gpu_test, single_gpu_our
from mmseg.datasets import build_dataloader, build_dataset
from mmseg.models import build_segmentor
from IPython import embed


def create_ema_model(model):
    ema_model = deepcopy(model)#get_model(args.model)(num_classes=num_classes)

    for param in ema_model.parameters():
        param.detach_()
    mp = list(model.parameters())
    mcp = list(ema_model.parameters())
    n = len(mp)
    for i in range(0, n):
        mcp[i].data[:] = mp[i].data[:].clone()
    #_, availble_gpus = self._get_available_devices(self.config['n_gpu'])
    #ema_model = torch.nn.DataParallel(ema_model, device_ids=availble_gpus)
    return ema_model

def update_ema_variables(ema_model, model, alpha_teacher, iteration=None):
    # Use the "true" average until the exponential average is more correct
    if iteration:
        alpha_teacher = min(1 - 1 / (iteration + 1), alpha_teacher)

    if True:
        for ema_param, param in zip(ema_model.parameters(), model.parameters()):
            #ema_param.data.mul_(alpha).add_(1 - alpha, param.data)
            ema_param.data[:] = alpha_teacher * ema_param[:].data[:] + (1 - alpha_teacher) * param[:].data[:]
    return ema_model


def parse_args():
    parser = argparse.ArgumentParser(
        description='mmseg test (and eval) a model')
    parser.add_argument('config', help='test config file path')
    parser.add_argument('checkpoint', help='checkpoint file')
    parser.add_argument(
        '--aug-test', action='store_true', help='Use Flip and Multi scale aug')
    parser.add_argument('--out', default='work_dirs/res.pkl', help='output result file in pickle format')
    parser.add_argument(
        '--format-only',
        action='store_true',
        help='Format the output results without perform evaluation. It is'
        'useful when you want to format the result to a specific format and '
        'submit it to the test server')
    parser.add_argument(
        '--eval',
        type=str,
        nargs='+',
        default='mIoU',
        help='evaluation metrics, which depends on the dataset, e.g., "mIoU"'
        ' for generic datasets, and "cityscapes" for Cityscapes')
    parser.add_argument('--show', action='store_true', help='show results')
    parser.add_argument(
        '--show-dir', help='directory where painted images will be saved')
    parser.add_argument(
        '--gpu-collect',
        action='store_true',
        help='whether to use gpu to collect results.')
    parser.add_argument(
        '--tmpdir',
        help='tmp directory used for collecting results from multiple '
        'workers, available when gpu_collect is not specified')
    parser.add_argument(
        '--options', nargs='+', action=DictAction, help='custom options')
    parser.add_argument(
        '--eval-options',
        nargs='+',
        action=DictAction,
        help='custom options for evaluation')
    parser.add_argument(
        '--launcher',
        choices=['none', 'pytorch', 'slurm', 'mpi'],
        default='none',
        help='job launcher')
    parser.add_argument('--local_rank', type=int, default=0)
    args = parser.parse_args()
    if 'LOCAL_RANK' not in os.environ:
        os.environ['LOCAL_RANK'] = str(args.local_rank)
    return args


def main():
    args = parse_args()

    assert args.out or args.eval or args.format_only or args.show \
        or args.show_dir, \
        ('Please specify at least one operation (save/eval/format/show the '
         'results / save the results) with the argument "--out", "--eval"'
         ', "--format-only", "--show" or "--show-dir"')

    if 'None' in args.eval:
        args.eval = None
    if args.eval and args.format_only:

        raise ValueError('--eval and --format_only cannot be both specified')

    if args.out is not None and not args.out.endswith(('.pkl', '.pickle')):
        raise ValueError('The output file must be a pkl file.')

    cfg = mmcv.Config.fromfile(args.config)
    if args.options is not None:
        cfg.merge_from_dict(args.options)
    # set cudnn_benchmark
    if cfg.get('cudnn_benchmark', False):
        torch.backends.cudnn.benchmark = True
    if True:#True: #args.aug_test:
        if cfg.data.test.type in ['CityscapesDataset', 'ACDCDataset']:
            # hard code index
            cfg.data.test.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
            ]
            cfg.data.test.pipeline[1].flip = True
        elif cfg.data.test.type == 'ADE20KDataset':
            # hard code index
            cfg.data.test.pipeline[1].img_ratios = [
                0.75, 0.875, 1.0, 1.125, 1.25
            ]
            cfg.data.test.pipeline[1].flip = True
        else:
            # hard code index
            cfg.data.test.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75
            ]
            cfg.data.test.pipeline[1].flip = True
        if cfg.data.test1.type in ['CityscapesDataset', 'ACDCDataset']:
            # hard code index
            cfg.data.test1.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
            ]
            cfg.data.test1.pipeline[1].flip = True
        elif cfg.data.test1.type == 'ADE20KDataset':
            # hard code index
            cfg.data.test1.pipeline[1].img_ratios = [
                0.75, 0.875, 1.0, 1.125, 1.25
            ]
            cfg.data.test1.pipeline[1].flip = True
        else:
            # hard code index
            cfg.data.test1.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75
            ]
            cfg.data.test1.pipeline[1].flip = True
        if cfg.data.test2.type in ['CityscapesDataset', 'ACDCDataset']:
            # hard code index
            cfg.data.test2.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
            ]
            cfg.data.test2.pipeline[1].flip = True
        elif cfg.data.test2.type == 'ADE20KDataset':
            # hard code index
            cfg.data.test2.pipeline[1].img_ratios = [
                0.75, 0.875, 1.0, 1.125, 1.25
            ]
            cfg.data.test2.pipeline[1].flip = True
        else:
            # hard code index
            cfg.data.test2.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75
            ]
            cfg.data.test2.pipeline[1].flip = True
        if cfg.data.test3.type in ['CityscapesDataset', 'ACDCDataset']:
            # hard code index
            cfg.data.test3.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0
            ]
            cfg.data.test3.pipeline[1].flip = True
        elif cfg.data.test.type == 'ADE20KDataset':
            # hard code index
            cfg.data.test3.pipeline[1].img_ratios = [
                0.75, 0.875, 1.0, 1.125, 1.25
            ]
            cfg.data.test3.pipeline[1].flip = True
        else:
            # hard code index
            cfg.data.test3.pipeline[1].img_ratios = [
                0.5, 0.75, 1.0, 1.25, 1.5, 1.75
            ]
            cfg.data.test3.pipeline[1].flip = True


    cfg.model.pretrained = None
    cfg.data.test.test_mode = True

    # init distributed env first, since logger depends on the dist info.
    if args.launcher == 'none':
        distributed = False
    else:
        distributed = True
        init_dist(args.launcher, **cfg.dist_params)

    # build the dataloader
    # TODO: support multiple images per gpu (only minor changes are needed)
    print(cfg)
    datasets = [build_dataset(cfg.data.test), build_dataset(cfg.data.test1), build_dataset(cfg.data.test2),build_dataset(cfg.data.test3)]
    #data_loaders = [build_dataloader(
    #    dataset,
    #    samples_per_gpu=1,
    #    workers_per_gpu=cfg.data.workers_per_gpu,
    #    dist=distributed,
    #    shuffle=False) for dataset in datasets]

    # build the model and load checkpoint
    cfg.model.train_cfg = None
    model = build_segmentor(cfg.model, test_cfg=cfg.get('test_cfg'))
    checkpoint = load_checkpoint(model, args.checkpoint, map_location='cpu')
    model.CLASSES = checkpoint['meta']['CLASSES']
    model.PALETTE = checkpoint['meta']['PALETTE']

    efficient_test = True #False
    if args.eval_options is not None:
        efficient_test = args.eval_options.get('efficient_test', False)

    model = MMDataParallel(model, device_ids=[0])
    anchor = deepcopy(model.state_dict())
    anchor_model = deepcopy(model)
    ema_model = create_ema_model(model)
    for i in range(10):
        print("revisiting", i)
        data_loaders = [build_dataloader(
            dataset,
            samples_per_gpu=1,
            workers_per_gpu=cfg.data.workers_per_gpu,
            dist=distributed,
            shuffle=False) for dataset in datasets]
        for dataset, data_loader in zip(datasets, data_loaders):
            outputs = single_gpu_our(model, data_loader, args.show, args.show_dir,
                                  efficient_test, anchor, ema_model, anchor_model)

            rank, _ = get_dist_info()
            if rank == 0:
                if args.out:
                    print(f'\nwriting results to {args.out}')
                    mmcv.dump(outputs, args.out)
                kwargs = {} if args.eval_options is None else args.eval_options
                if args.format_only:
                    dataset.format_results(outputs, **kwargs)
                if args.eval:
                    dataset.evaluate(outputs, args.eval, **kwargs)
        del data_loaders

if __name__ == '__main__':
    main()
