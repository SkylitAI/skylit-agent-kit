"""The first-run path, defined once: what users are told to expect is what the commands do.

The README's "What to expect" block is generated from STEPS and checked by tests.
"""

from collections import namedtuple

KIT = 'python3 -m skylit_agent_kit'
DEVELOPER_PAGE = 'https://app.skylit.ai/developer'
LOGIN = f'{KIT} login'
FIRST_LIVE = f'{KIT} endpoint heatseeker.getHeatmap --param symbols=SPY --param metric=gamma --live'

Step = namedtuple('Step', 'title who action outcome credits')

STEPS = (
    Step('Check setup', 'Agent', 'runs `doctor`', 'offline; one line per prerequisite', 0),
    Step('Create a key', 'You', 'Developer page → API keys → New key, in the browser',
         'shown once; never paste it into chat', 0),
    Step('Store the key', 'You', f'`{LOGIN}` in your own terminal', 'hidden prompt; stored on this computer', 0),
    Step('Prove the connection', 'Agent', 'runs `account --welcome`',
         'one free account check; shows Connected to Skylit with your credits', 0),
    Step('First live data', 'Agent, after you say yes', 'fetches one SPY gamma heatmap',
         'real strikes nearest spot with their timestamp; 1 credit', 1),
)

PROMISE = 'Nothing spends credits before step 5, and step 5 waits for your yes.'


def render_markdown():
    lines = [f'{n}. **{s.title}** ({s.who.lower()}): {s.action}. {s.outcome[0].upper()}{s.outcome[1:]}.'
             for n, s in enumerate(STEPS, 1)]
    return '\n'.join([*lines, '', f'**{PROMISE}**'])


def plain(text):
    return text.replace('`', '')


def render_text():
    lines = [f'  {n}. {s.title:<21} {s.who}: {plain(s.action)}' for n, s in enumerate(STEPS, 1)]
    return '\n'.join(['What to expect:', *lines, '', PROMISE])


def render_progress(current):
    """`current` is the 1-based next step; earlier steps are done."""
    marks = ['✓' if n < current else '→' if n == current else ' ' for n in range(1, len(STEPS) + 1)]
    lines = [f'{mark} {n}. {s.title:<21} {s.who}' for n, (mark, s) in enumerate(zip(marks, STEPS), 1)]
    return '\n'.join(['Your path:', *lines])


def render_start():
    return '\n'.join(['Skylit Agent Kit: connect your Skylit account in five steps.', '', render_text(), '',
                      f'Start with: {KIT} doctor', f'All commands: {KIT} --help'])


def render_welcome_next():
    step = STEPS[-1]
    return f'Step 5, {step.title.lower()} ({step.credits} credit, only after you say yes): {FIRST_LIVE}'
