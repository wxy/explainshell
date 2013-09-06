import logging
from flask import render_template, request

from explainshell import matcher, errors, util, store, config
from explainshell.web import app, helpers

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/explain/<program>', defaults={'section' : None})
@app.route('/explain/<section>/<program>')
def explain(section, program):
    s = store.store('explainshell', config.MONGO_URI)
    try:
        if 'args' in request.args:
            args = request.args['args']
            command = '%s %s' % (program, args)
            matcher_ = matcher.matcher(command, s, section)
            groups = matcher_.match()
            mr = groups[1].results
            l = []
            it = util.peekable(iter(mr))
            while it.hasnext():
                m = it.next()
                spaces = 0
                if it.hasnext():
                    spaces = it.peek().start - m.end
                spaces = ' ' * spaces
                text = m.text
                if text:
                    text = text.decode('utf-8')
                d = {'match' : m.match, 'unknown' : m.unknown, 'text' : text, 'spaces' : spaces}
                l.append(d)

            d = l[0]
            d['section'] = groups[1].manpage.section
            d['match'] = '%s(%s)' % (d['match'], d['section'])
            d['source'] = groups[1].manpage.source[:-5]
            others = helpers.others(groups[1].others)

            return render_template('explain.html', program=l[0], matches=l,
                                   othersections=others, getargs=args)
        else:
            logger.info('/explain section=%r program=%r', section, program)
            mps = s.findmanpage(program, section)
            mp = mps.pop(0)
            program = mp.namesection

            mp = {'source' : mp.source[:-3],
                  'section' : mp.section,
                  'program' : program,
                  'synopsis' : mp.synopsis,
                  'options' : [o.text.decode('utf-8') for o in mp.options]}

            othersections = helpers.others(mps)
            logger.info('others: %s', othersections)
            return render_template('options.html', mp=mp, othersections=helpers.others(mps))
    except errors.ProgramDoesNotExist, e:
        return render_template('missingmanpage.html', prog=e.args[0])
    except errors.ParsingError, e:
        return render_template('error.html', message='Parsing error: %s' % str(e))
