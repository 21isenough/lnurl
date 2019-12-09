import math

from hashlib import sha256
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from typing_extensions import Literal

from .exceptions import LnurlResponseException
from .types import HttpsUrl, LightningInvoice, LightningNodeUri, LnurlPayMetadata, MilliSatoshi


class LnurlPayRoute(BaseModel):
    pass


class LnurlPaySuccessAction(BaseModel):
    pass


class LnurlResponseModel(BaseModel):

    class Config:
        allow_population_by_field_name = True

    def dict(self, **kwargs):
        kwargs.setdefault('by_alias', True)
        return super().dict(**kwargs)

    def json(self, **kwargs):
        kwargs.setdefault('by_alias', True)
        return super().json(**kwargs)

    @property
    def ok(self) -> bool:
        return not ('status' in self.__fields__ and self.status == 'ERROR')


class LnurlErrorResponse(LnurlResponseModel):
    status: Literal['ERROR'] = 'ERROR'
    reason: str

    @property
    def error_msg(self) -> str:
        return self.reason


class LnurlSuccessResponse(LnurlResponseModel):
    status: Literal['OK'] = 'OK'


class LnurlAuthResponse(LnurlResponseModel):
    tag: Literal['login'] = 'login'
    callback: HttpsUrl
    k1: str


class LnurlChannelResponse(LnurlResponseModel):
    tag: Literal['channelRequest'] = 'channelRequest'
    uri: LightningNodeUri
    callback: HttpsUrl
    k1: str


class LnurlHostedChannelResponse(LnurlResponseModel):
    tag: Literal['hostedChannelRequest'] = 'hostedChannelRequest'
    uri: LightningNodeUri
    k1: str
    alias: Optional[str]


class LnurlPayResponse(LnurlResponseModel):
    tag: Literal['payRequest'] = 'payRequest'
    callback: HttpsUrl
    min_sendable: MilliSatoshi = Field(..., alias='minSendable')
    max_sendable: MilliSatoshi = Field(..., alias='maxSendable')
    metadata: LnurlPayMetadata

    @validator('max_sendable')
    def max_less_than_min(cls, value, values, **kwargs):
        if 'min_sendable' in values and value < values['min_sendable']:
            raise ValueError('`max_sendable` cannot be less than `min_sendable`.')
        return value

    @property
    def h(self) -> str:
        return sha256(self.metadata.encode('utf-8')).hexdigest()

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_sendable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_sendable / 1000))


class LnurlPayActionResponse(LnurlResponseModel):
    pr: LightningInvoice
    success_action: Optional[LnurlPaySuccessAction] = Field(None, alias='successAction')
    routes: List[LnurlPayRoute] = []


class LnurlWithdrawResponse(LnurlResponseModel):
    tag: Literal['withdrawRequest'] = 'withdrawRequest'
    callback: HttpsUrl
    k1: str
    min_withdrawable: MilliSatoshi = Field(..., alias='minWithdrawable')
    max_withdrawable: MilliSatoshi = Field(..., alias='maxWithdrawable')
    default_description: str = Field('', alias='defaultDescription')

    @validator('max_withdrawable')
    def max_less_than_min(cls, value, values, **kwargs):
        if 'min_withdrawable' in values and value < values['min_withdrawable']:
            raise ValueError('`max_withdrawable` cannot be less than `min_withdrawable`.')
        return value

    @property
    def min_sats(self) -> int:
        return int(math.ceil(self.min_withdrawable / 1000))

    @property
    def max_sats(self) -> int:
        return int(math.floor(self.max_withdrawable / 1000))


class LnurlResponse:

    @staticmethod
    def from_dict(d: dict) -> LnurlResponseModel:
        try:
            if 'status' in d and d['status'].upper() == 'ERROR':
                d['status'] = d['status'].upper()  # some services return `status` in lowercase, but spec says upper
                return LnurlErrorResponse(**d)

            elif 'tag' in d:
                d.pop('status', None)  # some services return `status` here, but it is not in the spec
                return {
                    'channelRequest': LnurlChannelResponse,
                    'hostedChannelRequest': LnurlHostedChannelResponse,
                    'payRequest': LnurlPayResponse,
                    'withdrawRequest': LnurlWithdrawResponse,
                }[d['tag']](**d)

            elif 'success_action' in d:
                return LnurlPayActionResponse(**d)

            else:
                return LnurlSuccessResponse(**d)

        except Exception:
            raise LnurlResponseException