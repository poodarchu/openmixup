# Copyright (c) OpenMMLab. All rights reserved.
import logging
import torch
import torch.nn as nn
from mmcv.cnn.utils.weight_init import constant_init
from mmcv.runner import load_checkpoint

from ..builder import BACKBONES
from ..utils import trunc_normal_init, trunc_normal_
from .vision_transformer import VisionTransformer


@BACKBONES.register_module()
class DistilledVisionTransformer(VisionTransformer):
    """Distilled Vision Transformer.

    A PyTorch implement of : `Training data-efficient image transformers &
    distillation through attention <https://arxiv.org/abs/2012.12877>`_

    Args:
        arch (str | dict): Vision Transformer architecture
            Default: 'b'
        img_size (int | tuple): Input image size
        patch_size (int | tuple): The patch size
        out_indices (Sequence | int): Output from which stages.
            Defaults to -1, means the last stage.
        drop_rate (float): Probability of an element to be zeroed.
            Defaults to 0.
        drop_path_rate (float): stochastic depth rate. Defaults to 0.
        norm_cfg (dict): Config dict for normalization layer.
            Defaults to ``dict(type='LN')``.
        final_norm (bool): Whether to add a additional layer to normalize
            final feature map. Defaults to True.
        output_cls_token (bool): Whether output the cls_token. If set True,
            `with_cls_token` must be True. Defaults to True.
        interpolate_mode (str): Select the interpolate mode for position
            embeding vector resize. Defaults to "bicubic".
        patch_cfg (dict): Configs of patch embeding. Defaults to an empty dict.
        layer_cfgs (Sequence | dict): Configs of each transformer layer in
            encoder. Defaults to an empty dict.
        init_cfg (dict, optional): Initialization config dict (removed!).
            Defaults to None.
    """
    num_extra_tokens = 2  # cls_token, dist_token

    def __init__(self, *args, **kwargs):
        super(DistilledVisionTransformer, self).__init__(*args, **kwargs)
        self.dist_token = nn.Parameter(torch.zeros(1, 1, self.embed_dims))

    def init_weights(self, pretrained=None):
        if isinstance(pretrained, str):
            logger = logging.getLogger()
            load_checkpoint(self, pretrained, strict=False, logger=logger)
        elif pretrained is None:
            for m in self.modules():
                if isinstance(m, (nn.Conv2d, nn.Linear)):
                    trunc_normal_init(m, mean=0., std=0.02, bias=0)
                elif isinstance(m, (
                    nn.LayerNorm, nn.BatchNorm2d, nn.GroupNorm, nn.SyncBatchNorm)):
                    constant_init(m, val=1, bias=0)
            # ViT pos_embed & cls_token
            trunc_normal_(self.pos_embed, mean=0., std=0.02, bias=0, a=-2., b=2.)
            trunc_normal_(self.cls_token, mean=0., std=0.02, bias=0, a=-2., b=2.)
            # DeiT dist_token
            trunc_normal_(self.dist_token, mean=0., std=0.02, bias=0, a=-2., b=2.)
        else:
            raise TypeError('pretrained must be a str or None')
    
    def forward(self, x):
        B = x.shape[0]
        x = self.patch_embed(x)
        patch_resolution = self.patch_embed.patches_resolution

        # stole cls_tokens impl from Phil Wang, thanks
        cls_tokens = self.cls_token.expand(B, -1, -1)
        dist_token = self.dist_token.expand(B, -1, -1)
        x = torch.cat((cls_tokens, dist_token, x), dim=1)
        x = x + self.pos_embed
        x = self.drop_after_pos(x)

        outs = []
        for i, layer in enumerate(self.layers):
            x = layer(x)

            if i == len(self.layers) - 1 and self.final_norm:
                x = self.norm1(x)

            if i in self.out_indices:
                B, _, C = x.shape
                patch_token = x[:, 2:].reshape(B, *patch_resolution, C)
                patch_token = patch_token.permute(0, 3, 1, 2)
                cls_token = x[:, 0]
                dist_token = x[:, 1]
                if self.output_cls_token:
                    out = [patch_token, cls_token, dist_token]
                else:
                    out = patch_token
                outs.append(out)

        return outs