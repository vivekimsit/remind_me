# -*- coding: utf-8 -*- 
import os
import json
import redis
import random

from werkzeug.routing import Map, Rule
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import HTTPException, NotFound

from jinja2 import Environment, FileSystemLoader


class RemindMe(object):
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis = redis.Redis(redis_host, redis_port)
        self.url_map = Map([
        Rule('/', endpoint='home'),
        Rule('/msg', endpoint='set_message'),
        Rule('/msgs', endpoint='get_message')
        ])
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_environ = Environment(
                loader=FileSystemLoader(template_path),
                autoescape=True
            )

    def render_template(self, template_name, **context):
        template = self.jinja_environ.get_template(template_name)
        return Response(template.render(context), mimetype="text/html")

    def get_message(self):
        res = {'title': 'Empty', 'msg': 'Empty'}
        titles = self.redis.smembers('titles')
        if not titles:
            return res
        titles = list(titles)
        title = random.sample(titles,1).pop()
        res['title'] = title
        # Get all the messages for this title
        msgs = self.redis.lrange("msgs:%s"%title, 0, -1)
        if not msgs:
            return res
        msg = random.sample(msgs, 1).pop()
        res['msg'] = msg
        return res

    def on_get_message(self, request):
        res = self.get_message()
        res = json.dumps(res)
        print res
        return Response(res)

    def set_message(self, title, msg):
        # Check if title already exists
        if not self.redis.sismember('titles', title):
            # If not then set the title
            self.redis.sadd('titles', title)
        # now enter the message
        self.redis.rpush('msg:%s'%title, msg)

    def on_set_message(self, title, msg):
        self.set_message(title, msg)
        return redirect('/')

    def on_home(self, request, **vals):
        #res = self.get_message()
        return self.render_template('home.html')

    def dispatch(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, vals = adapter.match()
            return getattr(self, 'on_' + endpoint)(request, **vals)
        except NotFound, e:
            return e
        except HTTPException, he:
            return he

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch(request)
        return response(environ, start_response)

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = RemindMe()
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
