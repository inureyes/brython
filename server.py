import os
import sys
import json
import html
import datetime
from time import perf_counter as timer

from aiohttp import web


root = os.path.join(os.getcwd(), 'www')

async def handle_ajax_get(request):
    return web.Response(text=str(dict(request.rel_url.query)))

async def handle_ajax_post(request):
    text = await request.text()
    return web.Response(text=text)

async def handle_time_cpython(request):
    content = await request.read()
    data = json.loads(content.decode('utf-8'))
    script = data['script']
    with open(os.path.join(root, 'speed', *script.split('/')),
              encoding="utf-8") as f:
        src = f.read()

    t0 = timer()
    exec(src)
    dt = timer() - t0
    return web.Response(text=str(dt))

async def store_speed(request):
    assert request.remote == '::1', request.remote
    cpython_version = ".".join(str(x) for x in sys.implementation.version[:3])
    infos = json.loads((await request.read()).decode('utf-8'))
    results = infos['results']
    data = [
        {"test": result["test"],
         "description": result["description"],
         "src": result["src"].replace("\r\n", "\n"),
         "ratio": round(100 * (result["Brython"] / result["CPython"]))
         }
        for result in results]

    json.dump(data, open("speed_results.json", "w", encoding="utf-8"),
        indent=4)

    with open("speed_results.txt", "w", encoding="utf-8") as out:
        for line in data:
            out.write(f'{line["description"]};{line["ratio"]}\n')

    template = """<!doctype html>
    <html>
    <head>
    <meta charset="utf-8">
    <title>Brython speed compared to CPython</title>
    <link rel="stylesheet" href="/brython.css">
    <style>
    body{
        padding-left: 2em;
    }
    td{
        vertical-align: top;
        padding: 3px;
    }
    td, th{
        border-style: solid;
        border-width: 0px 0px 1px 0px;
        border-color: #000;
    }
    pre{
        margin: 0px 0px 0px 5px;
    }
    </style>
    </head>
    <body>
    <h2>Brython {{version}} performance compared to CPython {{cpython_version}}</h2>
    User agent: {{userAgent}}
    <br>{{date}}
    <p>
    <table>
    <tr>
    <th>Test</th>
    <th>Brython<br>(100 = CPython)</th>
    <th>Code</th>
    </tr>
    """
    result_path = os.path.join(root, "speed_results.html")
    with open(result_path, "w", encoding="utf-8") as out:
        head = template.replace("{{version}}", infos['version'])
        head = head.replace("{{userAgent}}", infos['userAgent'])
        head = head.replace("{{cpython_version}}", cpython_version)
        print('date', datetime.date.today().strftime('%d/%m/%Y'))
        now = datetime.datetime.now()
        head = head.replace("{{date}}", now.strftime('%d/%m/%Y %H:%M'))
        out.write(head)
        for record in data:
            out.write(f'<tr><td>{record["description"]}</td>' +
                f'<td align="right"><b>{record["ratio"]}</b></td>' +
                f'<td><pre>{html.escape(record["src"])}</pre></td></tr>\n')
        out.write("</table>\n</body>\n</html>")

    return web.Response(text='ok')

app = web.Application()

statics = ['', 'src', 'tests', 'assets']
static_routes = [web.static(f'/{s}', os.path.join(os.getcwd(), 'www', s))
                 for s in statics]
app.add_routes(static_routes)

app.add_routes([web.get('/ajax_get', handle_ajax_get),
                web.post('/ajax_post', handle_ajax_post),
                web.post('/time_cpython', handle_time_cpython),
                web.post('/store_speed', store_speed)])

web.run_app(app, port=8000)