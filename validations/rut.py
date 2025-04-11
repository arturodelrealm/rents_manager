from itertools import cycle

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class RutValidator:
    @staticmethod
    def get_verification_code(rut: str) -> str:
        """Return the verification code of one rut"""
        rut = rut.replace('.', '')
        if not rut.isnumeric():
            raise ValidationError(_('El rut contiene caracteres no numéricos'))
        if len(rut) > 8:
            raise ValidationError(_(
                'El rut no puede tener más de 8 dígitos (sin el código '
                'verificador).')
            )
        verification_code = 11 - (sum(
            rut_digit * mult for rut_digit, mult in zip(
                map(int, reversed(rut)),
                cycle(range(2, 8))
            )
        ) % 11)
        if verification_code == 11:
            return '0'
        if verification_code == 10:
            return 'K'
        return str(verification_code)

    @classmethod
    def validate_rut(cls, rut: str) -> bool:
        rut_body, __, verification_code = rut.partition('-')
        verification_code = verification_code.upper()
        return cls.get_verification_code(rut_body) == verification_code

    @staticmethod
    def clean_rut(rut: str) -> str:
        return rut.replace('.', '').upper()

    @classmethod
    def validator(cls, rut: str) -> str:
        if not rut:
            return ''
        rut = cls.clean_rut(rut)
        if not cls.validate_rut(rut):
            raise ValidationError(
                _('Código verificador incorrecto.')
            )
        return rut
