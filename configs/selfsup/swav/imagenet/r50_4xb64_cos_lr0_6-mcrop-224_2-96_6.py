_base_ = '../../_base_/datasets/imagenet/swav_mcrop-2-6_sz224_96_bs32.py'

# model settings
model = dict(
    type='SwAV',
    backbone=dict(
        type='ResNet_mmcls',
        depth=50,
        num_stages=4,
        out_indices=(3,),  # no conv-1, x-1: stage-x
        norm_cfg=dict(type='SyncBN'),
        style='pytorch'),
    neck=dict(
        type='SwAVNeck',
        in_channels=2048, hid_channels=2048, out_channels=128,
        with_avg_pool=True),
    head=dict(
        type='SwAVHead',
        feat_dim=128,  # equal to neck['out_channels']
        epsilon=0.05,
        temperature=0.1,
        num_crops=[2, 6],)
)

# interval for accumulate gradient
update_interval = 1  # total: 4 x bs64 x 1 accumulates = bs256

# additional hooks
custom_hooks = [
    dict(type='SwAVHook',
        priority='VERY_HIGH',
        batch_size=64,
        epoch_queue_starts=15,
        crops_for_assign=[0, 1],
        feat_dim=128,
        queue_length=3840)
]

# optimizer
optimizer = dict(
    type='LARS',
    lr=0.6,  # lr=0.6 / bs256
    momentum=0.9, weight_decay=1e-6,
    paramwise_options={
        '(bn|ln|gn)(\d+)?.(weight|bias)': dict(weight_decay=0., lars_exclude=True),
        'bias': dict(weight_decay=0., lars_exclude=True),
    })

# apex
use_fp16 = False
fp16 = dict(type='apex', loss_scale=dict(init_scale=512., mode='dynamic'))
# optimizer args
optimizer_config = dict(
    update_interval=update_interval, use_fp16=use_fp16, grad_clip=None,
    cancel_grad=dict(prototypes=5004),  # cancel grad of `prototypes` for 1 epoch
)

# lr scheduler
lr_config = dict(
    policy='CosineAnnealing',
    by_epoch=False, min_lr=6e-4,
)

# runtime settings
runner = dict(type='EpochBasedRunner', max_epochs=200)
