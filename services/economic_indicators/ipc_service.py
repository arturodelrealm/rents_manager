from datetime import date
from typing import List

import requests
from django.conf import settings
from pydantic import BaseModel, field_validator


class IPCValue(BaseModel):
    date: date
    value: float

    @field_validator('value', mode='before')
    @classmethod
    def parse_decimal(cls, v):
        if isinstance(v, str):
            v = v.replace(',', '.')
        return float(v)


class IPCService:
    API_URL = 'https://api.cmfchile.cl/api-sbifv3/recursos_api/ipc/periodo/' \
        '{from_year}/{from_month}/{to_year}/{to_month}' \
        '?apikey={api_key}&formato=json'

    @classmethod
    def get_ipc_data(cls, from_date: date, to_date: date) -> List[IPCValue]:
        """Get the ipc values of all the months between the 2 given dates
        (both included)."""
        url = cls.API_URL.format(
            from_year=from_date.year,
            from_month=from_date.month,
            to_year=to_date.year,
            to_month=to_date.month,
            api_key=settings.CMF_APIKEY,
        )
        response = requests.get(url)
        response.raise_for_status()
        ipc_values = response.json()['IPCs']
        return [
            IPCValue(date=ipc['Fecha'], value=ipc['Valor'])
            for ipc in ipc_values
        ]

