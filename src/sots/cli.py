"""SotS command-line interface (P00 T00.050-T00.051, P03 doctor/stop).

Every command and subcommand from blueprint 12 §1, §3.1, and §4 is registered.
Implemented: ``init``, ``cost``, ``settings test-providers``, ``doctor``,
``stop``, ``profile interview``, ``profile check``, ``ingest``,
``foundation parse``, ``foundation check``, and the ``vault`` app.
Every other command is a stub that prints
``not yet implemented (phase Pxx)`` and exits 1, except ``write`` which prints
the R-SCOPE-02 notice and exits 2.

Command bodies live in ``sots.commands`` (W0 split); this module keeps the
Typer app plus registration.
"""

# ruff: noqa: E402 - registrations import after the app setup by design.


from __future__ import annotations

import typer

app = typer.Typer(
    name="sots",
    help="The Subject of the Self research and manuscript workflow.",
    no_args_is_help=True,
)

# >>> lane-I  (W0 baseline registrations, original order)
from sots.commands.core import init

app.command()(init)
from sots.commands.ingest import ingest

app.command()(ingest)
from sots.commands.runs import run

app.command()(run)
from sots.commands.runs import resume

app.command()(resume)
from sots.commands.runs import status

app.command()(status)
from sots.commands.runs import report

app.command()(report)
from sots.commands.runs import claims

app.command()(claims)
from sots.commands.runs import audit

app.command()(audit)
from sots.commands.runs import eval

app.command()(eval)
from sots.commands.core import cost

app.command()(cost)
from sots.commands.runs import tui

app.command()(tui)
from sots.commands.core import write

app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(write)
from sots.commands.core import doctor

app.command()(doctor)
from sots.commands.core import stop

app.command()(stop)
from sots.commands.acts import act

app.command()(act)
from sots.commands.acts import advance

app.command()(advance)
from sots.commands.acts import export

app.command()(export)
from sots.commands.acts import replay

app.command()(replay)
from sots.commands.acts import reason

app.command()(reason)
from sots.commands.acts import revise

app.command()(revise)
from sots.commands.acts import master_audit

app.command(name="master-audit")(master_audit)
from sots.commands.profile import profile_app

app.add_typer(profile_app, name='profile')
from sots.commands.foundation import foundation_app

app.add_typer(foundation_app, name='foundation')
from sots.commands.review import review_app

app.add_typer(review_app, name='review')
from sots.commands.expand import expand_app

app.add_typer(expand_app, name='expand')
from sots.commands.core import settings_app

app.add_typer(settings_app, name='settings')
from sots.commands.chapter import chapter_app

app.add_typer(chapter_app, name='chapter')
from sots.commands.style_guide import style_guide_app

app.add_typer(style_guide_app, name='style-guide')
from sots.commands.revisions import revisions_app

app.add_typer(revisions_app, name='revisions')
from sots.commands.hunks import hunks_app

app.add_typer(hunks_app, name='hunks')
from sots.commands.audience import audience_app

app.add_typer(audience_app, name='audience')
from sots.commands.legal import legal_app

app.add_typer(legal_app, name='legal')
from sots.commands.proposals import proposals_app

app.add_typer(proposals_app, name='proposals')
from sots.commands.grader import grader_app

app.add_typer(grader_app, name='grader')
from sots.commands.learning import learning_app

app.add_typer(learning_app, name='learning')
from sots.commands.mge import mge_app

app.add_typer(mge_app, name='mge')
from sots.commands.voice import voice_app

app.add_typer(voice_app, name='voice')
from sots.vault.cli import vault_app

app.add_typer(vault_app, name='vault')
# <<< lane-I

# >>> lane-A
# <<< lane-A

# >>> lane-B
# <<< lane-B

# >>> lane-C
# <<< lane-C

# >>> lane-D
# <<< lane-D
