from django.utils.translation import gettext_lazy as _
from django.db import models

from .contract import Contract


class Comment(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Contrato')
    )
    text = models.CharField(verbose_name=_('Texto'), max_length=500)
    created_at = models.DateTimeField(
        verbose_name=_('Creado a'),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _('Comentario')
        verbose_name_plural = _('Comentarios')
