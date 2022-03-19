_base_ = '../../../../../_base_/datasets/cifar100/sz32_bs100.py'

# model settings
model = dict(
    type='MixUpClassification',
    pretrained=None,
    pretrained_k="work_dirs/my_pretrains/official/resnet18_pytorch.pth",
    alpha=2,
    mix_mode="attentivemix",
    mix_args=dict(
        attentivemix=dict(grid_size=32, top_k=None, beta=8),  # AttentiveMix+ in this repo (use pre-trained)
        automix=dict(mask_adjust=0, lam_margin=0),  # require pre-trained mixblock
        fmix=dict(decay_power=3, size=(32,32), max_soft=0., reformulate=False),
        manifoldmix=dict(layer=(0, 3)),
        puzzlemix=dict(transport=True, t_batch_size=None, t_size=4,  # t_size for small-scale datasets
            block_num=5, beta=1.2, gamma=0.5, eta=0.2, neigh_size=4, n_labels=3, t_eps=0.8),
        resizemix=dict(scope=(0.1, 0.8), use_alpha=True),
        samix=dict(mask_adjust=0, lam_margin=0.08),  # require pre-trained mixblock
    ),
    backbone=dict(
        type='ResNet_CIFAR',  # CIFAR version
        depth=18,
        num_stages=4,
        out_indices=(3,),  # no conv-1, x-1: stage-x
        style='pytorch'),
    backbone_k=dict(  # PyTorch pre-trained R-18 is required for attentivemix+
        type='ResNet_mmcls',
        depth=18,
        num_stages=4,
        out_indices=(3,),
        style='pytorch'),
    head=dict(
        type='ClsHead',  # normal CE loss
        loss=dict(type='CrossEntropyLoss', loss_weight=1.0),
        with_avg_pool=True, multi_label=False, in_channels=512, num_classes=100)
)

# additional hooks
custom_hooks = [
    dict(type='SAVEHook',
        iter_per_epoch=500,
        save_interval=12500),  # plot every 500 x 25 ep
]

# optimizer
optimizer = dict(type='SGD', lr=0.1, momentum=0.9, weight_decay=0.0001)
optimizer_config = dict(grad_clip=None)

# learning policy
lr_config = dict(policy='CosineAnnealing', min_lr=0.)

# runtime settings
runner = dict(type='EpochBasedRunner', max_epochs=800)