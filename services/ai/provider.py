"""Qualified Alice adapter. No tariff/quota logic and no automatic fallback."""
from __future__ import annotations
import json, subprocess, sys, os
from pathlib import Path
from domain.ai import PROVIDER, ProviderCall, ProviderResponse, ProviderError
from services.ai.settings import AISettings

WORKER=Path(__file__).with_name('_http_worker.py')

class DeadlineTransport:
    def __call__(self,payload:dict,timeout:float)->dict:
        if os.environ.get('APP_ENV') == 'test':
            raise ProviderError('configuration',unknown=False)
        encoded=json.dumps(payload,ensure_ascii=True).encode('utf-8')
        if len(encoded)>131072:raise ProviderError('invalid_request',unknown=False)
        process=subprocess.Popen([sys.executable,str(WORKER)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL,close_fds=True)
        try:
            output,_=process.communicate(encoded,timeout=max(.001,timeout))
        except subprocess.TimeoutExpired:
            process.kill();process.communicate()
            raise ProviderError('timeout_unknown',unknown=True) from None
        except BaseException:
            process.kill();process.communicate();raise
        if process.returncode!=0 or len(output)>2_000_000:
            raise ProviderError('transport_unknown')
        try:
            result=json.loads(output)
            if not isinstance(result,dict):raise ValueError
            return result
        except (ValueError,TypeError):raise ProviderError('invalid_envelope') from None

class YandexAliceProvider:
    provider_id=PROVIDER
    def __init__(self,settings:AISettings,*,transport=None):
        self.settings=settings;self.transport=transport or DeadlineTransport()

    def generate(self,call:ProviderCall)->ProviderResponse:
        # Service handles legal/environment/admission. Recheck transport's credential boundary.
        s=self.settings
        if not s.api_key or not s.folder_id or s.model_uri!=f'gpt://{s.folder_id}/aliceai-llm/latest':
            raise ProviderError('configuration',unknown=False)
        payload={'headers':{'Authorization':f'Api-Key {s.api_key}', 'Content-Type':'application/json',
                   'OpenAI-Project':s.folder_id,'x-folder-id':s.folder_id,
                   'x-data-logging-enabled':'false','x-client-request-id':call.request_id},
                 'body':{'model':s.model_uri,'messages':call.messages,'temperature':0,
                         'max_tokens':call.max_output_tokens,'stream':False,
                         'response_format':{'type':'json_schema','json_schema':{'name':call.task,'schema':call.schema,'strict':True}}},
                 'timeout':call.timeout_seconds}
        try:result=self.transport(payload,call.timeout_seconds)
        except ProviderError:raise
        except Exception:raise ProviderError('transport_unknown') from None
        if result.get('ok') is not True:
            raise ProviderError(result.get('code','transport_unknown'),retryable=result.get('retryable') is True,unknown=result.get('unknown',True) is not False)
        try:
            envelope=result['envelope'];usage=envelope.get('usage',{})
            def token(name):
                value=usage.get(name)
                return value if type(value)is int and 0<=value<=1_000_000 else None
            choices=envelope['choices']
            if not isinstance(choices,list) or len(choices)!=1:raise ValueError
            choice=choices[0];message=choice['message']
            content=message.get('content');finish=choice.get('finish_reason','')
            if message.get('refusal'):
                # Preserve known token counts even if the model refused.
                content='';finish='refusal'
            if not isinstance(content,str):content=''
            return ProviderResponse(content,token('prompt_tokens'),token('completion_tokens'),str(finish))
        except (TypeError,ValueError,KeyError,IndexError,AttributeError):
            raise ProviderError('invalid_envelope') from None
