// OWNER: A (potencialbg). D27: the language the fan hears, for the live Ask (sent with every question, so the relay
// answers in it). mountLaneA's setLanguage() sets it together with the commentary track.
let lang = 'en';

export const liveLanguage = (): string => lang;
export function setLiveLanguage(l: string): void {
  lang = l;
}
