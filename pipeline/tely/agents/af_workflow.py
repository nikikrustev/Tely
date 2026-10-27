"""The workflow.py steps as a Microsoft Agent Framework graph (file 18 §3). OWNER: A (potencialbg).

    Director -> Commentator -> Verifier -> TTS          (one short-lived workflow per window)

Imported only when agent-framework is installed (requirements-azure.txt); CI runs workflow.run_window instead.
File 18's gotcha "runs are stateful" is why build() makes a fresh workflow for every window.
Agent Framework emits the spans (workflow.run, executor.process <id>, invoke_agent Director, chat <model>) that
tracing.py exports to Application Insights.
"""

# No `from __future__ import annotations`: Agent Framework routes messages by the handlers' real type hints.

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

from tely.agents import workflow as W
from tely.commentary.source import Match


class DirectorExecutor(Executor):
    def __init__(self, model):
        super().__init__(id="director")
        self.model = model

    @handler
    async def plan(self, w: W.Window, ctx: WorkflowContext[W.Step]) -> None:
        await ctx.send_message(await W.director_step(w, self.model))


class CommentatorExecutor(Executor):
    def __init__(self, m: Match):
        super().__init__(id="commentator")
        self.m = m

    @handler
    async def write(self, s: W.Step, ctx: WorkflowContext[W.Step]) -> None:
        await ctx.send_message(W.commentator_step(self.m, s))


class VerifierExecutor(Executor):
    def __init__(self, m: Match):
        super().__init__(id="verifier")
        self.m = m

    @handler
    async def check(self, s: W.Step, ctx: WorkflowContext[W.Step]) -> None:
        await ctx.send_message(W.verifier_step(self.m, s))


class TtsExecutor(Executor):
    def __init__(self, render):
        super().__init__(id="tts")
        self.render = render

    @handler
    async def speak(self, s: W.Step, ctx: WorkflowContext[W.Step, W.Step]) -> None:
        await ctx.yield_output(W.tts_step(s, self.render))


def build(m: Match, model, render):
    d, c, v, t = DirectorExecutor(model), CommentatorExecutor(m), VerifierExecutor(m), TtsExecutor(render)
    return (WorkflowBuilder(start_executor=d, name="tely-director",
                            description="Director -> Commentator -> Verifier -> TTS for one look-ahead window")
            .add_edge(d, c).add_edge(c, v).add_edge(v, t).build())


async def run_window(m: Match, w: W.Window, model, render) -> W.Step:
    result = await build(m, model, render).run(w)
    outputs = result.get_outputs()
    if len(outputs) != 1:
        raise RuntimeError(f"workflow for {w.key} produced {len(outputs)} outputs, expected 1")
    return outputs[0]
