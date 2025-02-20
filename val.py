r"""
For validating model.
Consist of some Valers.
"""

from metaclass.metavaler import MetaValDetect

__all__ = ['ValDetect']


class ValDetect(MetaValDetect):
    def __init__(self, args=None,
                 last=True, model=None, writer=None,
                 half=True, dataloader=None, loss_fn=None, cls_names=None, epoch=None, visual_image=None,
                 coco_eval=None):
        super(ValDetect, self).__init__(last, model, writer, half, dataloader,
                                        loss_fn, cls_names, epoch, visual_image, coco_eval)


if __name__ == '__main__':
    pass
