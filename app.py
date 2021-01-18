"""
Example harbor hook json data:

{'event_data': {'repository': {'date_created': 1573203500,
                               'name': 'alpine',
                               'namespace': 'library',
                               'repo_full_name': 'library/alpine',
                               'repo_type': 'public'},
                'resources': [{'digest': 'sha256:e4355b66995c96b4b468159fc5c7e3540fcef961189ca13fee877798649f531a',
                               'resource_url': 'library/alpine:latest',
                               'tag': 'latest'}]},
 'occur_at': 1573205735,
 'operator': 'admin',
 'type': 'pushImage'}

"""
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import List

import httpx
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Repository(BaseModel):
    date_created: int
    name: str
    namespace: str
    repo_full_name: str
    repo_type: str


class Resource(BaseModel):
    digest: str
    resource_url: str
    tag: str


class Event(BaseModel):
    repository: Repository
    resources: List[Resource]


class DeployRequest(BaseModel):
    event_data: Event
    occur_at: int
    operator: str
    type: str


TIME_ZONE = timezone(timedelta(hours=8), 'Asia/Shanghai')


def load_rules():
    filename = os.path.join(os.path.dirname(__file__), 'rules.yaml')
    with open(filename, 'r') as f:
        return yaml.load(f.read(), Loader=yaml.SafeLoader)


RULES = load_rules()


def pretty_print(s):
    print('*' * 20)
    print(s)
    print('*' * 20)


def format_timestamp(ts):
    dt = datetime.fromtimestamp(ts, tz=TIME_ZONE)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def raise_exeception(status, detail):
    pretty_print(detail)
    raise HTTPException(status, detail=detail)


@dataclass
class Image:
    name: str
    full_name: str
    tag: str
    resource_url: str
    occur_at: str

    def send_hook(self, hook_url, token=''):
        if token:
            headers = {'Authorization': token}
        resp = httpx.post(hook_url, json=asdict(self), headers=headers)
        pretty_print(resp.content)

    def handle_image(self):
        pretty_print(str(self))
        hooks = RULES.get('deploys')
        if not hooks:
            raise_exeception(500, 'No deploy hook url.')

        for hook in hooks:
            self.send_hook(hook['url'], hook.get('token', ''))


@app.get('/')
def hello():
    return 'Hello, hook!'


@app.post('/deploy')
def deploy(req: DeployRequest):
    print(req)
    if req.type != 'PUSH_ARTIFACT':
        pretty_print('Not push image, direct return')
        return 'ok'

    event_data = req.event_data
    repo = event_data.repository
    resources = event_data.resources
    if not resources:
        msg = 'Has not resources.'
        pretty_print(msg)
        raise HTTPException(400, detail=msg)

    resource = resources[0]
    image = Image(
        name=repo.name,
        full_name=repo.repo_full_name,
        resource_url=f'{repo.repo_full_name}:{resource.tag}',
        tag=resource.tag,
        occur_at=format_timestamp(req.occur_at),
    )

    image.handle_image()
    return 'ok'
