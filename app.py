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
import hmac
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta

import requests
import yaml
from flask import Flask, request, abort

app = Flask(__name__)

TAGS = ['dev-latest', 'release-latest', 'hotfix-release']

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


@dataclass
class Image:
    name: str
    full_name: str
    tag: str
    resource_url: str
    occur_at: str

    def send_hook(self, hook_url, token=''):
        if token:
            hook_url += f'?token={token}'
        resp = requests.post(hook_url, json=asdict(self))
        pretty_print(resp.content)

    def handle_image(self):
        pretty_print(str(self))
        hook = RULES.get('deploy_hook')
        rule = RULES.get(self.full_name)
        if not hook:
            pretty_print('No deploy hook url.')
            abort(500)
        if not rule:
            pretty_print('No image rule')
            abort(500)
        if self.tag not in TAGS:
            pretty_print('Do not need proxy hook..')
            return

        self.send_hook(hook, rule.get('token', ''))


@app.route('/')
def hello():
    return 'Hello, hook!'


@app.route('/deploy-hook', methods=['POST'])
def deploy():
    data = request.json
    if data['type'] != 'pushImage':
        pretty_print('Not push image, direct return')
        return 'ok'

    event_data = data['event_data']
    repo = event_data['repository']
    resources = event_data['resources']
    if not resources:
        pretty_print('Has not resources.')
        abort(400)

    resource = resources[0]
    image = Image(name=repo['name'], full_name=repo['repo_full_name'], resource_url=resource['resource_url'],
                  tag=resource['tag'], occur_at=format_timestamp(data['occur_at']))

    image.handle_image()
    return 'ok'


def github_auth_check():
    github_secret = RULES.get('github_secret')
    if not github_secret:
        pretty_print('No github secret.')
        abort(500)
    # Only SHA1 is supported
    header_signature = request.headers.get('X-Hub-Signature')
    if header_signature is None:
        pretty_print('No signature header.')
        abort(403)
    sha_name, signature = header_signature.split('=')
    if sha_name != 'sha1':
        abort(501)

    mac = hmac.new(github_secret.encode(), msg=request.data, digestmod='sha1')
    if str(mac.hexdigest()) != signature:
        pretty_print('Signature not match.')
        print(mac.hexdigest(), signature)
        abort(403)


@app.route('/build-hook', methods=['POST'])
def build():
    hook = RULES.get('build_hook')
    if not hook:
        pretty_print('No build hook url.')
        abort(500)

    token = request.args.get('token')
    if not token:
        pretty_print('No project token.')
        abort(400)

    github_auth_check()

    url = hook + f'?token={token}'
    resp = requests.post(url, json=request.json)
    pretty_print(resp.content)
    return 'ok'


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True)
