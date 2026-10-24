// OWNER: A (potencialbg). Tester mode (?test=1, D19): the questions after each clip and in the overall feedback.
// Probes and scale are eval/listening_test.md sections 5 and 6, turned into multiple choice with "Don't know" always
// there. The answer KEY is section 5's table. It is used only by scoreClip(): never shown, and the score is sent to
// the relay but never displayed. Choice ids must match relay/feedback.py SCHEMA (relay/tests/test_feedback.py).

export type ClipNo = 1 | 2;
export type ProbeId = 'where' | 'side' | 'danger' | 'scored';
export type ScaleId = 'enjoy' | 'access' | 'follow';
export type Choice = readonly [id: string, label: string];

export interface Probe { id: ProbeId; question: string; choices: readonly Choice[] }

const DONT_KNOW: Choice = ['dont_know', "Don't know"];

export const PROBES: readonly Probe[] = [
  {
    id: 'where',
    question: 'Think of the biggest moment in that clip. Where on the pitch was the ball?',
    choices: [
      ['left_close', 'Close to the goal at the left end'],
      ['right_close', 'Close to the goal at the right end'],
      ['left_far', 'Towards the left end, but not close to the goal'],
      ['right_far', 'Towards the right end, but not close to the goal'],
      ['middle', 'Around the middle of the pitch'],
      DONT_KNOW,
    ],
  },
  {
    id: 'side',
    question: 'Which side of the pitch did that attack come down?',
    choices: [['near', 'The near side (closest to you)'], ['far', 'The far side'], ['middle', 'The middle'], DONT_KNOW],
  },
  {
    id: 'danger',
    question: 'Was there a moment when a goal looked likely? For which team?',
    choices: [['reds', 'Yes, for Reds'], ['navy', 'Yes, for Navy'], ['both', 'Yes, for both teams'], ['no', 'No'], DONT_KNOW],
  },
  {
    id: 'scored',
    question: 'Did anyone score? Who?',
    choices: [['reds', 'Reds scored'], ['navy', 'Navy scored'], ['nobody', 'Nobody scored'], DONT_KNOW],
  },
];

/** eval/listening_test.md section 5. Navy attack left and Reds attack right (the fan sits on the halfway line). */
export const KEY: Record<ClipNo, Record<ProbeId, readonly string[]>> = {
  // Navy header 6.8 m out at the left end, cross from the far side, the goal stands after VAR.
  1: { where: ['left_close'], side: ['far'], danger: ['navy'], scored: ['navy'] },
  // Reds shot blocked 1 m out at the right end (centre), or the Navy shot from outside the box at the left end
  // (after "far side, Navy"); the score stays Reds nil, Navy one.
  2: { where: ['right_close', 'left_far'], side: ['middle', 'far'], danger: ['reds', 'navy', 'both'], scored: ['nobody'] },
};

export type ProbeAnswers = Partial<Record<ProbeId, string>>;
export type ProbeScores = Record<`${ProbeId}_ok`, 0 | 1>;

/** 1 if the answer is in the key, 0 if it is wrong, missing or "don't know" (section 5's scoring). */
export function scoreClip(clip: ClipNo, answers: ProbeAnswers): ProbeScores {
  const key = KEY[clip];
  const ok = (p: ProbeId): 0 | 1 => (answers[p] !== undefined && key[p].includes(answers[p]!) ? 1 : 0);
  return { where_ok: ok('where'), side_ok: ok('side'), danger_ok: ok('danger'), scored_ok: ok('scored') };
}

export interface ScaleQ { id: ScaleId; question: string; low: string; high: string }

/** Section 6: our 3 x 1-5 version of RNIB's 15-point scale. */
export const SCALE: readonly ScaleQ[] = [
  { id: 'enjoy', question: 'How much did you enjoy listening to that clip?', low: 'not at all', high: 'very much' },
  { id: 'access', question: 'How well did it give you what you need to follow football without seeing it?', low: 'not at all', high: 'completely' },
  { id: 'follow', question: 'How accurately could you follow what was happening on the pitch?', low: 'not at all', high: 'completely' },
];

export const PREFERRED: readonly Choice[] = [['1', 'Clip 1'], ['2', 'Clip 2'], ['none', 'No preference']];
export const DEVICE: readonly Choice[] = [
  ['android_phone', 'Android phone'], ['iphone', 'iPhone'], ['windows', 'Windows computer'], ['mac', 'Mac'],
  ['tablet', 'Tablet'], ['other', 'Something else'],
];
export const HEADPHONES: readonly Choice[] = [
  ['wired', 'Wired headphones'], ['bluetooth', 'Bluetooth headphones or earbuds'], ['none', 'No headphones (speakers)'],
];
export const SCREEN_READER: readonly Choice[] = [
  ['none', 'No'], ['nvda', 'NVDA'], ['jaws', 'JAWS'], ['narrator', 'Narrator'], ['voiceover', 'VoiceOver'],
  ['talkback', 'TalkBack'], ['other', 'Another one'],
];
export const SIGHT: readonly Choice[] = [
  ['not_said', "I'd rather not say"], ['sighted', 'Sighted'], ['partially_sighted', 'Partially sighted'], ['blind', 'Blind'],
];
export const ASK_WORKED: readonly Choice[] = [
  ['yes', 'Yes'], ['partly', 'Partly'], ['no', 'No'], ['not_tried', "I didn't try it"],
];
export const SETTINGS_EASY: readonly Choice[] = [['yes', 'Yes'], ['partly', 'Partly'], ['no', 'No']];
export const PROBLEM_KINDS: readonly Choice[] = [
  ['sound', 'Sound'], ['voice', 'The commentator’s voice'], ['controls', 'Buttons or controls'],
  ['confusing', 'Something was confusing'], ['stuck', 'It crashed or got stuck'], ['other', 'Something else'],
];

/** The label for a choice id, for "Copy my answers". */
export function labelOf(choices: readonly Choice[], id: string | undefined): string {
  return choices.find(([c]) => c === id)?.[1] ?? '';
}
